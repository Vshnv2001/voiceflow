"""
Knowledge Base Service for document upload, processing, and RAG functionality
"""

import asyncio
import os
import uuid
import traceback
import hashlib
import mimetypes
import logging
from typing import List, Dict, Any, Optional, Tuple
import aiohttp
import json
import ssl
import certifi
from supabase import create_client, Client
from datetime import datetime, timezone
import aiofiles
import aiohttp
from openai import AsyncOpenAI
from elevenlabs import ElevenLabs
import PyPDF2
import docx
import markdown
from io import BytesIO
import json
import re

from services.database_service import DatabaseService
from models.schemas import (
    KnowledgeDocumentResponse, KnowledgeChunkResponse, 
    KnowledgeCollectionResponse, RAGSearchResult, RAGSearchResponse
)

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.db_service = DatabaseService()
        self.sb_url = os.getenv("SUPABASE_URL")
        self.sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # server only
        if not self.sb_url or not self.sb_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        self.sb: Client = create_client(self.sb_url, self.sb_key)

        # Initialize ElevenLabs client
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.elevenlabs_api_key:
            raise RuntimeError("Missing ELEVENLABS_API_KEY")
        self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)

        self.bucket = os.getenv("SUPABASE_KB_BUCKET", "knowledge-base")
        # Optional: ensure the bucket exists (once)
        try:
            # supabase-py is sync; call in a thread to keep async flow clean
            asyncio.get_event_loop().run_until_complete(self._ensure_bucket_exists())
        except RuntimeError:
            # If already in an event loop, just schedule it (or ignore if you create bucket out-of-band)
            asyncio.create_task(self._ensure_bucket_exists())

        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        
    async def _ensure_bucket_exists(self):
        """
        One-time creation; safe to call multiple times.
        If you create the bucket via dashboard/CLI, you can skip this.
        """
        def _create_if_missing():
            existing = self.sb.storage.list_buckets()
            if not any(b.name == self.bucket for b in existing):
                # private bucket (recommended)
                self.sb.storage.create_bucket(self.bucket)
        await asyncio.to_thread(_create_if_missing)

    def _make_storage_path(self, user_id: str, filename: str) -> str:
        # path inside the bucket
        return f"{user_id}/{filename}"

    async def _upload_to_storage(self, file_content: bytes, filename: str, user_id: str) -> str:
        """
        Uploads to a private bucket and returns a canonical storage path.
        We *don’t* return a public URL; we’ll sign on read.
        """
        path_in_bucket = self._make_storage_path(user_id, filename)
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        def _upload():
            # supabase-py requires bytes/IO; also supports `upsert`
            self.sb.storage.from_(self.bucket).upload(
                path=path_in_bucket,
                file=file_content,                 # raw bytes OK
                file_options={"contentType": content_type, "upsert": False}
            )
        await asyncio.to_thread(_upload)

        # Store as "bucket/path" in DB (easy to parse later)
        return f"{self.bucket}/{path_in_bucket}"

    async def _maybe_sign_storage_url(self, stored: Optional[str], expires_in: int = 3600) -> Optional[str]:
        """
        Turn a stored "bucket/path" into a signed URL. If the bucket is public you
        could instead return get_public_url, but private+signed is safer.
        """
        if not stored:
            return None
        if "://" in stored:
            # already a URL (legacy), return as is
            return stored

        try:
            bucket, *rest = stored.split("/", 1)
            if not rest:
                return None
            path_in_bucket = rest[0]

            def _sign():
                return self.sb.storage.from_(bucket).create_signed_url(path_in_bucket, expires_in)

            signed = await asyncio.to_thread(_sign)
            # supabase-py returns {"signedURL": "...", "path": "..."} in v2
            return signed.get("signedURL") or signed.get("signed_url") or signed  # handle different client shapes
        except Exception as e:
            print(f"Failed to sign storage URL for {stored}: {e}")
            print(traceback.format_exc())
            return None

    async def _upload_to_elevenlabs(
        self, 
        file_content: bytes, 
        file_name: str, 
        title: str
    ) -> Dict[str, Any]:
        """Upload file to ElevenLabs Knowledge Base API"""
        try:
            # Create a file-like object from bytes
            file_obj = BytesIO(file_content)
            file_obj.name = file_name
            
            # Upload to ElevenLabs Knowledge Base
            response = self.elevenlabs_client.conversational_ai.knowledge_base.documents.create_from_file(
                file=file_obj,
                name=title
            )
            
            return {
                "id": response.id,
                "name": response.name
            }
            
        except Exception as e:
            print(f"Error uploading to ElevenLabs: {e}")
            raise e

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

            # Upload to ElevenLabs Knowledge Base API
            elevenlabs_response = await self._upload_to_elevenlabs(
                file_content=file_content,
                file_name=file_name,
                title=title
            )

            # Create document record in our database with ElevenLabs file ID
            document = await self.db_service.create_knowledge_document(
                user_id=user_id,
                title=title,
                description=description,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                file_url=elevenlabs_response["id"],  # Store ElevenLabs file ID as file_url
                elevenlabs_file_id=elevenlabs_response["id"],
                status="processed"  # ElevenLabs handles processing
            )

            if collection_ids:
                for collection_id in collection_ids:
                    await self.db_service.add_document_to_collection(
                        document_id=document["id"],
                        collection_id=collection_id
                    )

            return document

        except Exception as e:
            print(f"Error uploading document: {e}")
            print(traceback.format_exc())
            raise e
    
    
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
    
    async def search_knowledge_base(
        self, 
        query: str, 
        user_id: str,
        collection_ids: Optional[List[str]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> RAGSearchResponse:
        """Search knowledge base using ElevenLabs API"""
        try:
            start_time = datetime.utcnow()
            
            # Get user's documents with ElevenLabs file IDs
            documents = await self.db_service.get_knowledge_documents(
                user_id=user_id,
                collection_id=collection_ids[0] if collection_ids else None,
                status="processed",
                limit=100  # Get all processed documents
            )
            
            # For now, return a simple response indicating ElevenLabs integration
            # In a full implementation, you would use ElevenLabs search API
            search_results = []
            for doc in documents[:limit]:
                if doc.get('elevenlabs_file_id'):
                    search_results.append(RAGSearchResult(
                        chunk_id=doc['id'],
                        document_id=doc['id'],
                        document_title=doc['title'],
                        content=f"Document: {doc['title']} (Processed by ElevenLabs)",
                        similarity_score=0.8,  # Placeholder score
                        metadata={"elevenlabs_file_id": doc['elevenlabs_file_id']}
                    ))
            
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
            # Sign each one (do in parallel)
            async def sign_one(d):
                d["signed_file_url"] = await self._maybe_sign_storage_url(d.get("file_url"))
                return d
            return await asyncio.gather(*(sign_one(d) for d in docs))
        except Exception as e:
            print(f"Error getting documents: {e}")
            raise e
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[KnowledgeDocumentResponse]:
        try:
            doc = await self.db_service.get_knowledge_document(document_id, user_id)
            if not doc:
                return None
            signed = await self._maybe_sign_storage_url(doc.get("file_url"))
            # Option A: augment response
            doc["signed_file_url"] = signed
            # Option B: overwrite file_url with signed (if your UI expects file_url to be clickable)
            # doc["file_url"] = signed
            return doc
        except Exception as e:
            print(f"Error getting document: {e}")
            raise e
    
    async def _delete_from_elevenlabs(self, elevenlabs_file_id: str) -> bool:
        """Delete document from ElevenLabs Knowledge Base"""
        try:
            if not elevenlabs_file_id:
                return True  # Nothing to delete
                
            if not self.elevenlabs_client:
                print("ElevenLabs client not available, skipping ElevenLabs deletion")
                return True
                
            # Delete from ElevenLabs Knowledge Base
            self.elevenlabs_client.conversational_ai.knowledge_base.documents.delete(
                documentation_id=elevenlabs_file_id
            )
            print(f"Successfully deleted document {elevenlabs_file_id} from ElevenLabs")
            return True
            
        except Exception as e:
            # Check if it's a 404 error (document not found) - this is acceptable
            if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 404:
                print(f"Document {elevenlabs_file_id} not found in ElevenLabs (already deleted or never existed)")
                return True  # Consider this a success since the end result is the same
            else:
                print(f"Error deleting from ElevenLabs: {e}")
                # Don't raise - we still want to delete from our DB even if ElevenLabs fails
                return False

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document from both ElevenLabs and our database"""
        try:
            # First, get the document to retrieve the ElevenLabs file ID
            doc = await self.db_service.get_knowledge_document(document_id, user_id)
            if not doc:
                return False
                
            elevenlabs_file_id = doc.get("elevenlabs_file_id")
            
            # Delete from ElevenLabs first (best effort)
            if elevenlabs_file_id:
                await self._delete_from_elevenlabs(elevenlabs_file_id)
            
            # Then delete from our database
            return await self.db_service.delete_knowledge_document(document_id, user_id)
            
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
    
    async def get_user_elevenlabs_file_ids(self, user_id: str) -> List[str]:
        """Get all elevenlabs_file_id values for a user's processed documents"""
        try:
            # Get all processed documents for the user
            documents = await self.db_service.get_knowledge_documents(
                user_id=user_id,
                status="processed",
                limit=1000  # Get all processed documents
            )
            
            # Extract elevenlabs_file_id values, filtering out None/empty values
            file_ids = [
                doc["elevenlabs_file_id"] 
                for doc in documents 
                if doc.get("elevenlabs_file_id")
            ]
            
            print(f"Found {len(file_ids)} ElevenLabs file IDs for user {user_id}")
            return file_ids
            
        except Exception as e:
            print(f"Error getting ElevenLabs file IDs for user {user_id}: {e}")
            return []
    
    async def update_agent_with_knowledge_base(self, agent_id: str, user_id: str) -> bool:
        """Update an agent to use the user's knowledge base documents"""
        try:
            # Get all processed file IDs for the user
            file_ids = await self.get_user_elevenlabs_file_ids(user_id)
            
            if not file_ids:
                print(f"No knowledge base documents found for user {user_id}")
                return True  # Not an error, just no documents to add
            
            # Create knowledge base locators for the agent update
            knowledge_base = [
                {
                    "type": "file",
                    "name": f"Document.txt",
                    "id": file_id,
                    "usage_mode": "auto"
                }
                for i, file_id in enumerate(file_ids)
            ]
            
            # Prepare the agent update payload
            update_payload = {
                "conversation_config": {
                    "agent": {
                        "prompt": {
                            "knowledge_base": knowledge_base
                        },
                    }
                }
            }
            
            # Update the agent using ElevenLabs API with SSL context handling
            
            url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json"
            }
            
            # Create SSL context with proper certificate handling
            ssl_context = ssl.create_default_context()
            try:
                # Try with certifi certificates first
                ssl_context.load_verify_locations(certifi.where())
                print("Using certifi certificates for SSL verification")
            except Exception as cert_error:
                print(f"Failed to load certifi certificates: {cert_error}")
                # Fallback to system certificates
                ssl_context = ssl.create_default_context()
                print("Using system certificates for SSL verification")
            
            # Create connector with SSL context
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            try:
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.patch(url, headers=headers, json=update_payload) as response:
                        if response.status == 200:
                            print(f"Successfully updated agent {agent_id} with {len(file_ids)} knowledge base documents")
                            return True
                        else:
                            error_text = await response.text()
                            print(f"Failed to update agent {agent_id}: {response.status} - {error_text}")
                            return False
                            
            except ssl.SSLError as ssl_error:
                print(f"SSL verification failed, retrying without verification: {ssl_error}")
                # Fallback: disable SSL verification (less secure but works)
                ssl_context_insecure = ssl.create_default_context()
                ssl_context_insecure.check_hostname = False
                ssl_context_insecure.verify_mode = ssl.CERT_NONE
                
                connector_insecure = aiohttp.TCPConnector(ssl=ssl_context_insecure)
                
                async with aiohttp.ClientSession(connector=connector_insecure) as session:
                    async with session.patch(url, headers=headers, json=update_payload) as response:
                        if response.status == 200:
                            print(f"Successfully updated agent {agent_id} with {len(file_ids)} knowledge base documents (insecure SSL)")
                            return True
                        else:
                            error_text = await response.text()
                            print(f"Failed to update agent {agent_id}: {response.status} - {error_text}")
                            return False
                        
        except Exception as e:
            print(f"Error updating agent {agent_id} with knowledge base: {e}")
            return False
    
    async def refresh_agent_knowledge_base(self, agent_id: str, user_id: str) -> bool:
        """Refresh the agent's knowledge base with the latest documents"""
        try:
            logger.info(f"Refreshing knowledge base for agent {agent_id} with user {user_id}'s documents")
            return await self.update_agent_with_knowledge_base(agent_id, user_id)
        except Exception as e:
            logger.error(f"Error refreshing agent knowledge base: {e}")
            return False