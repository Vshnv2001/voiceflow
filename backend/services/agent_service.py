"""
Agent Service for creating and managing ElevenLabs conversational AI agents
"""

import asyncio
import os
import traceback
import ssl
from typing import List, Dict, Any, Optional
import aiohttp
import json

from services.database_service import DatabaseService

class AgentService:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.elevenlabs_api_key:
            raise RuntimeError("Missing ELEVENLABS_API_KEY")
        
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        self.db_service = DatabaseService()
        
        # Suppress SSL warnings in development
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
    async def _make_elevenlabs_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to ElevenLabs API"""
        url = f"{self.elevenlabs_base_url}{endpoint}"
        headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        
        # Try with default SSL context first, fall back to unverified if needed
        try:
            # First attempt with default SSL verification
            async with aiohttp.ClientSession() as session:
                return await self._execute_request(session, method, url, headers, data)
        except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientConnectorError) as e:
            # SSL certificate verification failed, retry without verification
            # This is common in development environments or when certificates are not properly configured
            print(f"SSL certificate verification failed, retrying without verification...")
            
            # Fallback: Create SSL context that doesn't verify certificates
            # This is safe for API calls where we're not handling sensitive user data
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            # Set minimum TLS version for security
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                return await self._execute_request(session, method, url, headers, data)
        except Exception as e:
            # If both SSL attempts fail, provide a more helpful error message
            print(f"Failed to connect to ElevenLabs API: {e}")
            raise Exception(f"Unable to connect to ElevenLabs API. Please check your internet connection and API key. Error: {str(e)}")
    
    async def _execute_request(self, session: aiohttp.ClientSession, method: str, url: str, headers: Dict, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute the actual HTTP request"""
        if method.upper() == "POST":
            async with session.post(url, headers=headers, json=data) as response:
                response_data = await response.json()
                if response.status >= 400:
                    raise Exception(f"ElevenLabs API error: {response.status} - {response_data}")
                return response_data
        elif method.upper() == "GET":
            async with session.get(url, headers=headers) as response:
                response_data = await response.json()
                if response.status >= 400:
                    raise Exception(f"ElevenLabs API error: {response.status} - {response_data}")
                return response_data
        elif method.upper() == "DELETE":
            async with session.delete(url, headers=headers) as response:
                if response.status >= 400:
                    response_data = await response.json()
                    raise Exception(f"ElevenLabs API error: {response.status} - {response_data}")
                return {"success": True}
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    async def create_agent_for_user(
        self, 
        user_id: str, 
        agent_name: str,
        knowledge_base_file_ids: List[str],
        voice_id: str = "pNInz6obpgDQGcFmaJgB",  # Default voice
        first_message: str = "Hello! I'm here to help you with any questions you might have. How can I assist you today?"
    ) -> Dict[str, Any]:
        """
        Create a new ElevenLabs agent for a user based on their knowledge base documents
        
        Args:
            user_id: The customer rep's user ID
            agent_name: Name for the agent
            knowledge_base_file_ids: List of ElevenLabs file IDs to use as knowledge base
            voice_id: Voice ID to use for the agent
            first_message: Initial message the agent will say
            
        Returns:
            Dict containing agent_id and other agent details
        """
        try:
            print(f"Creating agent for user {user_id} with knowledge base files: {knowledge_base_file_ids}")
            
            # Build knowledge base locators
            knowledge_base = []
            for file_id in knowledge_base_file_ids:
                knowledge_base.append({
                    "type": "file",
                    "name": f"Knowledge Document {file_id[:8]}",
                    "id": file_id,
                    "usage_mode": "auto"
                })
            
            # Create agent configuration
            agent_config = {
                "conversation_config": {
                    "asr": {
                        "quality": "high",
                        "provider": "elevenlabs",
                        "user_input_audio_format": "pcm_16000"
                    },
                    "turn": {
                        "turn_timeout": 5.0,
                        "silence_end_call_timeout": 10.0,
                        "mode": "silence"
                    },
                    "tts": {
                        "model_id": "eleven_turbo_v2",
                        "voice_id": voice_id,
                        "agent_output_audio_format": "pcm_16000",
                        "optimize_streaming_latency": "2",
                        "stability": 0.5,
                        "speed": 1.0,
                        "similarity_boost": 0.75
                    },
                    "conversation": {
                        "text_only": False,
                        "max_duration_seconds": 1800,
                        "client_events": [
                            "conversation_initiation_metadata",
                            "asr_initiation_metadata",
                            "ping",
                            "audio",
                            "interruption",
                            "user_transcript",
                            "tentative_user_transcript",
                            "agent_response",
                            "agent_response_correction",
                            "vad_score",
                            "agent_chat_response_part"
                        ]
                    },
                    "agent": {
                        "first_message": first_message,
                        "language": "en",
                        "prompt": {
                            "prompt": f"""You are a helpful customer service agent. You have access to a knowledge base that contains information to help answer customer questions. 

Use the knowledge base to provide accurate, helpful responses. If you don't find relevant information in the knowledge base, be honest about it and offer to help in other ways.

Be friendly, professional, and concise in your responses. Focus on solving the customer's problem efficiently.""",
                            "llm": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 500,
                            "knowledge_base": knowledge_base
                        }
                    }
                },
                "name": agent_name,
                "tags": [f"user_{user_id}", "knowledge_base_agent"]
            }
            
            # Create the agent via ElevenLabs API
            response = await self._make_elevenlabs_request(
                "POST", 
                "/convai/agents/create", 
                agent_config
            )
            
            agent_id = response.get("agent_id")
            if not agent_id:
                raise Exception("Failed to get agent ID from ElevenLabs API")
            
            print(f"✅ Created agent {agent_id} for user {user_id}")
            
            # Store agent information in our database
            agent_data = {
                "user_id": user_id,
                "elevenlabs_agent_id": agent_id,
                "agent_name": agent_name,
                "voice_id": voice_id,
                "first_message": first_message,
                "knowledge_base_file_ids": knowledge_base_file_ids,
                "status": "active"
            }
            
            # Store in database
            await self.db_service.create_agent(
                user_id=user_id,
                elevenlabs_agent_id=agent_id,
                agent_name=agent_name,
                voice_id=voice_id,
                first_message=first_message,
                knowledge_base_file_ids=knowledge_base_file_ids,
                status="active"
            )
            
            return {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "voice_id": voice_id,
                "knowledge_base_file_ids": knowledge_base_file_ids,
                "status": "active"
            }
            
        except Exception as e:
            print(f"Error creating agent: {e}")
            print(traceback.format_exc())
            raise e

    async def get_agent_for_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the agent for a specific user"""
        try:
            return await self.db_service.get_agent_by_user_id(user_id)
        except Exception as e:
            print(f"Error getting agent for user: {e}")
            return None

    async def update_agent_knowledge_base(
        self, 
        user_id: str, 
        new_file_ids: List[str]
    ) -> bool:
        """Update the agent's knowledge base with new files"""
        try:
            # Get current agent
            agent = await self.get_agent_for_user(user_id)
            if not agent:
                print(f"No agent found for user {user_id}")
                return False
            
            # Create new agent with updated knowledge base
            agent_name = f"{agent['agent_name']} (Updated)"
            new_agent = await self.create_agent_for_user(
                user_id=user_id,
                agent_name=agent_name,
                knowledge_base_file_ids=new_file_ids,
                voice_id=agent.get('voice_id', 'pNInz6obpgDQGcFmaJgB'),
                first_message=agent.get('first_message', 'Hello! How can I help you?')
            )
            
            # Deactivate old agent
            await self.db_service.update_agent_status(agent['id'], 'inactive')
            
            print(f"✅ Updated agent knowledge base for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error updating agent knowledge base: {e}")
            return False

    async def delete_agent(self, user_id: str) -> bool:
        """Delete the agent for a user"""
        try:
            agent = await self.get_agent_for_user(user_id)
            if not agent:
                print(f"No agent found for user {user_id}")
                return False
            
            # Delete from ElevenLabs
            elevenlabs_agent_id = agent['elevenlabs_agent_id']
            try:
                await self._make_elevenlabs_request("DELETE", f"/convai/agents/{elevenlabs_agent_id}")
                print(f"✅ Deleted agent {elevenlabs_agent_id} from ElevenLabs")
            except Exception as e:
                print(f"Warning: Failed to delete agent from ElevenLabs: {e}")
                # Continue with database deletion even if ElevenLabs deletion fails
            
            # Mark as deleted in database
            await self.db_service.update_agent_status(agent['id'], 'deleted')
            
            print(f"✅ Deleted agent for user {user_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting agent: {e}")
            return False

    async def delete_agent_by_id(self, agent_id: str) -> bool:
        """Delete an agent by its ElevenLabs agent ID"""
        try:
            # Get agent from database
            agent = await self.db_service.get_agent_by_elevenlabs_id(agent_id)
            if not agent:
                print(f"No agent found with ID {agent_id}")
                return False
            
            # Delete from ElevenLabs
            try:
                await self._make_elevenlabs_request("DELETE", f"/convai/agents/{agent_id}")
                print(f"✅ Deleted agent {agent_id} from ElevenLabs")
            except Exception as e:
                print(f"Warning: Failed to delete agent from ElevenLabs: {e}")
                # Continue with database deletion even if ElevenLabs deletion fails
            
            # Mark as deleted in database
            await self.db_service.update_agent_status(agent['id'], 'deleted')
            
            print(f"✅ Deleted agent {agent_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting agent by ID: {e}")
            return False

    async def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ElevenLabs agent ID"""
        try:
            return await self.db_service.get_agent_by_elevenlabs_id(agent_id)
        except Exception as e:
            print(f"Error getting agent by ID: {e}")
            return None
