"""
Knowledge Base Service for document upload, processing, and RAG functionality using ElevenLabs API
"""

import asyncio
import os
import traceback
import hashlib
import mimetypes
import ssl
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import aiohttp
import aiofiles
from io import BytesIO
import json

from services.database_service import DatabaseService
from services.agent_service import AgentService
from models.schemas import (
    KnowledgeDocumentResponse, KnowledgeChunkResponse, 
    KnowledgeCollectionResponse, RAGSearchResult, RAGSearchResponse
)

class KnowledgeService:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.elevenlabs_api_key:
            raise RuntimeError("Missing ELEVENLABS_API_KEY")
        
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        self.db_service = DatabaseService()
        self.agent_service = AgentService()
        
    async def _make_elevenlabs_request(self, method: str, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to ElevenLabs API"""
        url = f"{self.elevenlabs_base_url}{endpoint}"
        headers = {
            "xi-api-key": self.elevenlabs_api_key
        }
        
        # Try with default SSL context first, fall back to unverified if needed
        try:
            # First attempt with default SSL verification
            async with aiohttp.ClientSession() as session:
                return await self._execute_request(session, method, url, headers, data, files)
        except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientConnectorError) as e:
            print(f"SSL connection failed: {e}, retrying without verification...")
            # Fallback: Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                return await self._execute_request(session, method, url, headers, data, files)
    
    async def _execute_request(self, session: aiohttp.ClientSession, method: str, url: str, headers: Dict, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute the actual HTTP request"""
        if method.upper() == "POST":
            if files:
                # Multipart form data for file uploads
                form_data = aiohttp.FormData()
                for key, value in files.items():
                    if isinstance(value, tuple):
                        # New format: (filename, content, content_type)
                        filename, content, content_type = value
                        form_data.add_field(key, content, filename=filename, content_type=content_type)
                    else:
                        # Old format: {"content": ..., "filename": ..., "content_type": ...}
                        form_data.add_field(key, value["content"], filename=value["filename"], content_type=value.get("content_type", "application/octet-stream"))
                
                # Add additional data fields
                if data:
                    for key, value in data.items():
                        form_data.add_field(key, value)
                
                async with session.post(url, headers=headers, data=form_data) as response:
                    response_data = await response.json()
                    if response.status >= 400:
                        raise Exception(f"ElevenLabs API error: {response.status} - {response_data}")
                    return response_data
            else:
                async with session.post(url, headers=headers, json=data) as response:
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

    async def upload_document(
        self, 
        file_content: bytes, 
        file_name: str, 
        user_id: str,
        title: str,
        description: Optional[str] = None,
        collection_ids: Optional[List[str]] = None
    ) -> KnowledgeDocumentResponse:
        try:
            file_type = self._get_file_type(file_name)
            file_size = len(file_content)
            
            # Upload to ElevenLabs knowledge base
            files = {
                "file": (file_name, file_content, mimetypes.guess_type(file_name)[0] or "application/octet-stream")
            }
            data = {
                "name": title
            }
            
            response = await self._make_elevenlabs_request("POST", "/convai/knowledge-base/file", data=data, files=files)
            elevenlabs_file_id = response.get("id")
            
            if not elevenlabs_file_id:
                raise Exception("Failed to get file ID from ElevenLabs API")
            
            # Create document record in our database
            document = await self.db_service.create_knowledge_document(
                user_id=user_id,
                title=title,
                description=description,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                file_url=f"elevenlabs://{elevenlabs_file_id}",  # Store ElevenLabs reference
                elevenlabs_file_id=elevenlabs_file_id
            )

            if collection_ids:
                for collection_id in collection_ids:
                    await self.db_service.add_document_to_collection(
                        document_id=document["id"],
                        collection_id=collection_id
                    )

            # Update document status to processed (ElevenLabs handles processing)
            await self.db_service.update_knowledge_document(
                document_id=document["id"],
                status="processed"
            )
            
            # Create or update agent for this user
            await self._create_or_update_agent_for_user(user_id, elevenlabs_file_id)
            
            return document

        except Exception as e:
            print(f"Error uploading document: {e}")
            print(traceback.format_exc())
            raise e
    
    async def search_knowledge_base(
        self, 
        query: str, 
        user_id: str,
        collection_ids: Optional[List[str]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> RAGSearchResponse:
        """Search knowledge base using ElevenLabs RAG"""
        try:
            start_time = datetime.utcnow()
            
            # Note: ElevenLabs handles the search internally
            # For now, we'll return a placeholder response
            # In a real implementation, you might need to call ElevenLabs search API
            # or use their conversational AI with knowledge base context
            
            search_results = []
            
            # TODO: Implement actual ElevenLabs knowledge base search
            # This would typically involve calling their conversational AI API
            # with the knowledge base context enabled
            
            end_time = datetime.utcnow()
            search_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return RAGSearchResponse(
                query=query,
                results=search_results,
                total_results=len(search_results),
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            raise e
    
    async def get_documents(
        self, user_id: str, collection_id: Optional[str] = None,
        status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[KnowledgeDocumentResponse]:
        try:
            docs = await self.db_service.get_knowledge_documents(
                user_id=user_id, collection_id=collection_id, status=status, limit=limit, offset=offset
            )
            return docs
        except Exception as e:
            print(f"Error getting documents: {e}")
            raise e
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[KnowledgeDocumentResponse]:
        try:
            doc = await self.db_service.get_knowledge_document(document_id, user_id)
            return doc
        except Exception as e:
            print(f"Error getting document: {e}")
            raise e
    
    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document from both ElevenLabs and our database"""
        try:
            # Get document to find ElevenLabs file ID
            doc = await self.db_service.get_knowledge_document(document_id, user_id)
            if not doc:
                print(f"Document {document_id} not found for user {user_id}")
                return False
            
            elevenlabs_file_id = doc.get("elevenlabs_file_id")
            if elevenlabs_file_id:
                try:
                    # Delete from ElevenLabs
                    print(f"Deleting document {elevenlabs_file_id} from ElevenLabs...")
                    await self._make_elevenlabs_request("DELETE", f"/convai/knowledge-base/{elevenlabs_file_id}")
                    print(f"Successfully deleted document {elevenlabs_file_id} from ElevenLabs")
                except Exception as e:
                    print(f"Warning: Failed to delete from ElevenLabs: {e}")
                    # Continue with database deletion even if ElevenLabs deletion fails
            else:
                print(f"No ElevenLabs file ID found for document {document_id}")
            
            # Delete from our database
            print(f"Deleting document {document_id} from database...")
            db_result = await self.db_service.delete_knowledge_document(document_id, user_id)
            if db_result:
                print(f"Successfully deleted document {document_id} from database")
            else:
                print(f"Failed to delete document {document_id} from database")
            
            return db_result
        except Exception as e:
            print(f"Error deleting document: {e}")
            raise e
    
    async def create_collection(
        self, 
        user_id: str, 
        name: str, 
        description: Optional[str] = None,
        is_public: bool = False
    ) -> KnowledgeCollectionResponse:
        """Create a knowledge collection"""
        try:
            return await self.db_service.create_knowledge_collection(
                user_id=user_id,
                name=name,
                description=description,
                is_public=is_public
            )
        except Exception as e:
            print(f"Error creating collection: {e}")
            raise e
    
    async def get_collections(
        self, 
        user_id: str, 
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeCollectionResponse]:
        """Get user's collections"""
        try:
            return await self.db_service.get_knowledge_collections(
                user_id=user_id,
                include_public=include_public,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            print(f"Error getting collections: {e}")
            raise e
    
    async def delete_collection(self, collection_id: str, user_id: str) -> bool:
        """Delete a collection"""
        try:
            return await self.db_service.delete_knowledge_collection(collection_id, user_id)
        except Exception as e:
            print(f"Error deleting collection: {e}")
            raise e
    
    async def _create_or_update_agent_for_user(self, user_id: str, new_file_id: str):
        """Create or update agent for user with their knowledge base documents"""
        try:
            # Get all processed documents for this user
            documents = await self.db_service.get_knowledge_documents(
                user_id=user_id,
                status="processed",
                limit=100  # Get all processed documents
            )
            
            # Extract ElevenLabs file IDs
            file_ids = []
            for doc in documents:
                if doc.get("elevenlabs_file_id"):
                    file_ids.append(doc["elevenlabs_file_id"])
            
            if not file_ids:
                print(f"No processed documents found for user {user_id}")
                return
            
            # Check if user already has an agent
            existing_agent = await self.agent_service.get_agent_for_user(user_id)
            
            if existing_agent:
                # Update existing agent with new knowledge base
                print(f"Updating existing agent for user {user_id} with {len(file_ids)} documents")
                await self.agent_service.update_agent_knowledge_base(user_id, file_ids)
            else:
                # Create new agent
                agent_name = f"Knowledge Base Agent for User {user_id[:8]}"
                print(f"Creating new agent for user {user_id} with {len(file_ids)} documents")
                await self.agent_service.create_agent_for_user(
                    user_id=user_id,
                    agent_name=agent_name,
                    knowledge_base_file_ids=file_ids
                )
                
        except Exception as e:
            print(f"Error creating/updating agent for user {user_id}: {e}")
            # Don't raise the exception as document upload should still succeed
            # even if agent creation fails

    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        ext = filename.lower().split('.')[-1]
        if ext in ['pdf']:
            return 'pdf'
        elif ext in ['docx', 'doc']:
            return 'docx'
        elif ext in ['txt']:
            return 'txt'
        elif ext in ['md', 'markdown']:
            return 'md'
        else:
            raise ValueError(f"Unsupported file type: {ext}")