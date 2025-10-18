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
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    # ==================== SESSION OPERATIONS ====================
    
    async def create_session(
        self, 
        customer_rep_id: str, 
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new session"""
        try:
            data = {
                "customer_rep_id": customer_rep_id,
                "customer_id": customer_id,
                "status": "active",
                "metadata": metadata or {}
            }
            
            result = self.supabase.table("sessions").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating session: {e}")
            raise Exception(f"Failed to create session: {str(e)}")
    
    async def get_session(self, session_id: str, customer_rep_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID"""
        try:
            result = self.supabase.table("sessions").select("*").eq("id", session_id).eq("customer_rep_id", customer_rep_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    async def get_sessions(
        self, 
        customer_rep_id: str, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get customer rep's sessions with optional filtering"""
        try:
            query = self.supabase.table("sessions").select("*").eq("customer_rep_id", customer_rep_id)
            
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
        customer_rep_id: str, 
        **updates
    ) -> bool:
        """Update a session"""
        try:
            result = self.supabase.table("sessions").update(updates).eq("id", session_id).eq("customer_rep_id", customer_rep_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error updating session: {e}")
            return False
        
    async def close_session(self, session_id: str, customer_rep_id: str) -> bool:
        """Close a session"""
        try:
            result = self.supabase.table("sessions").update({"status": "closed"}).eq("id", session_id).eq("customer_rep_id", customer_rep_id).execute()
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
    
    async def get_voice_job(self, job_id: str, customer_rep_id: str) -> Optional[Dict[str, Any]]:
        """Get a voice processing job"""
        try:
            result = self.supabase.table("voice_processing_jobs").select("*, messages(sessions(*))").eq("id", job_id).execute()
            
            if result.data:
                # Check if customer rep has access to this job
                job = result.data[0]
                if job["messages"]["sessions"]["customer_rep_id"] == customer_rep_id:
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
            # Return default config if database access fails
            return {
                "default_voice_id": "pNInz6obpgDQGcFmaJgB",
                "ai_model": "gpt-4o-mini",
                "ai_temperature": "0.7"
            }
    
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
        customer_rep_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics for customer rep sessions"""
        try:
            query = self.supabase.table("sessions").select("*").eq("customer_rep_id", customer_rep_id)
            
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
    
    # ==================== KNOWLEDGE BASE OPERATIONS ====================
    
    async def create_knowledge_document(
        self,
        user_id: str,
        title: str,
        description: Optional[str],
        file_name: str,
        file_type: str,
        file_size: int,
        file_url: str
    ) -> Dict[str, Any]:
        """Create a knowledge document"""
        try:
            data = {
                "user_id": user_id,
                "title": title,
                "description": description,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
                "file_url": file_url,
                "status": "processing"
            }
            
            result = self.supabase.table("knowledge_documents").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating knowledge document: {e}")
            raise Exception(f"Failed to create knowledge document: {str(e)}")
    
    async def update_knowledge_document(
        self,
        document_id: str,
        content_text: Optional[str] = None,
        status: Optional[str] = None,
        processing_error: Optional[str] = None
    ) -> bool:
        """Update a knowledge document"""
        try:
            update_data = {}
            if content_text is not None:
                update_data["content_text"] = content_text
            if status is not None:
                update_data["status"] = status
            if processing_error is not None:
                update_data["processing_error"] = processing_error
            
            result = self.supabase.table("knowledge_documents").update(update_data).eq("id", document_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error updating knowledge document: {e}")
            return False
    
    async def get_knowledge_document(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a knowledge document by ID"""
        try:
            result = self.supabase.table("knowledge_documents").select("*").eq("id", document_id).eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting knowledge document: {e}")
            return None
    
    async def get_knowledge_documents(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's knowledge documents"""
        try:
            query = self.supabase.table("knowledge_documents").select("*").eq("user_id", user_id)
            
            if collection_id:
                # Join with document_collections table
                query = query.in_("id", 
                    self.supabase.table("document_collections")
                    .select("document_id")
                    .eq("collection_id", collection_id)
                    .execute()
                    .data
                )
            
            if status:
                query = query.eq("status", status)
            
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            return result.data
            
        except Exception as e:
            print(f"Error getting knowledge documents: {e}")
            return []
    
    async def delete_knowledge_document(self, document_id: str, user_id: str) -> bool:
        """Delete a knowledge document"""
        try:
            result = self.supabase.table("knowledge_documents").delete().eq("id", document_id).eq("user_id", user_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error deleting knowledge document: {e}")
            return False
    
    async def create_knowledge_chunk(
        self,
        document_id: str,
        chunk_index: int,
        content: str,
        content_length: int,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a knowledge chunk with embedding"""
        try:
            data = {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "content": content,
                "content_length": content_length,
                "embedding": embedding,
                "metadata": metadata or {}
            }
            
            result = self.supabase.table("knowledge_chunks").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating knowledge chunk: {e}")
            raise Exception(f"Failed to create knowledge chunk: {str(e)}")
    
    async def search_knowledge_chunks(
        self,
        query_embedding: List[float],
        user_id: str,
        collection_ids: Optional[List[str]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search knowledge chunks using vector similarity"""
        try:
            # Build the query with vector similarity search
            # Note: This requires pgvector extension and proper setup
            query = f"""
            SELECT 
                kc.id as chunk_id,
                kc.document_id,
                kd.title as document_title,
                kc.content,
                kc.metadata,
                1 - (kc.embedding <=> '{query_embedding}') as similarity_score
            FROM knowledge_chunks kc
            JOIN knowledge_documents kd ON kc.document_id = kd.id
            WHERE kd.user_id = '{user_id}'
            AND 1 - (kc.embedding <=> '{query_embedding}') > {similarity_threshold}
            """
            
            if collection_ids:
                collection_filter = "', '".join(collection_ids)
                query += f"""
                AND kc.document_id IN (
                    SELECT document_id FROM document_collections 
                    WHERE collection_id IN ('{collection_filter}')
                )
                """
            
            query += f"""
            ORDER BY similarity_score DESC
            LIMIT {limit}
            """
            
            result = self.supabase.rpc('execute_sql', {'query': query}).execute()
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error searching knowledge chunks: {e}")
            # Fallback to simple text search if vector search fails
            return await self._fallback_text_search(user_id, collection_ids, limit)
    
    async def _fallback_text_search(
        self,
        user_id: str,
        collection_ids: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Fallback text search when vector search is not available"""
        try:
            query = self.supabase.table("knowledge_chunks").select(
                "id, document_id, content, metadata, knowledge_documents(title)"
            ).eq("knowledge_documents.user_id", user_id).limit(limit)
            
            result = query.execute()
            return [{
                "chunk_id": chunk["id"],
                "document_id": chunk["document_id"],
                "document_title": chunk["knowledge_documents"]["title"],
                "content": chunk["content"],
                "similarity_score": 0.5,  # Default score for fallback
                "metadata": chunk["metadata"]
            } for chunk in result.data]
            
        except Exception as e:
            print(f"Error in fallback text search: {e}")
            return []
    
    async def create_knowledge_collection(
        self,
        user_id: str,
        name: str,
        description: Optional[str],
        is_public: bool = False
    ) -> Dict[str, Any]:
        """Create a knowledge collection"""
        try:
            data = {
                "user_id": user_id,
                "name": name,
                "description": description,
                "is_public": is_public
            }
            
            result = self.supabase.table("knowledge_collections").insert(data).execute()
            return result.data[0]
            
        except Exception as e:
            print(f"Error creating knowledge collection: {e}")
            raise Exception(f"Failed to create knowledge collection: {str(e)}")
    
    async def get_knowledge_collections(
        self,
        user_id: str,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's knowledge collections"""
        try:
            if include_public:
                query = self.supabase.table("knowledge_collections").select("*").or_(f"user_id.eq.{user_id},is_public.eq.true")
            else:
                query = self.supabase.table("knowledge_collections").select("*").eq("user_id", user_id)
            
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            return result.data
            
        except Exception as e:
            print(f"Error getting knowledge collections: {e}")
            return []
    
    async def delete_knowledge_collection(self, collection_id: str, user_id: str) -> bool:
        """Delete a knowledge collection"""
        try:
            result = self.supabase.table("knowledge_collections").delete().eq("id", collection_id).eq("user_id", user_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error deleting knowledge collection: {e}")
            return False
    
    async def add_document_to_collection(self, document_id: str, collection_id: str) -> bool:
        """Add a document to a collection"""
        try:
            data = {
                "document_id": document_id,
                "collection_id": collection_id
            }
            
            result = self.supabase.table("document_collections").insert(data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error adding document to collection: {e}")
            return False
    
    async def remove_document_from_collection(self, document_id: str, collection_id: str) -> bool:
        """Remove a document from a collection"""
        try:
            result = self.supabase.table("document_collections").delete().eq("document_id", document_id).eq("collection_id", collection_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error removing document from collection: {e}")
            return False