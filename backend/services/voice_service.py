"""
Voice processing service for handling ElevenLabs integration
"""

import asyncio
import aiohttp
import os
from typing import Optional, Dict, Any, List
import base64
from io import BytesIO
from elevenlabs.client import ElevenLabs
import uuid
from services.database_service import DatabaseService
from supabase import create_client, Client

class VoiceService:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        self.default_voice_id = os.getenv("DEFAULT_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam voice
        self.db_service = DatabaseService()
        
        # Initialize Supabase client for storage
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
    async def upload_audio(self, audio_file) -> str:
        """Upload audio file to Supabase Storage"""
        try:
            # Generate unique file path with proper extension
            file_extension = self._get_file_extension(audio_file.filename)
            file_path = f"audio/{uuid.uuid4()}.{file_extension}"
            
            # Read file content
            file_content = await audio_file.read()
            
            # Validate file size (optional - 50MB limit)
            max_size = 50 * 1024 * 1024  # 50MB
            if len(file_content) > max_size:
                raise Exception(f"File too large. Maximum size is {max_size // (1024*1024)}MB")
            
            # Upload to Supabase Storage
            result = self.supabase.storage.from_("audio-files").upload(file_path, file_content)
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Storage upload error: {result.error}")
            
            # Return public URL
            return f"{self.supabase_url}/storage/v1/object/public/audio-files/{file_path}"
            
        except Exception as e:
            print(f"Error uploading audio: {e}")
            raise Exception(f"Failed to upload audio: {str(e)}")
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if not filename:
            return 'wav'
        
        # Handle cases where filename might have multiple dots
        parts = filename.split('.')
        if len(parts) > 1:
            return parts[-1].lower()
        return 'wav'
        
    async def transcribe_audio(self, audio_url: str, language_code: str = "eng", diarize: bool = True) -> str:
        """Transcribe audio using ElevenLabs Speech-to-Text"""
        try:
            # Create SSL context to handle certificate issues
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Download audio file from Supabase Storage
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(audio_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download audio: {response.status}")
                    audio_data = await response.read()
            
            # Use ElevenLabs Speech-to-Text API
            # Initialize ElevenLabs client
            elevenlabs = ElevenLabs(api_key=self.elevenlabs_api_key)
            
            # Convert audio data to BytesIO for the API
            audio_file = BytesIO(audio_data)
            
            # Transcribe using ElevenLabs STT
            transcription = elevenlabs.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v1",  # Model to use, for now only "scribe_v1" is supported
                tag_audio_events=True,  # Tag audio events like laughter, applause, etc.
                language_code=language_code,  # Language of the audio file. If set to None, the model will detect the language automatically.
                diarize=diarize,  # Whether to annotate who is speaking
            )
            
            # Extract text from transcription response
            if hasattr(transcription, 'text'):
                return transcription.text
            elif isinstance(transcription, str):
                return transcription
            else:
                # Handle different response formats
                return str(transcription)
                
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
        """Save audio data to Supabase Storage and return URL"""
        try:
            # Generate unique file path
            file_path = f"synthesized/{uuid.uuid4()}.mp3"
            
            # Upload to Supabase Storage
            result = self.supabase.storage.from_("audio-files").upload(file_path, audio_data)
            
            if result.get('error'):
                raise Exception(f"Storage upload error: {result['error']}")
            
            # Return public URL
            return f"{self.supabase_url}/storage/v1/object/public/audio-files/{file_path}"
            
        except Exception as e:
            print(f"Error saving audio: {e}")
            raise Exception(f"Failed to save audio: {str(e)}")
    
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
            try:
                config = await self.db_service.get_system_config()
                default_voice_id = config.get('default_voice_id', self.default_voice_id)
            except Exception:
                # Fallback to environment variable if system config fails
                default_voice_id = self.default_voice_id
            
            # Get voice details
            voice = await self.get_voice_by_id(default_voice_id)
            return voice
        except Exception as e:
            print(f"Error getting default voice: {e}")
            return None
    
    async def select_voice_for_message(self, message_id: str, voice_preference: Optional[str] = None) -> str:
        """Select appropriate voice for a message"""
        try:
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
