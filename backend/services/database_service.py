"""
Database service for Supabase operations
"""

import asyncio
from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

class DatabaseService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    # ==================== SESSION OPERATIONS ====================
    
    async def create_session(
        self, 
        user_id: str, 
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new session"""
        try:
            data = {
                "user_id": user_id,
                "customer_id": customer_id,
                "status": "active",
                "metadata": metadata or {}
            }
            
            result = self.supabase.table("sessions").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating session: {e}")
            raise Exception(f"Failed to create session: {str(e)}")
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID"""
        try:
            result = self.supabase.table("sessions").select("*").eq("id", session_id).eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    async def get_sessions(
        self, 
        user_id: str, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's sessions with optional filtering"""
        try:
            query = self.supabase.table("sessions").select("*").eq("user_id", user_id)
            
            if status:
                query = query.eq("status", status)
            
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data
            
        except Exception as e:
            print(f"Error getting sessions: {e}")
            return []
    
    async def update_session(
        self, 
        session_id: str, 
        user_id: str, 
        **updates
    ) -> bool:
        """Update a session"""
        try:
            result = self.supabase.table("sessions").update(updates).eq("id", session_id).eq("user_id", user_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error updating session: {e}")
            return False
        
    async def close_session(self, session_id: str, user_id: str) -> bool:
        """Close a session"""
        try:
            result = self.supabase.table("sessions").update({"status": "closed"}).eq("id", session_id).eq("user_id", user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error closing session: {e}")
            return False
    
    # ==================== MESSAGE OPERATIONS ====================
    
    async def create_message(
        self,
        session_id: str,
        sender_type: str,
        message_type: str,
        **message_data
    ) -> Dict[str, Any]:
        """Create a new message"""
        try:
            data = {
                "session_id": session_id,
                "sender_type": sender_type,
                "message_type": message_type,
                **message_data
            }
            
            result = self.supabase.table("messages").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating message: {e}")
            raise Exception(f"Failed to create message: {str(e)}")
    
    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a message by ID"""
        try:
            result = self.supabase.table("messages").select("*").eq("id", message_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting message: {e}")
            return None
    
    async def get_messages(
        self, 
        session_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        try:
            result = self.supabase.table("messages").select("*").eq("session_id", session_id).order("created_at", desc=False).range(offset, offset + limit - 1).execute()
            return result.data
            
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    async def update_message(
        self, 
        message_id: str, 
        **updates
    ) -> bool:
        """Update a message"""
        try:
            result = self.supabase.table("messages").update(updates).eq("id", message_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error updating message: {e}")
            return False
    
    async def get_pending_messages(
        self, 
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages pending agent approval"""
        try:
            result = self.supabase.table("messages").select("*, sessions(*)").eq("status", "pending").eq("message_type", "ai_generated").order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data
            
        except Exception as e:
            print(f"Error getting pending messages: {e}")
            return []
    
    async def approve_message(
        self,
        message_id: str,
        agent_id: str,
        approved: bool,
        edited_content: Optional[str] = None,
        edit_reason: Optional[str] = None
    ) -> bool:
        """Approve or edit a message"""
        try:
            updates = {
                "status": "approved" if approved else "rejected",
                "approved_by": agent_id,
                "approved_at": datetime.utcnow().isoformat()
            }
            
            if edited_content:
                updates["edited_content"] = edited_content
                updates["status"] = "edited"
            
            result = self.supabase.table("messages").update(updates).eq("id", message_id).execute()
            
            # If approved, create agent response record
            if approved and edited_content:
                await self.create_agent_response(
                    message_id=message_id,
                    original_ai_response="",  # Would need to get from message
                    agent_edited_response=edited_content,
                    agent_id=agent_id,
                    edit_reason=edit_reason
                )
            
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error approving message: {e}")
            return False
    
    # ==================== VOICE PROCESSING JOB OPERATIONS ====================
    
    async def create_voice_job(
        self,
        message_id: str,
        job_type: str,
        provider: str,
        input_url: Optional[str] = None
    ) -> str:
        """Create a voice processing job"""
        try:
            data = {
                "message_id": message_id,
                "job_type": job_type,
                "provider": provider,
                "input_url": input_url
            }
            
            result = self.supabase.table("voice_processing_jobs").insert(data).execute()
            return result.data[0]["id"]
            
        except Exception as e:
            print(f"Error creating voice job: {e}")
            raise Exception(f"Failed to create voice job: {str(e)}")
    
    async def get_voice_job(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a voice processing job"""
        try:
            result = self.supabase.table("voice_processing_jobs").select("*, messages(sessions(*))").eq("id", job_id).execute()
            
            if result.data:
                # Check if user has access to this job
                job = result.data[0]
                if job["messages"]["sessions"]["user_id"] == user_id:
                    return job
            
            return None
            
        except Exception as e:
            print(f"Error getting voice job: {e}")
            return None
    
    async def update_voice_job(
        self,
        job_id: str,
        status: str,
        output_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update a voice processing job"""
        try:
            updates = {"status": status}
            
            if status == "processing":
                updates["started_at"] = datetime.utcnow().isoformat()
            elif status in ["completed", "failed"]:
                updates["completed_at"] = datetime.utcnow().isoformat()
            
            if output_url:
                updates["output_url"] = output_url
            
            if error_message:
                updates["error_message"] = error_message
            
            result = self.supabase.table("voice_processing_jobs").update(updates).eq("id", job_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error updating voice job: {e}")
            return False
    
    # ==================== AGENT RESPONSE OPERATIONS ====================
    
    async def create_agent_response(
        self,
        message_id: str,
        original_ai_response: str,
        agent_edited_response: str,
        agent_id: str,
        edit_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an agent response record"""
        try:
            data = {
                "message_id": message_id,
                "original_ai_response": original_ai_response,
                "agent_edited_response": agent_edited_response,
                "agent_id": agent_id,
                "edit_reason": edit_reason
            }
            
            result = self.supabase.table("agent_responses").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating agent response: {e}")
            raise Exception(f"Failed to create agent response: {str(e)}")
    
    # ==================== SYSTEM CONFIGURATION OPERATIONS ====================
    
    async def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration"""
        try:
            result = self.supabase.table("system_config").select("*").execute()
            config = {}
            for item in result.data:
                config[item["key"]] = item["value"]
            return config
            
        except Exception as e:
            print(f"Error getting system config: {e}")
            return {}
    
    async def update_system_config(self, config_updates: List[Dict[str, str]]) -> bool:
        """Update system configuration"""
        try:
            for update in config_updates:
                self.supabase.table("system_config").update({"value": update["value"]}).eq("key", update["key"]).execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating system config: {e}")
            return False
    
    # ==================== VOICE MANAGEMENT OPERATIONS ====================
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get all available voices"""
        try:
            result = self.supabase.table("available_voices").select("*").eq("is_active", True).order("name").execute()
            return result.data
        except Exception as e:
            print(f"Error getting available voices: {e}")
            return []
    
    async def get_voice_by_id(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific voice by ID"""
        try:
            result = self.supabase.table("available_voices").select("*").eq("voice_id", voice_id).eq("is_active", True).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting voice by ID: {e}")
            return None
    
    async def get_voices_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get voices by category"""
        try:
            result = self.supabase.table("available_voices").select("*").eq("category", category).eq("is_active", True).order("name").execute()
            return result.data
        except Exception as e:
            print(f"Error getting voices by category: {e}")
            return []
    
    async def update_voice_usage(self, voice_id: str) -> bool:
        """Update voice usage statistics (for analytics)"""
        try:
            # This could be expanded to track usage statistics
            # For now, just return success
            return True
        except Exception as e:
            print(f"Error updating voice usage: {e}")
            return False
    
    # ==================== ANALYTICS OPERATIONS ====================
    
    async def get_session_analytics(
        self, 
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics for user sessions"""
        try:
            query = self.supabase.table("sessions").select("*").eq("user_id", user_id)
            
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            result = query.execute()
            sessions = result.data
            
            # Calculate analytics
            total_sessions = len(sessions)
            active_sessions = len([s for s in sessions if s["status"] == "active"])
            closed_sessions = len([s for s in sessions if s["status"] == "closed"])
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "closed_sessions": closed_sessions,
                "sessions": sessions
            }
            
        except Exception as e:
            print(f"Error getting session analytics: {e}")
            return {"total_sessions": 0, "active_sessions": 0, "closed_sessions": 0, "sessions": []}
    
    async def get_message_analytics(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Get analytics for session messages"""
        try:
            result = self.supabase.table("messages").select("*").eq("session_id", session_id).execute()
            messages = result.data
            
            # Calculate analytics
            total_messages = len(messages)
            voice_messages = len([m for m in messages if m["message_type"] == "voice"])
            ai_messages = len([m for m in messages if m["message_type"] == "ai_generated"])
            approved_messages = len([m for m in messages if m["status"] == "approved"])
            edited_messages = len([m for m in messages if m["status"] == "edited"])
            
            return {
                "total_messages": total_messages,
                "voice_messages": voice_messages,
                "ai_messages": ai_messages,
                "approved_messages": approved_messages,
                "edited_messages": edited_messages,
                "messages": messages
            }
            
        except Exception as e:
            print(f"Error getting message analytics: {e}")
            return {"total_messages": 0, "voice_messages": 0, "ai_messages": 0, "approved_messages": 0, "edited_messages": 0, "messages": []}
