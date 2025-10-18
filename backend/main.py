"""
VoiceFlow AI - Voice-based Customer Service Backend
FastAPI application for handling voice messages, AI responses, and agent approvals
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
from datetime import datetime
import uuid

from services.voice_service import VoiceService
from services.ai_service import AIService
from services.database_service import DatabaseService
from services.auth_service import AuthService
from services.knowledge_service import KnowledgeService
from models.schemas import (
    SessionCreate, SessionResponse, MessageCreate, MessageResponse,
    VoiceProcessingJobResponse, AgentApprovalRequest, SystemConfigUpdate,
    VoiceResponse, VoiceSynthesisRequest, VoiceSynthesisResponse,
    KnowledgeDocumentCreate, KnowledgeDocumentResponse, KnowledgeCollectionCreate,
    KnowledgeCollectionResponse, DocumentUploadResponse, RAGSearchRequest, RAGSearchResponse
)

# Initialize FastAPI app
app = FastAPI(
    title="VoiceFlow AI API",
    description="Voice-based Customer Service API with AI responses and agent approval workflow",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
voice_service = VoiceService()
ai_service = AIService()
db_service = DatabaseService()
auth_service = AuthService()
knowledge_service = KnowledgeService()

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate user from JWT token"""
    try:
        user = await auth_service.verify_token(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# ==================== SESSION ENDPOINTS ====================

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new customer service session"""
    try:
        session = await db_service.create_session(
            user_id=current_user["id"],
            customer_id=session_data.customer_id,
            metadata=session_data.metadata
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/sessions/{session_id}/close", response_model=SessionResponse)
async def close_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Close a session"""
    try:
        await db_service.close_session(session_id, current_user["id"])
        return {"message": "Session closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions", response_model=List[SessionResponse])
async def get_sessions(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's sessions with optional filtering"""
    try:
        sessions = await db_service.get_sessions(
            user_id=current_user["id"],
            status=status,
            limit=limit,
            offset=offset
        )
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific session by ID"""
    try:
        session = await db_service.get_session(session_id, current_user["id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/sessions/{session_id}")
async def update_session(
    session_id: str,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update session status"""
    try:
        await db_service.update_session(session_id, current_user["id"], status=status)
        return {"message": "Session updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MESSAGE ENDPOINTS ====================

@app.post("/api/sessions/{session_id}/messages/voice", response_model=MessageResponse)
async def upload_voice_message(
    session_id: str,
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a voice message and start transcription process"""
    try:
        # Validate session belongs to user
        session = await db_service.get_session(session_id, current_user["id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Upload audio file to storage
        audio_url = await voice_service.upload_audio(audio_file)
        
        # Create message record
        message = await db_service.create_message(
            session_id=session_id,
            sender_type="customer",
            message_type="voice",
            voice_audio_url=audio_url,
            voice_duration_seconds=None  # Will be updated after processing
        )
        
        # Start transcription in background
        background_tasks.add_task(
            process_voice_transcription,
            message.id,
            audio_url
        )
        
        return message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a session"""
    try:
        # Validate session belongs to user
        session = await db_service.get_session(session_id, current_user["id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = await db_service.get_messages(session_id, limit, offset)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/{message_id}/generate-ai-response", response_model=MessageResponse)
async def generate_ai_response(
    message_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI response for a transcribed message"""
    try:
        # Get the message
        message = await db_service.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Validate session belongs to user
        session = await db_service.get_session(message.session_id, current_user["id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate AI response in background
        background_tasks.add_task(
            process_ai_response_generation,
            message_id
        )
        
        return {"message": "AI response generation started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AGENT APPROVAL ENDPOINTS ====================

@app.get("/api/agent/pending-messages", response_model=List[MessageResponse])
async def get_pending_messages(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get messages pending agent approval"""
    try:
        # Check if user is an agent
        if not await auth_service.is_agent(current_user["id"]):
            raise HTTPException(status_code=403, detail="Access denied. Agent role required.")
        
        messages = await db_service.get_pending_messages(limit, offset)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/{message_id}/approve")
async def approve_message(
    message_id: str,
    approval_data: AgentApprovalRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Approve or edit an AI-generated message"""
    try:
        # Check if user is an agent
        if not await auth_service.is_agent(current_user["id"]):
            raise HTTPException(status_code=403, detail="Access denied. Agent role required.")
        
        # Update message with approval
        await db_service.approve_message(
            message_id=message_id,
            agent_id=current_user["id"],
            approved=approval_data.approved,
            edited_content=approval_data.edited_content,
            edit_reason=approval_data.edit_reason
        )
        
        # If approved, start voice synthesis
        if approval_data.approved:
            # Get the message to get voice_id and text content
            message = await db_service.get_message(message_id)
            if message:
                text_to_synthesize = approval_data.edited_content or message.text_content
                voice_id = message.voice_id or voice_service.default_voice_id
                
                # Start voice synthesis in background
                background_tasks.add_task(
                    process_voice_synthesis,
                    message_id,
                    text_to_synthesize,
                    voice_id
                )
            
        return {"message": "Message processed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== VOICE PROCESSING ENDPOINTS ====================

@app.get("/api/voice-jobs/{job_id}", response_model=VoiceProcessingJobResponse)
async def get_voice_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get status of a voice processing job"""
    try:
        job = await db_service.get_voice_job(job_id, current_user["id"])
        if not job:
            raise HTTPException(status_code=404, detail="Voice job not found")
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== VOICE MANAGEMENT ENDPOINTS ====================

@app.get("/api/voices", response_model=List[VoiceResponse])
async def get_available_voices(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get available voices"""
    try:
        if category:
            voices = await voice_service.get_voices_by_category(category)
        else:
            voices = await voice_service.get_available_voices()
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voices/{voice_id}", response_model=VoiceResponse)
async def get_voice(
    voice_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific voice by ID"""
    try:
        voice = await voice_service.get_voice_by_id(voice_id)
        if not voice:
            raise HTTPException(status_code=404, detail="Voice not found")
        return voice
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voices/default", response_model=VoiceResponse)
async def get_default_voice(
    current_user: dict = Depends(get_current_user)
):
    """Get the default voice"""
    try:
        voice = await voice_service.get_default_voice()
        if not voice:
            raise HTTPException(status_code=404, detail="Default voice not found")
        return voice
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/synthesize", response_model=VoiceSynthesisResponse)
async def synthesize_voice(
    request: VoiceSynthesisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Synthesize text to speech"""
    try:
        # Use provided voice_id or default
        voice_id = request.voice_id
        if not voice_id:
            default_voice = await voice_service.get_default_voice()
            voice_id = default_voice['voice_id'] if default_voice else voice_service.default_voice_id
        
        # Synthesize audio
        audio_url = await voice_service.synthesize_audio(request.text, voice_id)
        
        return VoiceSynthesisResponse(
            audio_url=audio_url,
            voice_id=voice_id,
            text=request.text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SYSTEM CONFIGURATION ENDPOINTS ====================

@app.get("/api/admin/config")
async def get_system_config(
    current_user: dict = Depends(get_current_user)
):
    """Get system configuration (admin only)"""
    try:
        if not await auth_service.is_admin(current_user["id"]):
            raise HTTPException(status_code=403, detail="Access denied. Admin role required.")
        
        config = await db_service.get_system_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/admin/config")
async def update_system_config(
    config_updates: List[SystemConfigUpdate],
    current_user: dict = Depends(get_current_user)
):
    """Update system configuration (admin only)"""
    try:
        if not await auth_service.is_admin(current_user["id"]):
            raise HTTPException(status_code=403, detail="Access denied. Admin role required.")
        
        await db_service.update_system_config(config_updates)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== KNOWLEDGE BASE ENDPOINTS ====================

@app.post("/api/knowledge/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    collection_ids: Optional[str] = Form(None),  # JSON string of collection IDs
    current_user: dict = Depends(get_current_user)
):
    """Upload a document to the knowledge base"""
    try:
        # Validate file type
        allowed_types = ['pdf', 'txt', 'docx', 'md']
        file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}")
        
        # Read file content
        file_content = await file.read()
        
        # Parse collection IDs if provided
        collection_id_list = None
        if collection_ids:
            try:
                import json
                collection_id_list = json.loads(collection_ids)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid collection_ids format. Expected JSON array.")
        
        # Upload document
        document = await knowledge_service.upload_document(
            file_content=file_content,
            file_name=file.filename,
            user_id=current_user["id"],
            title=title,
            description=description,
            collection_ids=collection_id_list
        )
        
        return DocumentUploadResponse(
            document_id=document.id,
            file_url=document.file_url,
            status="processing",
            message="Document uploaded successfully and is being processed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/documents", response_model=List[KnowledgeDocumentResponse])
async def get_documents(
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's knowledge documents"""
    try:
        documents = await knowledge_service.get_documents(
            user_id=current_user["id"],
            collection_id=collection_id,
            status=status,
            limit=limit,
            offset=offset
        )
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific document"""
    try:
        document = await knowledge_service.get_document(document_id, current_user["id"])
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/knowledge/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document"""
    try:
        success = await knowledge_service.delete_document(document_id, current_user["id"])
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/collections", response_model=KnowledgeCollectionResponse)
async def create_collection(
    collection_data: KnowledgeCollectionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a knowledge collection"""
    try:
        collection = await knowledge_service.create_collection(
            user_id=current_user["id"],
            name=collection_data.name,
            description=collection_data.description,
            is_public=collection_data.is_public
        )
        return collection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/collections", response_model=List[KnowledgeCollectionResponse])
async def get_collections(
    include_public: bool = True,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's knowledge collections"""
    try:
        collections = await knowledge_service.get_collections(
            user_id=current_user["id"],
            include_public=include_public,
            limit=limit,
            offset=offset
        )
        return collections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/knowledge/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a collection"""
    try:
        success = await knowledge_service.delete_collection(collection_id, current_user["id"])
        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")
        return {"message": "Collection deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/search", response_model=RAGSearchResponse)
async def search_knowledge_base(
    search_request: RAGSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search the knowledge base using RAG"""
    try:
        results = await knowledge_service.search_knowledge_base(
            query=search_request.query,
            user_id=current_user["id"],
            collection_ids=search_request.collection_ids,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== BACKGROUND TASKS ====================

async def process_voice_transcription(message_id: str, audio_url: str):
    """Background task to transcribe voice message"""
    job_id = None
    try:
        # Create voice processing job
        job_id = await db_service.create_voice_job(
            message_id=message_id,
            job_type="transcription",
            provider="elevenlabs",
            input_url=audio_url
        )
        
        # Transcribe using ElevenLabs
        transcription = await voice_service.transcribe_audio(audio_url, language_code="eng", diarize=True)
        
        # Update message with transcription
        await db_service.update_message(
            message_id=message_id,
            voice_transcription=transcription
        )
        
        # Update job status
        await db_service.update_voice_job(job_id, "completed")
        
    except Exception as e:
        # Update job status to failed
        if job_id:
            await db_service.update_voice_job(job_id, "failed", error_message=str(e))

async def process_ai_response_generation(message_id: str):
    """Background task to generate AI response with RAG"""
    try:
        # Get the message with transcription
        message = await db_service.get_message(message_id)
        if not message or not message.voice_transcription:
            return
        
        # Get the session to get user_id for RAG
        session = await db_service.get_session(message.session_id, None)  # No user_id check for background task
        if not session:
            return
        
        # Generate AI response using OpenAI with RAG
        ai_response = await ai_service.generate_response(
            user_message=message.voice_transcription,
            session_id=message.session_id,
            use_rag=True,
            user_id=session["user_id"]
        )
        
        # Select appropriate voice for the response
        voice_id = await voice_service.select_voice_for_message(message_id)
        
        # Create AI response message
        await db_service.create_message(
            session_id=message.session_id,
            sender_type="system",
            message_type="ai_generated",
            text_content=ai_response,
            voice_id=voice_id,
            ai_model="gpt-4o-mini"
        )
        
    except Exception as e:
        print(f"Error generating AI response: {e}")

async def process_voice_synthesis(message_id: str, text: str, voice_id: str):
    """Background task to synthesize approved message to voice"""
    job_id = None
    try:
        # Create voice processing job
        job_id = await db_service.create_voice_job(
            message_id=message_id,
            job_type="synthesis",
            provider="elevenlabs",
            voice_id=voice_id
        )
        
        # Synthesize using ElevenLabs
        audio_url = await voice_service.synthesize_audio(text, voice_id)
        
        # Update message with audio URL
        await db_service.update_message(
            message_id=message_id,
            voice_audio_url=audio_url
        )
        
        # Update job status
        await db_service.update_voice_job(job_id, "completed", output_url=audio_url)
        
    except Exception as e:
        # Update job status to failed
        if job_id:
            await db_service.update_voice_job(job_id, "failed", error_message=str(e))

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)