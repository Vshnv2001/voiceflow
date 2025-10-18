# VoiceFlow AI - Implementation Guide

## 🎯 Overview

This guide provides a comprehensive implementation plan for your voice-based customer service system. The system allows users to send voice messages, generates AI responses via Groq, and enables agent approval workflows.

## 🏗️ Architecture

```
Frontend (Next.js) ←→ Backend (FastAPI) ←→ Supabase (PostgreSQL)
                           ↓
                    External APIs:
                    - ElevenLabs (Voice Synthesis)
                    - Groq (AI Responses)
                    - OpenAI (Alternative AI)
```

## 📋 Prerequisites

### Required Services & APIs

1. **Supabase Account**
   - PostgreSQL database
   - Authentication
   - Storage for audio files
   - Row Level Security (RLS)

2. **ElevenLabs API**
   - Voice synthesis (Text-to-Speech)
   - Voice cloning (optional)
   - Speech-to-Text (if using their STT service)

3. **Groq API**
   - Fast LLM inference
   - Alternative: OpenAI API

4. **Optional Services**
   - Redis (for background tasks)
   - Sentry (error monitoring)
   - Vercel/AWS (deployment)

## 🚀 Step-by-Step Implementation

### Phase 1: Database Setup

1. **Create Supabase Project**
   ```bash
   # Go to https://supabase.com
   # Create new project
   # Note down your project URL and API keys
   ```

2. **Run Database Schema**
   ```sql
   -- Execute the schema from backend/db_schema/voice_service_schema.sql
   -- This creates all necessary tables with RLS policies
   ```

3. **Set up Storage Bucket**
   ```sql
   -- In Supabase Dashboard > Storage
   -- Create bucket: voice-messages
   -- Set public access if needed
   ```

### Phase 2: Backend Setup

1. **Install Dependencies**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your actual API keys
   ```

3. **Test Backend**
   ```bash
   python main.py
   # Should start on http://localhost:8000
   ```

### Phase 3: Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure Environment**
   ```bash
   # Add to frontend/.env.local
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Test Frontend**
   ```bash
   npm run dev
   # Should start on http://localhost:3000
   ```

### Phase 4: API Integration Setup

1. **ElevenLabs Setup**
   ```bash
   # Get API key from https://elevenlabs.io
   # Add to backend/.env
   ELEVENLABS_API_KEY=your_key_here
   ```

2. **Groq Setup**
   ```bash
   # Get API key from https://groq.com
   # Add to backend/.env
   GROQ_API_KEY=your_key_here
   ```

3. **Test Integrations**
   ```python
   # Test voice synthesis
   python -c "
   from services.voice_service import VoiceService
   vs = VoiceService()
   print(vs.synthesize_audio('Hello world'))
   "
   ```

### Phase 5: User Roles Setup

1. **Create Admin User**
   ```sql
   -- In Supabase Dashboard > Authentication > Users
   -- Create user with role: admin
   ```

2. **Create Agent Users**
   ```sql
   -- Create users with role: agent
   -- These can approve AI responses
   ```

3. **Test Authentication**
   ```bash
   # Test login flow in frontend
   # Verify role-based access
   ```

## 🔧 Configuration Details

### Environment Variables

#### Backend (.env)
```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# APIs
ELEVENLABS_API_KEY=sk_...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-... # Alternative

# Security
JWT_SECRET=your_jwt_secret

# Storage
STORAGE_BUCKET=voice-messages
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Database Tables

1. **sessions** - Customer service conversations
2. **messages** - Voice/text messages in conversations
3. **voice_processing_jobs** - Async voice processing tasks
4. **agent_responses** - Agent-approved responses for learning
5. **system_config** - API keys and settings

## 🎮 Usage Workflow

### Customer Flow
1. User visits `/chat`
2. Records voice message
3. System transcribes using ElevenLabs
4. AI generates response using Groq
5. Response sent back as voice message

### Agent Flow
1. Agent visits `/agent`
2. Reviews pending AI responses
3. Approves, rejects, or edits responses
4. Approved responses sent to customer

## 🔌 API Endpoints

### Session Management
- `POST /api/sessions` - Create new session
- `GET /api/sessions` - List user sessions
- `GET /api/sessions/{id}` - Get specific session
- `PATCH /api/sessions/{id}` - Update session

### Message Handling
- `POST /api/sessions/{id}/messages/voice` - Upload voice message
- `GET /api/sessions/{id}/messages` - Get session messages
- `POST /api/messages/{id}/generate-ai-response` - Generate AI response

### Agent Operations
- `GET /api/agent/pending-messages` - Get pending approvals
- `POST /api/messages/{id}/approve` - Approve/reject message

### Voice Processing
- `GET /api/voice-jobs/{id}` - Get job status
- `POST /api/voice/synthesize` - Convert text to speech

## 🚀 Deployment

### Backend Deployment (Railway/Render)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Frontend Deployment (Vercel)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

### Environment Variables
Set all environment variables in your deployment platform:
- Supabase credentials
- API keys (ElevenLabs, Groq)
- JWT secret
- CORS origins

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Test voice upload
curl -X POST http://localhost:8000/api/sessions/{id}/messages/voice \
  -F "audio_file=@test.m4a"

# Test AI response
curl -X POST http://localhost:8000/api/messages/{id}/generate-ai-response
```

## 📊 Monitoring

### Error Tracking
- Sentry integration for error monitoring
- Logging with structured logs
- Health check endpoint: `/health`

### Analytics
- Message volume tracking
- Response time metrics
- Agent approval rates
- Voice quality metrics

## 🔒 Security Considerations

1. **API Key Management**
   - Store keys in environment variables
   - Use Supabase RLS for data access
   - Implement rate limiting

2. **Audio File Security**
   - Validate file types and sizes
   - Scan for malicious content
   - Implement access controls

3. **User Authentication**
   - JWT token validation
   - Role-based access control
   - Session management

## 🎯 Next Steps

1. **Set up development environment**
2. **Configure all API keys**
3. **Test basic voice flow**
4. **Implement agent dashboard**
5. **Add monitoring and analytics**
6. **Deploy to production**

## 🆘 Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check CORS_ORIGINS in backend
   - Verify frontend API_URL

2. **Authentication Issues**
   - Verify Supabase keys
   - Check JWT secret

3. **Voice Processing Fails**
   - Check ElevenLabs API key
   - Verify audio file format

4. **AI Responses Not Generated**
   - Check Groq API key
   - Verify model availability

### Support
- Check logs in Supabase Dashboard
- Monitor API usage in service dashboards
- Use health check endpoints for debugging

## 📈 Scaling Considerations

1. **Database**
   - Use connection pooling
   - Implement read replicas
   - Add database indexes

2. **Voice Processing**
   - Use background job queues
   - Implement retry logic
   - Add caching for repeated requests

3. **AI Responses**
   - Cache common responses
   - Use streaming for long responses
   - Implement response templates

4. **Storage**
   - Use CDN for audio files
   - Implement file compression
   - Add cleanup jobs for old files
