"""
Knowledge Base Service for document upload, processing, and RAG functionality
"""

import asyncio
import os
import uuid
import traceback
import hashlib
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from supabase import create_client, Client
from datetime import datetime, timezone
import aiofiles
import aiohttp
from openai import AsyncOpenAI
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
            return None

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

            # Stable unique name (you already have this)
            file_hash = hashlib.md5(file_content).hexdigest()
            unique_filename = f"{file_hash}_{file_name}"

            # --- CHANGED: upload to storage & get canonical storage path ---
            storage_path = await self._upload_to_storage(
                file_content=file_content,
                filename=unique_filename,
                user_id=user_id
            )
            # Note: we store the storage *path* in file_url (not a signed URL)
            # e.g., "knowledge-base/<user_id>/2025/10/18/<hash>_file.pdf"

            document = await self.db_service.create_knowledge_document(
                user_id=user_id,
                title=title,
                description=description,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                file_url=storage_path  # <-- store path, not public URL
            )

            if collection_ids:
                for collection_id in collection_ids:
                    await self.db_service.add_document_to_collection(
                        document_id=document["id"],
                        collection_id=collection_id
                    )

            asyncio.create_task(self._process_document(document["id"], file_content, file_type))
            return document

        except Exception as e:
            print(f"Error uploading document: {e}")
            print(traceback.format_exc())
            raise e
    
    async def _process_document(self, document_id: str, file_content: bytes, file_type: str):
        """Background task to process document and create embeddings"""
        try:
            # Extract text content
            content_text = await self._extract_text(file_content, file_type)
            
            # Update document with extracted text
            await self.db_service.update_knowledge_document(
                document_id=document_id,
                content_text=content_text,
                status="processed"
            )
            
            # Split into chunks
            chunks = self._split_into_chunks(content_text)
            
            # Create chunks with embeddings
            for i, chunk_content in enumerate(chunks):
                # Generate embedding
                embedding = await self._generate_embedding(chunk_content)
                
                # Create chunk record
                await self.db_service.create_knowledge_chunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk_content,
                    content_length=len(chunk_content),
                    embedding=embedding,
                    metadata={"chunk_size": len(chunk_content)}
                )
            
        except Exception as e:
            print(f"Error processing document {document_id}: {e}")
            # Update document status to failed
            await self.db_service.update_knowledge_document(
                document_id=document_id,
                status="failed",
                processing_error=str(e)
            )
    
    async def _extract_text(self, file_content: bytes, file_type: str) -> str:
        """Extract text content from various file types"""
        try:
            if file_type == "pdf":
                return self._extract_pdf_text(file_content)
            elif file_type == "docx":
                return self._extract_docx_text(file_content)
            elif file_type == "txt":
                return file_content.decode('utf-8')
            elif file_type == "md":
                return self._extract_markdown_text(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            print(f"Error extracting text from {file_type}: {e}")
            raise e
    
    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            raise e
    
    def _extract_docx_text(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            raise e
    
    def _extract_markdown_text(self, file_content: bytes) -> str:
        """Extract text from Markdown file"""
        try:
            content = file_content.decode('utf-8')
            # Convert markdown to HTML then extract text
            html = markdown.markdown(content)
            # Simple HTML tag removal
            text = re.sub(r'<[^>]+>', '', html)
            return text.strip()
        except Exception as e:
            print(f"Error extracting Markdown text: {e}")
            raise e
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(start + self.chunk_size - 100, start)
                sentence_end = text.rfind('.', search_start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', search_start, end)
                    if word_end > start:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            print("Trying to generate embeddings")
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            print("Embeddings generated successfully")
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
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
        """Search knowledge base using RAG"""
        try:
            start_time = datetime.utcnow()
            
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Search for similar chunks
            results = await self.db_service.search_knowledge_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                collection_ids=collection_ids,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            # Convert to response format
            search_results = []
            for result in results:
                search_results.append(RAGSearchResult(
                    chunk_id=result['chunk_id'],
                    document_id=result['document_id'],
                    document_title=result['document_title'],
                    content=result['content'],
                    similarity_score=result['similarity_score'],
                    metadata=result['metadata']
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
    
    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document and its chunks"""
        try:
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
