"""
Agent Control Manager

Manages agent-controlled responses where agents can review and approve
AI-generated responses before sending them to customers.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, List
from fastapi import WebSocket
from collections import defaultdict

logger = logging.getLogger(__name__)


class AgentControlManager:
    """
    Manages the flow of AI responses through agent approval.
    
    Flow:
    1. AI generates response (text + audio)
    2. Text is sent to agent for review
    3. Audio is buffered
    4. Agent approves/edits and sends
    5. Audio is streamed to customer
    """
    
    def __init__(self):
        # Store pending responses: {session_id: {'text': str, 'original_text': str, 'audio_chunks': [str]}}
        self.pending_responses: Dict[str, dict] = {}
        
        # Store agent websocket connections: {session_id: WebSocket}
        self.agent_connections: Dict[str, WebSocket] = {}
        
        # Store customer websocket connections: {session_id: WebSocket}
        self.customer_connections: Dict[str, WebSocket] = {}
        
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
    
    async def register_agent_connection(self, session_id: str, websocket: WebSocket):
        """Register an agent's WebSocket connection for a session"""
        async with self.lock:
            self.agent_connections[session_id] = websocket
            logger.info(f"✅ Agent connected for session: {session_id}")
    
    async def unregister_agent_connection(self, session_id: str):
        """Unregister an agent's WebSocket connection"""
        async with self.lock:
            if session_id in self.agent_connections:
                del self.agent_connections[session_id]
                logger.info(f"❌ Agent disconnected for session: {session_id}")
    
    async def register_customer_connection(self, session_id: str, websocket: WebSocket):
        """Register a customer's WebSocket connection for a session"""
        async with self.lock:
            self.customer_connections[session_id] = websocket
            logger.info(f"✅ Customer connection registered for session: {session_id}")
    
    async def unregister_customer_connection(self, session_id: str):
        """Unregister a customer's WebSocket connection"""
        async with self.lock:
            if session_id in self.customer_connections:
                del self.customer_connections[session_id]
                logger.info(f"❌ Customer disconnected for session: {session_id}")
    
    async def buffer_agent_response(self, session_id: str, text: str):
        """
        Buffer an agent response text for review.
        Audio chunks will be added separately.
        """
        async with self.lock:
            if session_id not in self.pending_responses:
                self.pending_responses[session_id] = {
                    'text': '',
                    'original_text': '',
                    'audio_chunks': []
                }
            
            self.pending_responses[session_id]['text'] = text
            self.pending_responses[session_id]['original_text'] = text  # Store original for comparison
            logger.info(f"📝 Buffered agent response text for session {session_id}: {text[:50]}...")
        
        # Send suggestion to agent
        await self.send_suggestion_to_agent(session_id, text)
    
    async def buffer_audio_chunk(self, session_id: str, audio_base64: str):
        """Buffer an audio chunk for the pending response"""
        async with self.lock:
            if session_id not in self.pending_responses:
                self.pending_responses[session_id] = {
                    'text': '',
                    'audio_chunks': []
                }
            
            self.pending_responses[session_id]['audio_chunks'].append(audio_base64)
            chunk_count = len(self.pending_responses[session_id]['audio_chunks'])
            logger.debug(f"🔊 Buffered audio chunk for session {session_id} (total: {chunk_count})")
    
    async def send_suggestion_to_agent(self, session_id: str, text: str):
        """Send suggested response text to agent's WebSocket"""
        async with self.lock:
            if session_id in self.agent_connections:
                agent_ws = self.agent_connections[session_id]
                try:
                    await agent_ws.send_json({
                        'type': 'suggested_response',
                        'text': text
                    })
                    logger.info(f"💡 Sent suggestion to agent for session {session_id}")
                except Exception as e:
                    logger.error(f"Error sending suggestion to agent: {e}")
    
    async def approve_and_send_response(self, session_id: str, approved_text: str) -> bool:
        """
        Agent approves and sends the response.
        Streams buffered audio to customer.
        
        Args:
            session_id: The session ID
            approved_text: The text approved by the agent (may be edited)
            
        Returns:
            bool: True if successful, False otherwise
        """
        async with self.lock:
            # Get buffered audio
            if session_id not in self.pending_responses:
                logger.warning(f"No pending response for session {session_id}")
                return False
            
            audio_chunks = self.pending_responses[session_id]['audio_chunks']
            
            # Get customer connection
            if session_id not in self.customer_connections:
                logger.warning(f"No customer connection for session {session_id}")
                return False
            
            customer_ws = self.customer_connections[session_id]
        
        # Stream audio to customer
        logger.info(f"🎵 Streaming {len(audio_chunks)} audio chunks to customer for session {session_id}")
        
        try:
            for audio_chunk in audio_chunks:
                await customer_ws.send_json({
                    'type': 'audio',
                    'audio_event': {
                        'audio_base_64': audio_chunk
                    }
                })
                # Small delay to avoid overwhelming the connection
                await asyncio.sleep(0.01)
            
            # Clear pending response
            async with self.lock:
                if session_id in self.pending_responses:
                    del self.pending_responses[session_id]
            
            logger.info(f"✅ Successfully sent response to customer for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending response to customer: {e}")
            return False
    
    async def get_pending_response(self, session_id: str) -> Optional[dict]:
        """Get the pending response for a session"""
        async with self.lock:
            return self.pending_responses.get(session_id)
    
    async def get_original_text(self, session_id: str) -> Optional[str]:
        """Get the original suggested text for comparison"""
        async with self.lock:
            if session_id in self.pending_responses:
                return self.pending_responses[session_id].get('original_text')
            return None


# Global instance
agent_control_manager = AgentControlManager()

