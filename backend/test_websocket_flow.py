#!/usr/bin/env python3
"""
Comprehensive WebSocket Flow Test Script

This script tests the complete websocket flow:
1. Client -> Database WebSocket connection
2. Database -> ElevenLabs WebSocket connection  
3. ElevenLabs response -> Database -> Client

It verifies that:
- WebSocket connections are established successfully
- Audio data flows from client to ElevenLabs
- Responses from ElevenLabs are returned to the client
- The complete round-trip communication works
"""

import asyncio
import json
import time
import os
import base64
import websockets
import traceback
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play
import requests
import logging
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = "http://localhost:8000"
WS_BACKEND_URL = "ws://localhost:8000"
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
TEST_AUDIO_FILE = "test/test.mp3"  # Make sure this file exists
TEST_SESSION_ID = f"6201ba16-7bd0-4986-a7e7-ca0f81d13b0f"
TEST_USER_ID = f"dc78ffb0-a0e2-4528-9a7d-8fea25fcc64f"

# Audio Response Configuration
PLAYBACK_AUDIO_RESPONSES = True
SAVE_AUDIO_RESPONSES = True
OUTPUT_AUDIO_DIR = "test_output"
OUTPUT_AUDIO_FORMAT = "wav"

class WebSocketFlowTester:
    """Test the complete WebSocket flow from client to ElevenLabs and back"""
    
    def __init__(self):
        self.audio_collector = AudioCollector()
        self.test_results = {
            "backend_health": False,
            "websocket_connection": False,
            "elevenlabs_connection": False,
            "audio_sending": False,
            "response_receiving": False,
            "complete_flow": False
        }
        
    async def check_backend_health(self):
        """Check if the backend is running and healthy"""
        try:
            logger.info("🔍 Checking backend health...")
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Backend is running and healthy")
                self.test_results["backend_health"] = True
                return True
            else:
                logger.error(f"❌ Backend health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to backend: {e}")
            return False
    
    async def test_websocket_connection(self):
        """Test the main WebSocket endpoint for ElevenLabs agent conversations"""
        ws_url = f"{WS_BACKEND_URL}/ws/elevenlabs/{ELEVENLABS_AGENT_ID}?session_id={TEST_SESSION_ID}&user_id={TEST_USER_ID}"
        logger.info(f"🔌 Testing WebSocket connection to: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("✅ WebSocket connected successfully!")
                self.test_results["websocket_connection"] = True
                
                # Wait for connection confirmation
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    logger.info(f"📨 Connection confirmation: {response_data}")
                    
                    if response_data.get("type") == "connection_established":
                        logger.info("✅ Connection established successfully")
                    else:
                        logger.warning(f"⚠️ Unexpected connection response: {response_data}")
                        
                except asyncio.TimeoutError:
                    logger.error("❌ Timeout waiting for connection confirmation")
                    return False
                
                # Wait for ElevenLabs initiation metadata
                logger.info("⏳ Waiting for ElevenLabs initiation metadata...")
                initiation_received = await self.wait_for_initiation(websocket, timeout=15.0)
                
                if initiation_received:
                    logger.info("✅ ElevenLabs connection established")
                    self.test_results["elevenlabs_connection"] = True
                else:
                    logger.error("❌ Failed to receive ElevenLabs initiation metadata")
                    return False
                
                return True
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"🔌 WebSocket connection closed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {e}")
            logger.error(f"❌ Error details: {traceback.format_exc()}")
            return False
    
    async def test_audio_flow(self):
        """Test sending audio and receiving responses"""
        ws_url = f"{WS_BACKEND_URL}/ws/elevenlabs/{ELEVENLABS_AGENT_ID}?session_id={TEST_SESSION_ID}&user_id={TEST_USER_ID}"
        logger.info(f"🎵 Testing audio flow...")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Wait for connection confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"📨 Connection confirmed: {json.loads(response)}")
                
                # Wait for ElevenLabs initiation
                await self.wait_for_initiation(websocket, timeout=15.0)
                
                # Test 1: Send text message
                logger.info("🧪 Test 1: Sending text message...")
                text_message = {
                    "type": "user_message",
                    "text": "Hello, this is a test message. Can you hear me?",
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(text_message))
                logger.info("✅ Text message sent")
                
                # Test 2: Send audio if available
                if os.path.exists(TEST_AUDIO_FILE):
                    logger.info(f"🧪 Test 2: Sending audio from {TEST_AUDIO_FILE}...")
                    audio_sent = await self.send_audio_file(websocket, TEST_AUDIO_FILE)
                    if audio_sent:
                        self.test_results["audio_sending"] = True
                        logger.info("✅ Audio sent successfully")
                    else:
                        logger.error("❌ Failed to send audio")
                else:
                    logger.warning(f"⚠️ Audio file {TEST_AUDIO_FILE} not found, skipping audio test")
                
                # Test 3: Listen for responses
                logger.info("🧪 Test 3: Listening for responses...")
                responses_received = await self.listen_for_responses(websocket, timeout=30.0)
                
                if responses_received:
                    self.test_results["response_receiving"] = True
                    logger.info("✅ Responses received successfully")
                else:
                    logger.warning("⚠️ No responses received")
                
                # Check if we have audio responses
                if self.audio_collector.has_audio():
                    logger.info(f"🎵 Processing {len(self.audio_collector.audio_chunks)} audio chunks...")
                    
                    if PLAYBACK_AUDIO_RESPONSES:
                        logger.info("🔊 Playing audio response...")
                        self.audio_collector.play_audio()
                    
                    if SAVE_AUDIO_RESPONSES:
                        logger.info("💾 Saving audio response...")
                        saved_file = self.audio_collector.save_audio("websocket_test_response")
                        if saved_file:
                            logger.info(f"✅ Audio saved: {saved_file}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Audio flow test error: {e}")
            logger.error(f"❌ Error details: {traceback.format_exc()}")
            return False
    
    async def test_audio_websocket_endpoint(self):
        """Test the dedicated audio WebSocket endpoint"""
        ws_url = f"{WS_BACKEND_URL}/ws/audio/{TEST_SESSION_ID}"
        logger.info(f"🔊 Testing audio WebSocket endpoint: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("✅ Audio WebSocket connected successfully!")
                
                # Wait for ready status
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    logger.info(f"📨 Audio WebSocket response: {response_data}")
                    
                    if response_data.get("status") == "ready":
                        logger.info("✅ Audio WebSocket ready for streaming")
                    else:
                        logger.warning(f"⚠️ Unexpected ready response: {response_data}")
                        
                except asyncio.TimeoutError:
                    logger.error("❌ Timeout waiting for audio WebSocket ready status")
                    return False
                
                # Send test audio if available
                if os.path.exists(TEST_AUDIO_FILE):
                    logger.info("🎵 Sending audio to audio WebSocket...")
                    audio_sent = await self.send_raw_audio(websocket, TEST_AUDIO_FILE)
                    if audio_sent:
                        logger.info("✅ Raw audio sent successfully")
                        
                        # Listen for responses
                        logger.info("👂 Listening for audio WebSocket responses...")
                        await self.listen_for_responses(websocket, timeout=20.0)
                    else:
                        logger.error("❌ Failed to send raw audio")
                else:
                    logger.warning(f"⚠️ Audio file {TEST_AUDIO_FILE} not found, skipping audio test")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Audio WebSocket test error: {e}")
            logger.error(f"❌ Error details: {traceback.format_exc()}")
            return False
    
    async def wait_for_initiation(self, websocket, timeout=10.0):
        """Wait for ElevenLabs conversation initiation metadata"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=timeout - (time.time() - start_time))
                data = json.loads(response)
                
                if data.get("type") == "conversation_initiation_metadata":
                    logger.info(f"✅ ElevenLabs initiation received: {data}")
                    return True
                else:
                    logger.debug(f"📨 Pre-init message: {data}")
                    
            except asyncio.TimeoutError:
                break
            except json.JSONDecodeError:
                logger.debug(f"📨 Non-JSON message: {response}")
                continue
        
        logger.error("❌ Timeout waiting for ElevenLabs initiation metadata")
        return False
    
    async def send_audio_file(self, websocket, audio_file_path):
        """Send audio file as base64 encoded chunks"""
        try:
            frames = self.mp3_to_pcm16k_base64_chunks(audio_file_path, frame_ms=20)
            logger.info(f"📦 Split audio into {len(frames)} frames")
            
            # Send first few frames for testing
            max_frames = min(len(frames), 50)  # Limit for testing
            for i, b64_frame in enumerate(frames[:max_frames], 1):
                await websocket.send(json.dumps({
                    "user_audio_chunk": b64_frame
                }))
                
                if i % 10 == 0:
                    logger.info(f"📤 Sent frame {i}/{max_frames}")
                
                await asyncio.sleep(0.02)  # Real-time pacing
            
            logger.info("✅ Audio frames sent")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending audio: {e}")
            return False
    
    async def send_raw_audio(self, websocket, audio_file_path):
        """Send raw audio data to the audio WebSocket endpoint"""
        try:
            # Load and convert audio to PCM 16kHz mono
            audio = AudioSegment.from_file(audio_file_path)
            audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            raw_data = audio.raw_data
            
            # Send in chunks
            chunk_size = 1024
            for i in range(0, len(raw_data), chunk_size):
                chunk = raw_data[i:i+chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.01)  # Small delay between chunks
            
            logger.info("✅ Raw audio sent")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending raw audio: {e}")
            return False
    
    async def listen_for_responses(self, websocket, timeout=30.0):
        """Listen for responses from the WebSocket"""
        response_count = 0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                
                try:
                    data = json.loads(response)
                    response_type = data.get("type", "unknown")
                    logger.info(f"📨 Response {response_count + 1}: {response_type}")
                    
                    # Handle different response types
                    if response_type == "agent_response":
                        text = data.get("agent_response_event", {}).get("agent_response", "")
                        logger.info(f"🤖 Agent response: {text}")
                    
                    elif response_type == "audio":
                        audio_data = data.get("audio_event", {}).get("audio_base_64")
                        if audio_data:
                            self.audio_collector.add_audio_chunk(audio_data)
                            logger.info(f"🔊 Audio chunk received (len={len(audio_data)})")
                    
                    elif response_type == "user_transcript":
                        text = data.get("user_transcript", {}).get("text", "")
                        logger.info(f"📝 User transcript: {text}")
                    
                    elif response_type == "ping":
                        # Respond to ping with pong
                        await websocket.send(json.dumps({"type": "pong"}))
                        logger.info("🏓 Responded to ping")
                    
                    response_count += 1
                    
                except json.JSONDecodeError:
                    logger.debug(f"📨 Non-JSON response: {response}")
                    response_count += 1
                    
            except asyncio.TimeoutError:
                logger.info("⏰ No more responses (timeout)")
                break
            except websockets.exceptions.ConnectionClosed:
                logger.info("🔌 Connection closed by server")
                break
            except Exception as e:
                logger.error(f"❌ Error receiving response: {e}")
                break
        
        logger.info(f"📊 Total responses received: {response_count}")
        return response_count > 0
    
    def mp3_to_pcm16k_base64_chunks(self, path: str, frame_ms: int = 20):
        """Convert MP3 to PCM 16kHz base64 chunks"""
        try:
            audio = AudioSegment.from_file(path)
            audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            raw_data = audio.raw_data
            
            bytes_per_frame = int(16000 * (frame_ms / 1000.0) * 2)
            chunks = []
            
            for i in range(0, len(raw_data), bytes_per_frame):
                frame = raw_data[i:i+bytes_per_frame]
                if frame:
                    chunks.append(base64.b64encode(frame).decode("ascii"))
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Error converting audio: {e}")
            return []
    
    def print_test_results(self):
        """Print comprehensive test results"""
        logger.info("\n" + "="*60)
        logger.info("📊 WEBSOCKET FLOW TEST RESULTS")
        logger.info("="*60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        
        # Overall assessment
        all_passed = all(self.test_results.values())
        if all_passed:
            logger.info("\n🎉 ALL TESTS PASSED! WebSocket flow is working correctly.")
            self.test_results["complete_flow"] = True
        else:
            failed_tests = [name for name, result in self.test_results.items() if not result]
            logger.info(f"\n⚠️ SOME TESTS FAILED: {', '.join(failed_tests)}")
        
        logger.info("="*60)


class AudioCollector:
    """Collect and process audio chunks from ElevenLabs responses"""
    
    def __init__(self):
        self.audio_chunks = []
        self.response_count = 0
    
    def add_audio_chunk(self, base64_audio):
        """Add a base64 encoded audio chunk"""
        self.audio_chunks.append(base64_audio)
        logger.info(f"🎵 Collected audio chunk {len(self.audio_chunks)}")
    
    def get_combined_audio(self):
        """Combine all collected audio chunks into a single AudioSegment"""
        if not self.audio_chunks:
            return None
        
        try:
            raw_chunks = []
            for chunk_b64 in self.audio_chunks:
                raw_chunk = base64.b64decode(chunk_b64)
                raw_chunks.append(raw_chunk)
            
            combined_raw = b''.join(raw_chunks)
            
            audio = AudioSegment(
                data=combined_raw,
                sample_width=2,
                frame_rate=16000,
                channels=1
            )
            
            return audio
            
        except Exception as e:
            logger.error(f"❌ Error combining audio chunks: {e}")
            return None
    
    def play_audio(self):
        """Play the collected audio"""
        audio = self.get_combined_audio()
        if audio:
            logger.info("🔊 Playing audio response...")
            try:
                play(audio)
                logger.info("✅ Audio playback completed")
            except Exception as e:
                logger.error(f"❌ Error playing audio: {e}")
        else:
            logger.warning("⚠️ No audio to play")
    
    def save_audio(self, filename=None):
        """Save the collected audio to a file"""
        audio = self.get_combined_audio()
        if not audio:
            logger.warning("⚠️ No audio to save")
            return None
        
        os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)
        
        if filename is None:
            self.response_count += 1
            filename = f"websocket_response_{self.response_count}.{OUTPUT_AUDIO_FORMAT}"
        
        filepath = os.path.join(OUTPUT_AUDIO_DIR, filename)
        
        try:
            audio.export(filepath, format=OUTPUT_AUDIO_FORMAT)
            logger.info(f"💾 Audio saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"❌ Error saving audio: {e}")
            return None
    
    def has_audio(self):
        """Check if any audio chunks have been collected"""
        return len(self.audio_chunks) > 0
    
    def clear_chunks(self):
        """Clear collected audio chunks"""
        self.audio_chunks.clear()


async def main():
    """Main test function"""
    logger.info("🚀 Starting WebSocket Flow Tests")
    logger.info("="*60)
    
    # Create output directory
    if SAVE_AUDIO_RESPONSES:
        os.makedirs(OUTPUT_AUDIO_DIR, exist_ok=True)
        logger.info(f"📁 Output directory: {os.path.abspath(OUTPUT_AUDIO_DIR)}")
    
    # Initialize tester
    tester = WebSocketFlowTester()
    
    # Run tests
    logger.info("\n🧪 Running WebSocket Flow Tests...")
    
    # Test 1: Backend health check
    await tester.check_backend_health()
    
    if tester.test_results["backend_health"]:
        # Test 2: WebSocket connection
        await tester.test_websocket_connection()
        
        # Test 3: Audio flow
        await tester.test_audio_flow()
        
        # Test 4: Audio WebSocket endpoint
        await tester.test_audio_websocket_endpoint()
    
    # Print results
    tester.print_test_results()
    
    # Cleanup
    if tester.audio_collector.has_audio():
        tester.audio_collector.clear_chunks()
    
    logger.info("\n✅ WebSocket Flow Tests completed!")


if __name__ == "__main__":
    # Check configuration
    logger.info("📋 Test Configuration:")
    logger.info(f"   Backend URL: {BACKEND_URL}")
    logger.info(f"   WebSocket URL: {WS_BACKEND_URL}")
    logger.info(f"   Agent ID: {ELEVENLABS_AGENT_ID}")
    logger.info(f"   Test Audio: {TEST_AUDIO_FILE}")
    logger.info(f"   Audio exists: {os.path.exists(TEST_AUDIO_FILE)}")
    logger.info(f"   Session ID: {TEST_SESSION_ID}")
    logger.info(f"   User ID: {TEST_USER_ID}")
    
    # Run the tests
    asyncio.run(main())
