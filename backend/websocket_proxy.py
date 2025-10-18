"""
WebSocket Proxy for ElevenLabs

This module provides a WebSocket proxy that forwards messages between
the frontend and ElevenLabs API, enabling logging, monitoring, and control.
"""

import asyncio
import json
import logging
import websockets
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


async def handle_elevenlabs_proxy(
    frontend_ws: WebSocket,
    session_id: str,
    agent_id: str,
    db_service
):
    """
    WebSocket proxy handler that forwards messages between frontend and ElevenLabs API.
    
    Args:
        frontend_ws: FastAPI WebSocket connection from frontend
        session_id: Session ID for this conversation
        agent_id: ElevenLabs agent ID
        db_service: Database service for session verification
    
    Flow:
        1. Frontend connects to this handler
        2. Handler establishes connection to ElevenLabs
        3. Messages are forwarded bidirectionally
        4. Audio and transcripts flow through the handler
    """
    logger.info(f"Frontend WebSocket connected for session: {session_id}")
    
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
            """Forward messages from frontend to ElevenLabs"""
            try:
                while True:
                    # Receive from frontend
                    data = await frontend_ws.receive_text()
                    message = json.loads(data)
                    
                    message_type = message.get('type', 'unknown')
                    logger.info(f"Frontend → ElevenLabs: {message_type}")
                    
                    # Optional: Log audio chunks being sent
                    if 'user_audio_chunk' in message:
                        audio_length = len(message.get('user_audio_chunk', ''))
                        logger.debug(f"  Sending audio chunk: {audio_length} bytes (base64)")
                    
                    # Forward to ElevenLabs
                    await elevenlabs_ws.send(data)
                    
            except WebSocketDisconnect:
                logger.info("Frontend disconnected")
            except Exception as e:
                logger.error(f"Error forwarding to ElevenLabs: {e}")
        
        async def forward_to_frontend():
            """Forward messages from ElevenLabs to frontend"""
            try:
                while True:
                    # Receive from ElevenLabs
                    data = await elevenlabs_ws.recv()
                    message = json.loads(data)
                    
                    message_type = message.get('type', 'unknown')
                    logger.info(f"ElevenLabs → Frontend: {message_type}")
                    
                    # Optional: Log interesting events
                    if message_type == 'audio':
                        audio_event = message.get('audio_event', {})
                        audio_length = len(audio_event.get('audio_base_64', ''))
                        logger.debug(f"  Audio chunk size: {audio_length} bytes (base64)")
                    
                    elif message_type == 'user_transcript':
                        transcript = message.get('user_transcription_event', {}).get('user_transcript', '')
                        logger.info(f"  👤 User said: {transcript}")
                        
                        # Save user transcript to database
                        if transcript:
                            await db_service.append_transcript(session_id, 'user', transcript)
                    
                    elif message_type == 'agent_response':
                        response = message.get('agent_response_event', {}).get('agent_response', '')
                        logger.info(f"  🤖 Agent response: {response}")
                        
                        # Save agent response to database
                        if response:
                            await db_service.append_transcript(session_id, 'agent', response)
                    
                    # Forward to frontend
                    await frontend_ws.send_text(data)
                    
            except websockets.exceptions.ConnectionClosed:
                logger.info("ElevenLabs connection closed")
            except Exception as e:
                logger.error(f"Error forwarding to frontend: {e}")
        
        # Run both forwarding tasks concurrently
        await asyncio.gather(
            forward_to_elevenlabs(),
            forward_to_frontend(),
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
        # Close ElevenLabs connection
        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
                logger.info("ElevenLabs WebSocket closed")
            except:
                pass
        
        logger.info(f"WebSocket proxy closed for session: {session_id}")

