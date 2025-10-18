"""
VoiceFlow AI - Voice-based Customer Service Backend
FastAPI application for handling voice messages, AI responses, and agent approvals
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, Form, WebSocket, WebSocketDisconnect, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
from datetime import datetime
import uuid
import json
import logging
import io
import numpy as np
import time

import uvicorn

# Configure logging
logger = logging.getLogger(__name__)

from services.voice_service import VoiceService
from services.ai_service import AIService
from services.database_service import DatabaseService
from services.auth_service import AuthService
from services.knowledge_service import KnowledgeService
from services.elevenlabs_websocket_service import ElevenLabsWebSocketService
from models.schemas import (
    SessionCreate, SessionResponse, MessageCreate, MessageResponse,
    VoiceProcessingJobResponse, AgentApprovalRequest, SystemConfigUpdate,
    VoiceResponse, VoiceSynthesisRequest, VoiceSynthesisResponse,
    KnowledgeDocumentCreate, KnowledgeDocumentResponse, KnowledgeCollectionCreate,
    KnowledgeCollectionResponse, DocumentUploadResponse, RAGSearchRequest, RAGSearchResponse,
    CustomerServiceCallRequest, WebSocketConnectionRequest, WebSocketConnectionResponse
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
    allow_origins=["http://localhost:3000"],
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

# Initialize ElevenLabs WebSocket service
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
if not elevenlabs_api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable is required")
elevenlabs_ws_service = ElevenLabsWebSocketService(elevenlabs_api_key)

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate user from JWT token"""
    try:
        user = await auth_service.verify_token(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# ==================== SESSION ENDPOINTS ====================

@app.post("/api/customer-service/call", response_model=SessionResponse)
async def initiate_customer_service_call(
    call_data: CustomerServiceCallRequest,
):
    """Initiate a customer service call"""
    try:
        print(f"📞 Initiating call - rep_id: {call_data.rep_id}, customer_name: {call_data.customer_name}")
        session = await db_service.create_session(
            customer_rep_id=call_data.rep_id,
            customer_name=call_data.customer_name,
            metadata=call_data.metadata
        )
        print(f"✅ Session created successfully! ID: {session.get('id')}")
        print(f"Session data being returned: {session}")
        return session
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/customer-service/call/accept", response_model=SessionResponse)
async def accept_customer_service_call(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a customer service call"""
    try:
        session = await db_service.accept_session(session_id, current_user["id"])
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
    """Get customer rep's sessions with optional filtering"""
    try:
        sessions = await db_service.get_sessions(
            customer_rep_id=current_user["id"],
            status=status,
            limit=limit,
            offset=offset
        )
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reps/pending-sessions", response_model=List[SessionResponse])
async def get_pending_sessions_for_rep(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get pending call requests for the current customer rep"""
    try:
        # Get pending sessions where customer_rep_id matches current user's id
        sessions = await db_service.get_pending_sessions_for_rep(
            customer_rep_id=current_user["id"],
            limit=limit,
            offset=offset
        )
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reps/active-sessions", response_model=List[SessionResponse])
async def get_active_sessions_for_rep(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get active sessions for the current customer rep"""
    try:
        # Get active sessions where customer_rep_id matches current user's id
        sessions = await db_service.get_active_sessions_for_rep(
            customer_rep_id=current_user["id"],
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
            document_id=document['id'],
            file_url=document['file_url'],
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
        
        # Get the session to get customer_rep_id for RAG
        session = await db_service.get_session(message.session_id, None)  # No customer_rep_id check for background task
        if not session:
            return
        
        # Generate AI response using OpenAI with RAG
        ai_response = await ai_service.generate_response(
            user_message=message.voice_transcription,
            session_id=message.session_id,
            use_rag=True,
            user_id=session["customer_rep_id"]
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

# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws/elevenlabs/{agent_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    agent_id: str
):
    """WebSocket endpoint for ElevenLabs agent conversations with robust persistence"""
    await websocket.accept()
    connection_id = None
    
    try:
        # Get query parameters
        query_params = websocket.query_params
        session_id = query_params.get("session_id")
        user_id = query_params.get("user_id")
        
        # Validate required parameters
        if not session_id or not user_id:
            await websocket.close(code=1008, reason="Missing session_id or user_id")
            return
        
        # Create WebSocket connection
        connection_id = await elevenlabs_ws_service.create_connection(
            websocket=websocket,
            agent_id=agent_id,
            session_id=session_id,
            user_id=user_id
        )
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "user_id": user_id,
            "heartbeat_interval": 30,
            "features": ["reconnection", "heartbeat", "persistence"]
        })
        
        # Keep connection alive and handle client messages
        try:
            while True:
                try:
                    # Wait for messages from client with timeout
                    message = await asyncio.wait_for(
                        websocket.receive_text(), 
                        timeout=60.0  # 1 minute timeout
                    )
                    
                    # Handle ping/pong for connection health
                    try:
                        data = json.loads(message)
                        if data.get("type") == "pong":
                            # Client responded to heartbeat
                            continue
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to client
                    try:
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": time.time()
                        })
                    except Exception:
                        break  # Connection lost
                        
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected for session: {session_id}")
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        # Clean up connection
        if connection_id:
            await elevenlabs_ws_service.close_connection(connection_id)

@app.post("/api/websocket/connect", response_model=WebSocketConnectionResponse)
async def create_websocket_connection(
    request: WebSocketConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a WebSocket connection for ElevenLabs agent"""
    try:
        # Validate session belongs to user
        session = await db_service.get_session(request.session_id, current_user["id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate connection URL
        connection_url = f"/ws/elevenlabs/{request.agent_id}?session_id={request.session_id}&user_id={current_user['id']}"
        
        return WebSocketConnectionResponse(
            connection_id="pending",  # Will be set when WebSocket connects
            status="ready",
            message=f"Connect to WebSocket at: {connection_url}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/websocket/connections")
async def list_websocket_connections(
    current_user: dict = Depends(get_current_user)
):
    """List active WebSocket connections"""
    try:
        connections = elevenlabs_ws_service.list_connections()
        return {"connections": connections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/websocket/connections/{connection_id}")
async def close_websocket_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Close a WebSocket connection"""
    try:
        await elevenlabs_ws_service.close_connection(connection_id)
        return {"message": "Connection closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== WEBSOCKET AUDIO STREAMING ====================

class AudioBuffer:
    """Buffer to accumulate audio chunks and detect silence"""
    def __init__(self, silence_threshold: float = 0.01, silence_duration: float = 2.0, sample_rate: int = 16000):
        self.buffer = []
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.sample_rate = sample_rate
        self.silence_samples = int(silence_duration * sample_rate)
        self.current_silence_count = 0
        
    def add_chunk(self, audio_data: bytes) -> bool:
        """
        Add audio chunk to buffer and check for silence.
        Returns True if silence detected for specified duration.
        """
        self.buffer.append(audio_data)
        
        # Convert bytes to numpy array for amplitude analysis
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            # Normalize to -1.0 to 1.0
            audio_normalized = audio_array.astype(np.float32) / 32768.0
            
            # Calculate RMS (Root Mean Square) for volume level
            rms = np.sqrt(np.mean(audio_normalized ** 2))
            
            # Check if this chunk is silent
            if rms < self.silence_threshold:
                self.current_silence_count += len(audio_array)
            else:
                # Reset silence counter if sound detected
                self.current_silence_count = 0
            
            # Return True if we've had enough silence
            return self.current_silence_count >= self.silence_samples
            
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
            return False
    
    def get_audio(self) -> bytes:
        """Get all buffered audio as bytes"""
        return b''.join(self.buffer)
    
    def clear(self):
        """Clear the buffer"""
        self.buffer = []
        self.current_silence_count = 0


@app.websocket("/ws/audio/{session_id}")
async def websocket_audio_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming with ElevenLabs.
    
    Flow:
    1. Client connects and sends audio chunks
    2. Server buffers audio and detects silence
    3. After 2 seconds of silence, sends audio to ElevenLabs
    4. Streams ElevenLabs response back to client
    5. Continues until client disconnects
    
    Message format:
    - Client sends: binary audio data (PCM 16-bit, 16kHz recommended)
    - Server sends: JSON with response audio URL or direct audio bytes
    """
    await websocket.accept()
    print(f"WebSocket connection established for session: {session_id}")
    
    # Verify session exists (query directly without customer_rep_id check for customer access)
    try:
        result = db_service.supabase.table("sessions").select("*").eq("id", session_id).single().execute()
        if not result.data:
            await websocket.send_json({"error": "Session not found"})
            await websocket.close()
            return
        session = result.data
    except Exception as e:
        await websocket.send_json({"error": f"Failed to verify session: {str(e)}"})
        await websocket.close()
        return
    
    # Get agent_id from session metadata or use environment variable
    agent_id = session.get("metadata", {}).get("agent_id", os.getenv("ELEVENLABS_AGENT_ID", "default_agent"))
    
    # Validate agent_id
    if agent_id == "default_agent":
        await websocket.send_json({
            "error": "No valid ElevenLabs agent configured. Please set ELEVENLABS_AGENT_ID environment variable or create an agent.",
            "instructions": "Run 'python create_elevenlabs_agent.py' to create an agent"
        })
        await websocket.close()
        return
    
    audio_buffer = AudioBuffer(
        silence_threshold=0.01,  # Adjust based on your needs
        silence_duration=2.0,     # 2 seconds of silence
        sample_rate=16000         # 16kHz sample rate
    )
    
    elevenlabs_connection_id = None
    
    try:
        # Create ElevenLabs connection
        elevenlabs_connection_id = await elevenlabs_ws_service.create_connection(
            websocket=websocket,
            agent_id=agent_id,
            session_id=session_id,
            user_id=session.get("customer_rep_id", "customer")
        )
        
        print(f"Created ElevenLabs connection: {elevenlabs_connection_id}")
        
        await websocket.send_json({
            "status": "connected",
            "message": "Connected to ElevenLabs agent",
            "connection_id": elevenlabs_connection_id
        })
        
        while True:
            # Receive audio data from client
            data = await websocket.receive()
            
            if "bytes" in data:
                audio_chunk = data["bytes"]
                
                # Add chunk to buffer and check for silence
                silence_detected = audio_buffer.add_chunk(audio_chunk)
                
                if silence_detected:
                    print(f"Silence detected for session {session_id}, sending to ElevenLabs...")
                    
                    # Get all buffered audio
                    complete_audio = audio_buffer.get_audio()
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "status": "processing",
                        "message": "Audio received, sending to ElevenLabs..."
                    })
                    
                    try:
                        # Convert audio to base64 and send to ElevenLabs
                        import base64
                        audio_base64 = base64.b64encode(complete_audio).decode('ascii')
                        
                        print(f"Sending {len(complete_audio)} bytes to ElevenLabs via connection {elevenlabs_connection_id}")
                        
                        # Send audio chunk to ElevenLabs
                        await elevenlabs_ws_service.send_audio_chunk(
                            connection_id=elevenlabs_connection_id,
                            audio_data=complete_audio
                        )
                        
                        print(f"✅ Successfully sent audio to ElevenLabs")
                        
                        # The response will be handled by the ElevenLabs service
                        # and forwarded back to the client automatically
                        
                    except Exception as e:
                        print(f"❌ Error sending to ElevenLabs: {e}")
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "status": "error",
                            "error": str(e)
                        })
                    
                    # Clear buffer for next utterance
                    audio_buffer.clear()
            
            elif "text" in data:
                # Handle text messages (e.g., control messages)
                message = data["text"]
                print(f"Received text message: {message}")
                
                if message == "ping":
                    await websocket.send_json({"status": "pong"})
                    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        # Clean up ElevenLabs connection
        if elevenlabs_connection_id:
            await elevenlabs_ws_service.close_connection(elevenlabs_connection_id)
        print(f"Closing WebSocket for session: {session_id}")


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )