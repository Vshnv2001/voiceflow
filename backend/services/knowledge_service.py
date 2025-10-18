"""
Knowledge Base Service for document upload, processing, and RAG functionality
"""

import asyncio
import os
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
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
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        
    async def upload_document(
        self, 
        file_content: bytes, 
        file_name: str, 
        user_id: str,
        title: str,
        description: Optional[str] = None,
        collection_ids: Optional[List[str]] = None
    ) -> KnowledgeDocumentResponse:
        """Upload and process a document for the knowledge base"""
        try:
            # Determine file type
            file_type = self._get_file_type(file_name)
            file_size = len(file_content)
            
            # Generate unique file name
            file_hash = hashlib.md5(file_content).hexdigest()
            unique_filename = f"{file_hash}_{file_name}"
            
            # Upload file to storage (using Supabase storage)
            file_url = await self._upload_to_storage(file_content, unique_filename)
            
            # Create document record
            document = await self.db_service.create_knowledge_document(
                user_id=user_id,
                title=title,
                description=description,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                file_url=file_url
            )
            
            # Add to collections if specified
            if collection_ids:
                for collection_id in collection_ids:
                    await self.db_service.add_document_to_collection(
                        document_id=document.id,
                        collection_id=collection_id
                    )
            
            # Start background processing
            asyncio.create_task(self._process_document(document.id, file_content, file_type))
            
            return document
            
        except Exception as e:
            print(f"Error uploading document: {e}")
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
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise e
    
    async def _upload_to_storage(self, file_content: bytes, filename: str) -> str:
        """Upload file to Supabase storage"""
        try:
            # This would integrate with your Supabase storage
            # For now, return a placeholder URL
            return f"https://your-storage-bucket.supabase.co/storage/v1/object/public/knowledge-base/{filename}"
        except Exception as e:
            print(f"Error uploading to storage: {e}")
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
        self, 
        user_id: str, 
        collection_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeDocumentResponse]:
        """Get user's knowledge documents"""
        try:
            return await self.db_service.get_knowledge_documents(
                user_id=user_id,
                collection_id=collection_id,
                status=status,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            print(f"Error getting documents: {e}")
            raise e
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[KnowledgeDocumentResponse]:
        """Get a specific document"""
        try:
            return await self.db_service.get_knowledge_document(document_id, user_id)
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
