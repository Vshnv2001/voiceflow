# services/elevenlabs_websocket_service.py

import asyncio
import json
import base64
import time
from typing import Dict, Any, Optional
import websockets
import logging
from datetime import datetime
import uuid
import ssl
import certifi

from starlette.websockets import WebSocket as StarletteWebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ElevenLabsWebSocketService:
    """Service for managing ElevenLabs WebSocket connections"""

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

    async def create_connection(
        self,
        websocket: StarletteWebSocket,
        agent_id: str,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
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
            logger.info(f"WebSocket connection {connection_id} established for agent {agent_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}")
            await self.close_connection(connection_id)
            raise

    async def _forward_messages(self, connection_id: str):
        """Forward messages between client and ElevenLabs"""
        try:
            client_ws = self.active_connections.get(connection_id)
            elevenlabs_ws = self.elevenlabs_connections.get(connection_id)
            if not client_ws or not elevenlabs_ws:
                return

            client_to_elevenlabs = asyncio.create_task(self._forward_client_to_elevenlabs(connection_id))
            elevenlabs_to_client = asyncio.create_task(self._forward_elevenlabs_to_client(connection_id))

            done, pending = await asyncio.wait(
                [client_to_elevenlabs, elevenlabs_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        except Exception as e:
            logger.error(f"Error in message forwarding for connection {connection_id}: {e}")
        finally:
            await self.close_connection(connection_id)

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
                        "type": "user_audio_chunk",
                        "audio_base_64": b64
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
            return

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
            "type": "user_audio_chunk",
            "audio_base_64": b64
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
        client_ws = self.active_connections.pop(connection_id, None)
        if client_ws:
            try:
                await client_ws.close()
            except Exception:
                pass

        elevenlabs_ws = self.elevenlabs_connections.pop(connection_id, None)
        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
            except Exception:
                pass

        self.connection_metadata.pop(connection_id, None)
        logger.info(f"WebSocket connection {connection_id} closed")

    # ---------- Introspection ----------

    def get_connection_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        return self.connection_metadata.get(connection_id)

    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        return self.connection_metadata.copy()

    async def cleanup_stale_connections(self):
        now = time.time()
        for connection_id, meta in list(self.connection_metadata.items()):
            created_at = meta.get("created_at")
            if created_at and (now - created_at.timestamp()) > 3600:
                await self.close_connection(connection_id)
                logger.info(f"Cleaned up stale connection {connection_id}")
