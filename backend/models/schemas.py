"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    PAUSED = "paused"

class MessageType(str, Enum):
    VOICE = "voice"
    TEXT = "text"
    AI_GENERATED = "ai_generated"

class SenderType(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"

class MessageStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"

class JobType(str, Enum):
    TRANSCRIPTION = "transcription"
    SYNTHESIS = "synthesis"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# ==================== SESSION SCHEMAS ====================

class SessionCreate(BaseModel):
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    id: str
    user_id: str
    customer_id: Optional[str]
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True

# ==================== MESSAGE SCHEMAS ====================

class MessageCreate(BaseModel):
    sender_type: SenderType
    message_type: MessageType
    text_content: Optional[str] = None
    voice_audio_url: Optional[str] = None
    voice_duration_seconds: Optional[int] = None
    voice_transcription: Optional[str] = None
    voice_id: Optional[str] = None
    ai_model: Optional[str] = None
    ai_prompt: Optional[str] = None
    ai_temperature: Optional[float] = 0.7

class MessageResponse(BaseModel):
    id: str
    session_id: str
    sender_type: SenderType
    message_type: MessageType
    voice_audio_url: Optional[str]
    voice_duration_seconds: Optional[int]
    voice_transcription: Optional[str]
    voice_id: Optional[str]
    text_content: Optional[str]
    ai_model: Optional[str]
    ai_prompt: Optional[str]
    ai_temperature: Optional[float]
    status: MessageStatus
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    edited_content: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ==================== VOICE PROCESSING SCHEMAS ====================

class VoiceProcessingJobResponse(BaseModel):
    id: str
    message_id: str
    job_type: JobType
    status: JobStatus
    provider: str
    provider_job_id: Optional[str]
    input_url: Optional[str]
    output_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# ==================== AGENT APPROVAL SCHEMAS ====================

class AgentApprovalRequest(BaseModel):
    approved: bool
    edited_content: Optional[str] = None
    edit_reason: Optional[str] = None

class AgentResponseCreate(BaseModel):
    message_id: str
    original_ai_response: str
    agent_edited_response: str
    edit_reason: Optional[str] = None

# ==================== SYSTEM CONFIGURATION SCHEMAS ====================

class SystemConfigUpdate(BaseModel):
    key: str
    value: str

class SystemConfigResponse(BaseModel):
    key: str
    value: str
    description: Optional[str]
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ==================== VOICE MANAGEMENT SCHEMAS ====================

class VoiceResponse(BaseModel):
    id: str
    voice_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    language: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VoiceSynthesisRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

class VoiceSynthesisResponse(BaseModel):
    audio_url: str
    voice_id: str
    text: str

# ==================== VOICE UPLOAD SCHEMAS ====================

class VoiceUploadResponse(BaseModel):
    message_id: str
    audio_url: str
    processing_job_id: str
    status: str = "processing"

# ==================== AI RESPONSE SCHEMAS ====================

class AIResponseRequest(BaseModel):
    message_id: str
    model: Optional[str] = "gpt-4o-mini"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

class AIResponseResponse(BaseModel):
    message_id: str
    ai_response: str
    model: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None

# ==================== ERROR SCHEMAS ====================

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ==================== PAGINATION SCHEMAS ====================

class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool
