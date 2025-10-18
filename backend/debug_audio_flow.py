#!/usr/bin/env python3
"""
Debug script to test audio flow from client to ElevenLabs and back
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_audio_flow():
    """Test the complete audio flow"""
    
    # Test parameters
    session_id = "test_session_123"
    agent_id = "agent_4901k7vt2tdffjw9qrkhk4by8ecp"
    
    uri = f"ws://localhost:8000/ws/audio/{agent_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to audio WebSocket")
            
            # Wait for connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            logger.info(f"📨 Connection response: {data}")
            
            if "error" in data:
                logger.error(f"❌ Connection error: {data['error']}")
                return
            
            # Generate test audio (1 second of sine wave at 440Hz)
            sample_rate = 16000
            duration = 1.0
            frequency = 440  # A4 note
            
            # Generate sine wave
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Convert to bytes
            audio_bytes = audio_data.tobytes()
            
            logger.info(f"📤 Sending {len(audio_bytes)} bytes of test audio...")
            
            # Send audio data
            await websocket.send(audio_bytes)
            
            # Wait for processing response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                logger.info(f"📨 Processing response: {data}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No processing response received")
            
            # Wait for audio response from ElevenLabs
            logger.info("🎧 Waiting for audio response from ElevenLabs...")
            
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    
                    try:
                        data = json.loads(response)
                        logger.info(f"📨 Received JSON response: {data}")
                        
                        # Check if it's audio data
                        if data.get("type") == "audio" or "audio" in data:
                            logger.info("🎵 Audio response received!")
                            break
                            
                    except json.JSONDecodeError:
                        # Might be binary audio data
                        logger.info(f"📨 Received binary data: {len(response)} bytes")
                        if len(response) > 100:  # Likely audio data
                            logger.info("🎵 Binary audio response received!")
                            break
                            
            except asyncio.TimeoutError:
                logger.warning("⚠️ No audio response received within 30 seconds")
            
            logger.info("✅ Audio flow test completed")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

async def test_elevenlabs_connection():
    """Test direct ElevenLabs WebSocket connection"""
    
    agent_id = "agent_4901k7vt2tdffjw9qrkhk4by8ecp"
    uri = f"ws://localhost:8000/ws/elevenlabs/{agent_id}?session_id=test_session&user_id=test_user"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to ElevenLabs WebSocket")
            
            # Wait for connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            logger.info(f"📨 Connection response: {data}")
            
            # Send a test message
            test_message = {
                "type": "user_message",
                "text": "Hello, this is a test message"
            }
            await websocket.send(json.dumps(test_message))
            logger.info("📤 Sent test message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"📨 Received response: {response}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No response received")
            
            logger.info("✅ ElevenLabs connection test completed")
            
    except Exception as e:
        logger.error(f"❌ ElevenLabs test failed: {e}")

async def main():
    """Run all tests"""
    logger.info("🚀 Starting audio flow debug tests...")
    
    print("""
    Audio Flow Debug Tests
    =====================
    
    This script will test:
    1. Direct ElevenLabs WebSocket connection
    2. Audio streaming through the audio endpoint
    
    Make sure to:
    - Replace 'your_agent_id_here' with your actual ElevenLabs agent ID
    - Have your FastAPI server running on localhost:8000
    - Have a valid ELEVENLABS_API_KEY set
    """)
    
    # Test 1: Direct ElevenLabs connection
    logger.info("\n🧪 Test 1: Direct ElevenLabs Connection")
    await test_elevenlabs_connection()
    
    # Wait a bit between tests
    await asyncio.sleep(2)
    
    # Test 2: Audio flow
    logger.info("\n🧪 Test 2: Audio Flow")
    await test_audio_flow()
    
    logger.info("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
