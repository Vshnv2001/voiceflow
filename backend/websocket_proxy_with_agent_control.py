"""
WebSocket Proxy with Agent Control

This version buffers agent responses and sends them to the agent for approval
before forwarding to the customer.
"""

import asyncio
import json
import logging
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from agent_control_manager import agent_control_manager

logger = logging.getLogger(__name__)


async def handle_elevenlabs_proxy_with_agent_control(
    frontend_ws: WebSocket,
    session_id: str,
    agent_id: str,
    db_service
):
    """
    WebSocket proxy handler with agent control.
    
    Flow:
        1. Customer speaks → ElevenLabs
        2. ElevenLabs generates response → Backend buffers it
        3. Backend sends text suggestion to agent
        4. Agent reviews/edits → Clicks Send
        5. Backend streams audio to customer
    """
    logger.info(f"Customer WebSocket connected for session: {session_id}")
    
    # Register customer connection
    await agent_control_manager.register_customer_connection(session_id, frontend_ws)
    
    elevenlabs_ws = None
    
    try:
        # Verify session exists
        try:
            result = db_service.supabase.table("sessions").select("*").eq("id", session_id).single().execute()
            if not result.data:
                await frontend_ws.send_json({"error": "Session not found"})
                await frontend_ws.close()
                return
            session = result.data
            logger.info(f"Session verified: {session_id}, customer: {session.get('customer_name')}")
        except Exception as e:
            logger.error(f"Failed to verify session: {e}")
            await frontend_ws.send_json({"error": f"Failed to verify session: {str(e)}"})
            await frontend_ws.close()
            return
        
        # Connect to ElevenLabs API
        elevenlabs_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
        logger.info(f"Connecting to ElevenLabs: {elevenlabs_url}")
        
        elevenlabs_ws = await websockets.connect(elevenlabs_url)
        logger.info("✅ Connected to ElevenLabs WebSocket")
        
        # Create tasks for bidirectional message forwarding
        async def forward_to_elevenlabs():
            """Forward messages from customer to ElevenLabs"""
            try:
                while True:
                    # Receive from customer
                    data = await frontend_ws.receive_text()
                    message = json.loads(data)
                    
                    message_type = message.get('type', 'unknown')
                    logger.info(f"Customer → ElevenLabs: {message_type}")
                    
                    # Optional: Log audio chunks being sent
                    if 'user_audio_chunk' in message:
                        audio_length = len(message.get('user_audio_chunk', ''))
                        logger.debug(f"  Sending audio chunk: {audio_length} bytes (base64)")
                    
                    # Forward to ElevenLabs
                    await elevenlabs_ws.send(data)
                    
            except WebSocketDisconnect:
                logger.info("Customer disconnected")
            except Exception as e:
                logger.error(f"Error forwarding to ElevenLabs: {e}")
        
        async def forward_from_elevenlabs():
            """Forward messages from ElevenLabs (with agent control)"""
            try:
                while True:
                    # Receive from ElevenLabs
                    data = await elevenlabs_ws.recv()
                    message = json.loads(data)
                    
                    message_type = message.get('type', 'unknown')
                    logger.info(f"ElevenLabs → Backend: {message_type}")
                    
                    # Handle different message types
                    if message_type == 'audio':
                        # BUFFER audio instead of forwarding immediately
                        audio_event = message.get('audio_event', {})
                        audio_base64 = audio_event.get('audio_base_64', '')
                        if audio_base64:
                            await agent_control_manager.buffer_audio_chunk(session_id, audio_base64)
                        # DON'T forward to customer yet
                    
                    elif message_type == 'user_transcript':
                        transcript = message.get('user_transcription_event', {}).get('user_transcript', '')
                        logger.info(f"  👤 User said: {transcript}")
                        
                        # Save user transcript to database
                        if transcript:
                            await db_service.append_transcript(session_id, 'user', transcript)
                        
                        # Forward user transcript to customer
                        await frontend_ws.send_text(data)
                    
                    elif message_type == 'agent_response':
                        # BUFFER agent response text for agent review
                        response = message.get('agent_response_event', {}).get('agent_response', '')
                        logger.info(f"  🤖 Agent response (buffering): {response}")
                        
                        if response:
                            # Buffer the text and send to agent for review
                            await agent_control_manager.buffer_agent_response(session_id, response)
                            
                            # DON'T save to database yet - only save when agent clicks Send
                        
                        # DON'T forward agent response to customer yet
                    
                    else:
                        # Forward other message types normally
                        await frontend_ws.send_text(data)
                    
            except websockets.exceptions.ConnectionClosed:
                logger.info("ElevenLabs connection closed")
            except Exception as e:
                logger.error(f"Error forwarding from ElevenLabs: {e}")
        
        # Run both forwarding tasks concurrently
        await asyncio.gather(
            forward_to_elevenlabs(),
            forward_from_elevenlabs(),
            return_exceptions=True
        )
        
    except websockets.exceptions.WebSocketException as e:
        logger.error(f"❌ ElevenLabs WebSocket error: {e}")
        try:
            await frontend_ws.send_json({"error": f"ElevenLabs connection error: {str(e)}"})
        except:
            pass
    except Exception as e:
        logger.error(f"❌ WebSocket proxy error: {e}")
        try:
            await frontend_ws.send_json({"error": str(e)})
        except:
            pass
    finally:
        # Unregister customer connection
        await agent_control_manager.unregister_customer_connection(session_id)
        
        # Close ElevenLabs connection
        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
                logger.info("ElevenLabs WebSocket closed")
            except:
                pass
        
        logger.info(f"WebSocket proxy closed for session: {session_id}")

