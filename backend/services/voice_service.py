"""
Voice processing service for handling ElevenLabs integration
"""

import asyncio
import aiohttp
import os
from typing import Optional, Dict, Any, List
import base64
from io import BytesIO
from services.database_service import DatabaseService

class VoiceService:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        self.default_voice_id = os.getenv("DEFAULT_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam voice
        self.db_service = DatabaseService()
        
    async def upload_audio(self, audio_file) -> str:
        """Upload audio file to storage and return URL"""
        # In a real implementation, you'd upload to Supabase Storage or AWS S3
        # For now, we'll simulate this
        file_id = f"audio_{asyncio.get_event_loop().time()}.wav"
        # This would be the actual storage URL
        return f"https://your-storage-bucket.com/audio/{file_id}"
    
    async def transcribe_audio(self, audio_url: str) -> str:
        """Transcribe audio using ElevenLabs Speech-to-Text"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.elevenlabs_api_key,
                    "Content-Type": "application/json"
                }
                
                # Download audio file
                async with session.get(audio_url) as response:
                    audio_data = await response.read()
                
                # For ElevenLabs, you might need to use a different endpoint
                # This is a placeholder - ElevenLabs primarily does TTS, not STT
                # You might want to use OpenAI Whisper or Google Speech-to-Text instead
                
                # For now, return a mock transcription
                return "This is a mock transcription of the voice message."
                
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def synthesize_audio(self, text: str, voice_id: Optional[str] = None) -> str:
        """Convert text to speech using ElevenLabs"""
        try:
            voice_id = voice_id or self.default_voice_id
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.elevenlabs_base_url}/text-to-speech/{voice_id}"
                headers = {
                    "xi-api-key": self.elevenlabs_api_key,
                    "Content-Type": "application/json"
                }
                
                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5
                    }
                }
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        # Save audio and return URL
                        audio_url = await self._save_audio(audio_data)
                        return audio_url
                    else:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error: {error_text}")
                        
        except Exception as e:
            print(f"Error synthesizing audio: {e}")
            raise Exception(f"Audio synthesis failed: {str(e)}")
    
    async def _save_audio(self, audio_data: bytes) -> str:
        """Save audio data to storage and return URL"""
        # In a real implementation, save to Supabase Storage or AWS S3
        file_id = f"synthesized_{asyncio.get_event_loop().time()}.mp3"
        return f"https://your-storage-bucket.com/audio/{file_id}"
    
    async def get_voice_models(self) -> list:
        """Get available voice models from ElevenLabs"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.elevenlabs_base_url}/models"
                headers = {"xi-api-key": self.elevenlabs_api_key}
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("models", [])
                    else:
                        return []
                        
        except Exception as e:
            print(f"Error fetching voice models: {e}")
            return []
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices from database"""
        try:
            voices = await self.db_service.get_available_voices()
            return voices
        except Exception as e:
            print(f"Error fetching available voices: {e}")
            return []
    
    async def get_voice_by_id(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific voice by ID"""
        try:
            voice = await self.db_service.get_voice_by_id(voice_id)
            return voice
        except Exception as e:
            print(f"Error fetching voice: {e}")
            return None
    
    async def get_voices_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get voices by category (male, female, etc.)"""
        try:
            voices = await self.db_service.get_voices_by_category(category)
            return voices
        except Exception as e:
            print(f"Error fetching voices by category: {e}")
            return []
    
    async def get_default_voice(self) -> Optional[Dict[str, Any]]:
        """Get the default voice"""
        try:
            # First try to get from system config
            config = await self.db_service.get_system_config()
            default_voice_id = config.get('default_voice_id', self.default_voice_id)
            
            # Get voice details
            voice = await self.get_voice_by_id(default_voice_id)
            return voice
        except Exception as e:
            print(f"Error getting default voice: {e}")
            return None
    
    async def select_voice_for_message(self, message_id: str, voice_preference: Optional[str] = None) -> str:
        """Select appropriate voice for a message"""
        try:
            # Get message context
            message = await self.db_service.get_message(message_id)
            if not message:
                return self.default_voice_id
            
            # For now, use default voice or user preference
            if voice_preference:
                voice = await self.get_voice_by_id(voice_preference)
                if voice:
                    return voice_preference
            
            # Use default voice
            default_voice = await self.get_default_voice()
            return default_voice['voice_id'] if default_voice else self.default_voice_id
            
        except Exception as e:
            print(f"Error selecting voice: {e}")
            return self.default_voice_id
