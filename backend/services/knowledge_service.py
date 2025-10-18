"""
Knowledge Base Service for document upload, processing, and RAG functionality
"""

import asyncio
import os
import traceback
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from openai import AsyncOpenAI
import PyPDF2
import docx
import markdown
from io import BytesIO
import json
import re
from elevenlabs import ElevenLabs

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

        # Initialize ElevenLabs client
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.elevenlabs_api_key:
            raise RuntimeError("Missing ELEVENLABS_API_KEY")
        self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)

        # ElevenLabs is now the primary storage method

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
        try:
            file_type = self._get_file_type(file_name)
            file_size = len(file_content)

            # Upload to ElevenLabs knowledge base
            elevenlabs_file_id = await self._upload_to_elevenlabs_knowledge_base(
                file_content=file_content,
                file_name=file_name,
                user_id=user_id,
                title=title
            )

            # Create document record with ElevenLabs file reference
            # Use ElevenLabs file ID as the primary reference
            document = await self.db_service.create_knowledge_document(
                user_id=user_id,
                title=title,
                description=description,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                file_url=f"elevenlabs://{elevenlabs_file_id}",  # Use ElevenLabs reference
                elevenlabs_file_id=elevenlabs_file_id
            )

            if collection_ids:
                for collection_id in collection_ids:
                    await self.db_service.add_document_to_collection(
                        document_id=document["id"],
                        collection_id=collection_id
                    )

            # ElevenLabs handles document processing, no need for local embedding generation
            return document

        except Exception as e:
            print(f"Error uploading document: {e}")
            print(traceback.format_exc())
            raise e
    
    async def _upload_to_elevenlabs_knowledge_base(
        self, 
        file_content: bytes, 
        file_name: str, 
        user_id: str,
        title: str
    ) -> str:
        """Upload file to ElevenLabs knowledge base and return file ID"""
        try:
            # Create a file-like object from bytes
            file_obj = BytesIO(file_content)
            file_obj.name = file_name
            
            # Upload to ElevenLabs knowledge base
            response = await asyncio.to_thread(
                self.elevenlabs_client.conversational_ai.knowledge_base.documents.create_from_file,
                file=file_obj,
                name=title
            )
            
            # Store the ElevenLabs file record in our database
            elevenlabs_file_record = await self.db_service.create_elevenlabs_knowledge_file(
                user_id=user_id,
                elevenlabs_file_id=response.id,
                elevenlabs_name=response.name,
                original_filename=file_name,
                file_type=self._get_file_type(file_name),
                file_size=len(file_content),
                upload_status="completed"
            )
            
            return response.id  # Return the actual ElevenLabs document ID, not the Supabase record ID
            
        except Exception as e:
            print(f"Error uploading to ElevenLabs knowledge base: {e}")
            # Create a failed record in our database
            try:
                failed_record = await self.db_service.create_elevenlabs_knowledge_file(
                    user_id=user_id,
                    elevenlabs_file_id="",  # Empty since upload failed
                    elevenlabs_name="",
                    original_filename=file_name,
                    file_type=self._get_file_type(file_name),
                    file_size=len(file_content),
                    upload_status="failed",
                    error_message=str(e)
                )
                return failed_record["id"]
            except Exception as db_error:
                print(f"Error creating failed ElevenLabs record: {db_error}")
                raise e
    
    async def _delete_from_elevenlabs_knowledge_base(
        self, 
        elevenlabs_file_id: str,
        force: bool = False
    ) -> bool:
        """Delete file from ElevenLabs knowledge base"""
        try:
            # Delete from ElevenLabs knowledge base
            await asyncio.to_thread(
                self.elevenlabs_client.conversational_ai.knowledge_base.documents.delete,
                documentation_id=elevenlabs_file_id,
                force=force
            )
            return True
            
        except Exception as e:
            print(f"Error deleting from ElevenLabs knowledge base: {e}")
            return False
    
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
            # ElevenLabs files don't need URL signing
            return docs
        except Exception as e:
            print(f"Error getting documents: {e}")
            raise e
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[KnowledgeDocumentResponse]:
        try:
            doc = await self.db_service.get_knowledge_document(document_id, user_id)
            if not doc:
                return None
            # ElevenLabs files don't need URL signing
            return doc
        except Exception as e:
            print(f"Error getting document: {e}")
            raise e
    
    async def delete_document(self, document_id: str, user_id: str, force: bool = False) -> bool:
        """Delete a document from both ElevenLabs and local database"""
        try:
            # First, get the document to retrieve the ElevenLabs file ID
            document = await self.db_service.get_knowledge_document(document_id, user_id)
            if not document:
                return False
            
            # Delete from ElevenLabs if we have an ElevenLabs file ID
            elevenlabs_file_id = document.get('elevenlabs_file_id')
            if elevenlabs_file_id:
                elevenlabs_deleted = await self._delete_from_elevenlabs_knowledge_base(
                    elevenlabs_file_id=elevenlabs_file_id,  # Use the actual ElevenLabs file ID, not the Supabase document ID
                    force=force
                )
                if not elevenlabs_deleted:
                    print(f"Warning: Failed to delete from ElevenLabs knowledge base for document {document_id}")
                    print(traceback.format_exc())
                    # Continue with local deletion even if ElevenLabs deletion fails
            
            # Delete from local database (this will also delete chunks due to CASCADE)
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
