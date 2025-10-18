# services/elevenlabs_websocket_service.py

import asyncio
import json
import base64
import time
from typing import Dict, Any, Optional, Callable
import websockets
import logging
from datetime import datetime, timedelta
import uuid
import ssl
import certifi
import os
import wave
import io

from starlette.websockets import WebSocket as StarletteWebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ElevenLabsWebSocketService:
    """Service for managing ElevenLabs WebSocket connections with robust persistence"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "wss://api.elevenlabs.io/v1/convai/conversation"
        self._ready: Dict[str, asyncio.Event] = {}
        # NOTE: store the Starlette WebSocket for your app client, and the
        # websockets client for ElevenLabs
        self.active_connections: Dict[str, StarletteWebSocket] = {}
        self.elevenlabs_connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self._ssl_context: Optional[ssl.SSLContext] = None
        
        # Connection persistence settings
        self.heartbeat_interval = 30  # seconds
        self.reconnect_attempts = 5
        self.reconnect_delay = 2  # seconds
        self.max_connection_age = 3600  # 1 hour
        
        # Background tasks for connection management
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._reconnect_tasks: Dict[str, asyncio.Task] = {}
        
        # Audio and transcript saving
        self.test_output_dir = "/Users/chaitanya/Documents/Coding/voiceflow/backend/test_output"
        self.audio_chunks: Dict[str, list] = {}  # Store audio chunks per connection
        self.transcript_data: Dict[str, list] = {}  # Store transcript data per connection
        
    async def wait_until_ready(self, connection_id: str, timeout: float = 10.0):
        evt = self._ready.get(connection_id)
        if evt is None:
            raise ValueError(f"No ready event for {connection_id}")
        await asyncio.wait_for(evt.wait(), timeout=timeout)

    def _save_audio_chunk(self, connection_id: str, audio_base64: str, is_final: bool = False):
        """Save audio chunk to memory and write to file when final"""
        if connection_id not in self.audio_chunks:
            self.audio_chunks[connection_id] = []
        
        try:
            # Decode base64 audio data
            audio_data = base64.b64decode(audio_base64)
            self.audio_chunks[connection_id].append(audio_data)
            
            if is_final and self.audio_chunks[connection_id]:
                # Combine all audio chunks and save as WAV file
                combined_audio = b''.join(self.audio_chunks[connection_id])
                self._write_wav_file(connection_id, combined_audio)
                # Clear the chunks after saving
                self.audio_chunks[connection_id] = []
                
        except Exception as e:
            logger.error(f"Error saving audio chunk for {connection_id}: {e}")

    def _write_wav_file(self, connection_id: str, audio_data: bytes):
        """Write audio data to WAV file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audio_response_{connection_id}_{timestamp}.wav"
            filepath = os.path.join(self.test_output_dir, filename)
            
            # Create WAV file with proper headers
            with wave.open(filepath, 'wb') as wav_file:
                # Set WAV parameters (ElevenLabs typically uses 24kHz, 16-bit, mono)
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(24000)  # 24kHz
                wav_file.writeframes(audio_data)
            
            logger.info(f"Saved audio response to {filepath}")
            
        except Exception as e:
            logger.error(f"Error writing WAV file for {connection_id}: {e}")

    def _save_transcript(self, connection_id: str, transcript_text: str, is_final: bool = False):
        """Save transcript text to file"""
        if connection_id not in self.transcript_data:
            self.transcript_data[connection_id] = []
        
        self.transcript_data[connection_id].append(transcript_text)
        
        if is_final:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"transcript_{connection_id}_{timestamp}.txt"
                filepath = os.path.join(self.test_output_dir, filename)
                
                # Combine all transcript parts
                full_transcript = " ".join(self.transcript_data[connection_id])
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Transcript for connection {connection_id}\n")
                    f.write(f"Generated at: {datetime.now().isoformat()}\n")
                    f.write("-" * 50 + "\n")
                    f.write(full_transcript)
                
                logger.info(f"Saved transcript to {filepath}")
                # Clear the transcript data after saving
                self.transcript_data[connection_id] = []
                
            except Exception as e:
                logger.error(f"Error saving transcript for {connection_id}: {e}")

    def _create_ssl_context(self) -> ssl.SSLContext:
        if self._ssl_context is None:
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.load_verify_locations(certifi.where())
                self._ssl_context = ssl_context
                logger.info("SSL context created with certifi certificates")
            except Exception as e:
                logger.warning(f"Failed to create SSL context with certifi: {e}")
                self._ssl_context = ssl.create_default_context()
                logger.info("SSL context created with system certificates")
        return self._ssl_context

    async def _start_heartbeat(self, connection_id: str):
        """Start heartbeat task for a connection"""
        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
        
        self._heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat_loop(connection_id)
        )

    async def _heartbeat_loop(self, connection_id: str):
        """Send periodic heartbeat to keep connection alive"""
        try:
            while connection_id in self.active_connections:
                await asyncio.sleep(self.heartbeat_interval)
                
                if connection_id not in self.active_connections:
                    break
                    
                try:
                    # Send ping to client
                    client_ws = self.active_connections.get(connection_id)
                    if client_ws:
                        await client_ws.send_text(json.dumps({
                            "type": "ping",
                            "timestamp": time.time()
                        }))
                    
                    # Send ping to ElevenLabs
                    elevenlabs_ws = self.elevenlabs_connections.get(connection_id)
                    if elevenlabs_ws:
                        await elevenlabs_ws.send(json.dumps({
                            "type": "ping",
                            "timestamp": time.time()
                        }))
                        
                except Exception as e:
                    logger.warning(f"Heartbeat failed for {connection_id}: {e}")
                    # Trigger reconnection
                    await self._trigger_reconnection(connection_id)
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error for {connection_id}: {e}")

    async def _trigger_reconnection(self, connection_id: str):
        """Trigger reconnection for a failed connection"""
        if connection_id in self._reconnect_tasks:
            return  # Already reconnecting
            
        self._reconnect_tasks[connection_id] = asyncio.create_task(
            self._reconnect_loop(connection_id)
        )

    async def _reconnect_loop(self, connection_id: str):
        """Attempt to reconnect a failed connection"""
        metadata = self.connection_metadata.get(connection_id)
        if not metadata:
            return
            
        for attempt in range(self.reconnect_attempts):
            try:
                logger.info(f"Reconnection attempt {attempt + 1} for {connection_id}")
                await asyncio.sleep(self.reconnect_delay * (2 ** attempt))  # Exponential backoff
                
                # Try to reconnect to ElevenLabs
                agent_id = metadata.get("agent_id")
                if agent_id:
                    ssl_context = self._create_ssl_context()
                    elevenlabs_url = f"{self.base_url}?agent_id={agent_id}"
                    
                    try:
                        elevenlabs_ws = await websockets.connect(
                            elevenlabs_url,
                            additional_headers={"xi-api-key": self.api_key},
                            ssl=ssl_context,
                        )
                        
                        # Update connection
                        self.elevenlabs_connections[connection_id] = elevenlabs_ws
                        metadata["status"] = "reconnected"
                        metadata["last_reconnect"] = datetime.utcnow()
                        
                        # Restart message forwarding
                        asyncio.create_task(self._forward_messages(connection_id))
                        
                        logger.info(f"Successfully reconnected {connection_id}")
                        return
                        
                    except Exception as e:
                        logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                        
            except Exception as e:
                logger.error(f"Reconnection error for {connection_id}: {e}")
        
        # All reconnection attempts failed
        logger.error(f"Failed to reconnect {connection_id} after {self.reconnect_attempts} attempts")
        await self.close_connection(connection_id)

    async def create_connection(
        self,
        websocket: StarletteWebSocket,
        agent_id: str,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        enable_client_forwarding: bool = True,
    ) -> str:
        """Create a new WebSocket connection to ElevenLabs"""
        connection_id = str(uuid.uuid4())

        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "agent_id": agent_id,
            "session_id": session_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "enable_client_forwarding": enable_client_forwarding,
            "status": "connecting",
        }

        try:
            ssl_context = self._create_ssl_context()
            elevenlabs_url = f"{self.base_url}?agent_id={agent_id}"

            try:
                elevenlabs_ws = await websockets.connect(
                    elevenlabs_url,
                    additional_headers={"xi-api-key": self.api_key},
                    ssl=ssl_context,
                )
            except ssl.SSLError as ssl_error:
                logger.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                insecure = ssl.create_default_context()
                insecure.check_hostname = False
                insecure.verify_mode = ssl.CERT_NONE
                elevenlabs_ws = await websockets.connect(
                    elevenlabs_url,
                    additional_headers={"xi-api-key": self.api_key},
                    ssl=insecure,
                )

            self.elevenlabs_connections[connection_id] = elevenlabs_ws
            self.connection_metadata[connection_id]["status"] = "connected"
            self._ready[connection_id] = asyncio.Event()

            # ✅ Send proper ConvAI initiation envelope with required fields
            await elevenlabs_ws.send(json.dumps({
                "type": "conversation_initiation_client_data",
                "conversation_config": {
                    "turn_detection": {
                        "type": "server_vad",  # Use server-side VAD
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 800
                    }
                }
            }))

            # Start bi-directional forwarding
            asyncio.create_task(self._forward_messages(connection_id))
            
            # Start heartbeat to keep connection alive
            await self._start_heartbeat(connection_id)
            
            logger.info(f"WebSocket connection {connection_id} established for agent {agent_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}")
            await self.close_connection(connection_id)
            
            # Check if it's an agent not found error
            if "does not exist" in str(e) or "agent" in str(e).lower():
                raise ValueError(f"ElevenLabs agent '{agent_id}' not found. Please create an agent first using 'python create_elevenlabs_agent.py'")
            else:
                raise

    async def _forward_messages(self, connection_id: str):
        client_ws = self.active_connections.get(connection_id)
        elevenlabs_ws = self.elevenlabs_connections.get(connection_id)
        if not client_ws or not elevenlabs_ws:
            return

        tasks = [asyncio.create_task(self._forward_elevenlabs_to_client(connection_id))]
        if self.connection_metadata.get(connection_id, {}).get("enable_client_forwarding", True):
            tasks.append(asyncio.create_task(self._forward_client_to_elevenlabs(connection_id)))

        # Do not cancel the other task when one fails; let each run independently.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Forwarding task error on {connection_id}: {r}")


    async def _forward_client_to_elevenlabs(self, connection_id: str):
        """Forward messages from your app client (Starlette WS) to ElevenLabs"""
        client_ws = self.active_connections.get(connection_id)
        elevenlabs_ws = self.elevenlabs_connections.get(connection_id)
        if not client_ws or not elevenlabs_ws:
            return

        while True:
            try:
                # Expect JSON text from browser/client
                msg_text = await client_ws.receive_text()
            except WebSocketDisconnect:
                logger.info(f"Client connection {connection_id} disconnected")
                break
            except RuntimeError:
                # underlying connection already closed
                break
            except Exception as e:
                logger.error(f"Error receiving from client {connection_id}: {e}")
                break

            try:
                data = json.loads(msg_text)
            except json.JSONDecodeError:
                logger.warning("Non-JSON message from client ignored")
                continue

            # Accept both new 'type' and legacy 'message_type'
            t = (data.get("type") or data.get("message_type") or "").lower()

            try:
                # Gate anything except pongs until ElevenLabs sends initiation metadata
                if t in ("user_audio_chunk", "user_message", "contextual_update", "user_activity"):
                    ready_evt = self._ready.get(connection_id)
                    if ready_evt is not None:
                        await ready_evt.wait()
                if t == "user_audio_chunk":
                    # Expect base64 string from client
                    b64 = data.get("audio_base_64") or data.get("audio_chunk")  # be flexible
                    if not isinstance(b64, str):
                        continue
                    await elevenlabs_ws.send(json.dumps({
                        "user_audio_chunk": b64
                    }))

                elif t == "user_message":
                    text = data.get("text", "")
                    await elevenlabs_ws.send(json.dumps({
                        "type": "user_message",
                        "text": text
                    }))

                elif t == "pong":
                    await elevenlabs_ws.send(json.dumps({"type": "pong"}))

                elif t == "contextual_update":
                    await elevenlabs_ws.send(json.dumps({
                        "type": "contextual_update",
                        "context": data.get("context", {})
                    }))

                elif t == "user_activity":
                    # If you really need this, mirror Eleven's expected shape.
                    await elevenlabs_ws.send(json.dumps({
                        "type": "user_activity",
                        "activity_type": data.get("activity_type", "unknown"),
                        "timestamp": data.get("timestamp", time.time()),
                    }))

                else:
                    # Unknown type from client; ignore to avoid closing the remote
                    logger.debug(f"Ignoring client event with type={t!r}")

            except Exception as e:
                logger.error(f"Error forwarding client->ElevenLabs ({t}): {e}")
                break

    async def _forward_elevenlabs_to_client(self, connection_id: str):
        """Forward messages from ElevenLabs to your app client (Starlette WS)"""
        client_ws = self.active_connections.get(connection_id)
        elevenlabs_ws = self.elevenlabs_connections.get(connection_id)
        if not client_ws or not elevenlabs_ws:
            logger.warning(f"Missing connections for forwarding: client={client_ws is not None}, elevenlabs={elevenlabs_ws is not None}")
            return

        logger.info(f"Starting ElevenLabs->Client forwarding for connection {connection_id}")
        try:
            async for message in elevenlabs_ws:
                # ElevenLabs typically sends JSON text with base64 audio inside.
                if isinstance(message, (bytes, bytearray)):
                    # If they ever send raw bytes (unlikely), wrap safely for the client.
                    payload = {
                        "type": "binary_frame",
                        "payload_base64": base64.b64encode(message).decode("ascii")
                    }
                    await client_ws.send_text(json.dumps(payload))
                    continue

                # message is str (JSON)
                try:
                    event = json.loads(message)
                except json.JSONDecodeError:
                    # Pass through as text if not JSON
                    await client_ws.send_text(message)
                    continue

                etype = (event.get("type") or "").lower()
                
                # Handle audio responses
                if etype in ("agent_response", "audio_response"):
                    # Check if this is an audio response with base64 data
                    audio_base64 = event.get("audio_base_64") or event.get("audio")
                    if audio_base64:
                        is_final = event.get("is_final", False) or event.get("event") == "response_end"
                        self._save_audio_chunk(connection_id, audio_base64, is_final)
                    
                    # Check for transcript in the same event
                    transcript = event.get("transcript") or event.get("text")
                    if transcript:
                        is_final = event.get("is_final", False) or event.get("event") == "response_end"
                        self._save_transcript(connection_id, transcript, is_final)

                # Handle separate transcript events
                elif etype == "transcript":
                    transcript = event.get("text") or event.get("transcript")
                    if transcript:
                        is_final = event.get("is_final", False) or event.get("event") == "response_end"
                        self._save_transcript(connection_id, transcript, is_final)

                if etype == "conversation_initiation_metadata":
                    evt = self._ready.get(connection_id)
                    if evt and not evt.is_set():
                        evt.set()

                if etype == "ping":
                    # Respond to ElevenLabs ping with event_id if provided
                    ping_event = event.get("ping_event", {})
                    pong_response = {"type": "pong"}
                    if "event_id" in ping_event:
                        pong_response["event_id"] = ping_event["event_id"]
                    try:
                        await elevenlabs_ws.send(json.dumps(pong_response))
                    except Exception as e:
                        logger.warning(f"Failed to send pong: {e}")

                # Log the message type for debugging
                logger.info(f"Forwarding ElevenLabs message to client: type={etype}")
                
                # Pass-through the **exact** JSON we received so the client sees the real schema
                await client_ws.send_text(message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"ElevenLabs connection {connection_id} closed")
        except Exception as e:
            logger.error(f"Error forwarding ElevenLabs->client: {e}")

    # ---------- Convenience senders (optional) ----------

    async def send_audio_chunk(self, connection_id: str, audio_data: bytes, timestamp: Optional[float] = None):
        """Send an audio frame to ElevenLabs (wrap as base64 JSON)."""
        if connection_id not in self.elevenlabs_connections:
            raise ValueError(f"Connection {connection_id} not found")
        b64 = base64.b64encode(audio_data).decode("ascii")
        payload = {
            "user_audio_chunk": b64
        }
        await self.elevenlabs_connections[connection_id].send(json.dumps(payload))

    async def send_text_message(self, connection_id: str, text: str, timestamp: Optional[float] = None):
        if connection_id not in self.elevenlabs_connections:
            raise ValueError(f"Connection {connection_id} not found")
        payload = {
            "type": "user_message",
            "text": text
        }
        await self.elevenlabs_connections[connection_id].send(json.dumps(payload))

    async def send_user_activity(self, connection_id: str, activity_type: str, timestamp: Optional[float] = None):
        if connection_id not in self.elevenlabs_connections:
            raise ValueError(f"Connection {connection_id} not found")
        payload = {
            "type": "user_activity",
            "activity_type": activity_type,
            "timestamp": timestamp or time.time()
        }
        await self.elevenlabs_connections[connection_id].send(json.dumps(payload))

    # ---------- Robust, idempotent close ----------

    async def close_connection(self, connection_id: str):
        """Close both ends; safe if already closed elsewhere."""
        # Cancel heartbeat task
        heartbeat_task = self._heartbeat_tasks.pop(connection_id, None)
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Cancel reconnect task
        reconnect_task = self._reconnect_tasks.pop(connection_id, None)
        if reconnect_task:
            reconnect_task.cancel()
            try:
                await reconnect_task
            except asyncio.CancelledError:
                pass

        # Close client connection
        client_ws = self.active_connections.pop(connection_id, None)
        if client_ws:
            try:
                await client_ws.close()
            except Exception:
                pass

        # Close ElevenLabs connection
        elevenlabs_ws = self.elevenlabs_connections.pop(connection_id, None)
        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
            except Exception:
                pass

        self.connection_metadata.pop(connection_id, None)
        self._ready.pop(connection_id, None)
        self.audio_chunks.pop(connection_id, None)
        self.transcript_data.pop(connection_id, None)
        logger.info(f"WebSocket connection {connection_id} closed")

    # ---------- Introspection ----------

    def get_connection_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        return self.connection_metadata.get(connection_id)

    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        return self.connection_metadata.copy()

    async def shutdown(self):
        """Gracefully shutdown all connections and tasks"""
        logger.info("Shutting down ElevenLabs WebSocket service...")
        
        # Close all connections
        connection_ids = list(self.connection_metadata.keys())
        for connection_id in connection_ids:
            await self.close_connection(connection_id)
        
        logger.info("ElevenLabs WebSocket service shutdown complete")
