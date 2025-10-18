-- Voice Service Customer Support System Database Schema (Simplified - No Voice Cloning)
-- This schema focuses on the core voice service workflow without voice cloning functionality

-- 1. Sessions table - tracks customer service conversations
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    customer_id UUID, -- Optional: if different from user_id (for agent view)
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed', 'paused')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb -- Store additional session context
);

-- 2. Messages table - stores all voice and text messages in conversations
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('customer', 'agent', 'system')),
    message_type TEXT NOT NULL CHECK (message_type IN ('voice', 'text', 'ai_generated')),
    
    -- Voice message fields
    voice_audio_url TEXT, -- URL to stored audio file
    voice_duration_seconds INTEGER,
    voice_transcription TEXT,
    voice_id TEXT, -- ElevenLabs voice ID used for synthesis (default voices only)
    
    -- Text message fields
    text_content TEXT,
    
    -- AI generation fields
    ai_model TEXT, -- e.g., 'groq/llama-3.1-70b-versatile'
    ai_prompt TEXT, -- The prompt used for generation
    ai_temperature DECIMAL(3,2) DEFAULT 0.7,
    
    -- Approval workflow
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'edited')),
    approved_by UUID REFERENCES auth.users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    edited_content TEXT, -- If agent edited the AI response
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Voice processing jobs table - tracks async voice processing tasks
CREATE TABLE IF NOT EXISTS voice_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL CHECK (job_type IN ('transcription', 'synthesis')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    
    -- Service provider details
    provider TEXT NOT NULL, -- 'elevenlabs', 'openai', etc.
    provider_job_id TEXT, -- External service job ID
    
    -- Processing details
    input_url TEXT, -- Input audio URL for transcription
    output_url TEXT, -- Output audio URL for synthesis
    voice_id TEXT, -- Voice ID used for synthesis
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 4. Agent responses table - stores agent-approved responses for learning
CREATE TABLE IF NOT EXISTS agent_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    original_ai_response TEXT NOT NULL,
    agent_edited_response TEXT NOT NULL,
    agent_id UUID NOT NULL REFERENCES auth.users(id),
    edit_reason TEXT, -- Why the agent made changes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. System configuration table - stores API keys and settings
CREATE TABLE IF NOT EXISTS system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Available voices table - stores default ElevenLabs voices
CREATE TABLE IF NOT EXISTS available_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_id TEXT UNIQUE NOT NULL, -- ElevenLabs voice ID
    name TEXT NOT NULL,
    description TEXT,
    category TEXT, -- e.g., 'male', 'female', 'child', 'elderly'
    language TEXT DEFAULT 'en',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender_type ON messages(sender_type);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_voice_id ON messages(voice_id);

CREATE INDEX IF NOT EXISTS idx_voice_jobs_message_id ON voice_processing_jobs(message_id);
CREATE INDEX IF NOT EXISTS idx_voice_jobs_status ON voice_processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_voice_jobs_type ON voice_processing_jobs(job_type);

CREATE INDEX IF NOT EXISTS idx_agent_responses_message_id ON agent_responses(message_id);
CREATE INDEX IF NOT EXISTS idx_agent_responses_agent_id ON agent_responses(agent_id);

CREATE INDEX IF NOT EXISTS idx_available_voices_voice_id ON available_voices(voice_id);
CREATE INDEX IF NOT EXISTS idx_available_voices_category ON available_voices(category);
CREATE INDEX IF NOT EXISTS idx_available_voices_is_active ON available_voices(is_active);

-- Enable Row Level Security (RLS)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_processing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE available_voices ENABLE ROW LEVEL SECURITY;

-- RLS Policies for sessions
CREATE POLICY "Users can view their own sessions" ON sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own sessions" ON sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own sessions" ON sessions
    FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policies for messages
CREATE POLICY "Users can view messages in their sessions" ON messages
    FOR SELECT USING (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create messages in their sessions" ON messages
    FOR INSERT WITH CHECK (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- RLS Policies for voice processing jobs
CREATE POLICY "Users can view voice jobs for their messages" ON voice_processing_jobs
    FOR SELECT USING (
        message_id IN (
            SELECT m.id FROM messages m
            JOIN sessions s ON m.session_id = s.id
            WHERE s.user_id = auth.uid()
        )
    );

-- RLS Policies for agent responses
CREATE POLICY "Users can view agent responses for their messages" ON agent_responses
    FOR SELECT USING (
        message_id IN (
            SELECT m.id FROM messages m
            JOIN sessions s ON m.session_id = s.id
            WHERE s.user_id = auth.uid()
        )
    );

-- RLS Policies for system config (admin only)
CREATE POLICY "Only admins can access system config" ON system_config
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE id = auth.uid() 
            AND raw_user_meta_data->>'role' = 'admin'
        )
    );

-- RLS Policies for available voices (read-only for all users)
CREATE POLICY "All users can view available voices" ON available_voices
    FOR SELECT USING (is_active = true);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at 
    BEFORE UPDATE ON messages 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at 
    BEFORE UPDATE ON system_config 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_available_voices_updated_at 
    BEFORE UPDATE ON available_voices 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default system configuration
INSERT INTO system_config (key, value, description, is_encrypted) VALUES
('elevenlabs_api_key', '', 'ElevenLabs API key for voice synthesis', true),
('groq_api_key', '', 'Groq API key for LLM responses', true),
('default_voice_id', 'pNInz6obpgDQGcFmaJgB', 'Default ElevenLabs voice ID (Adam)', false),
('ai_model', 'groq/llama-3.1-70b-versatile', 'Default AI model for responses', false),
('ai_temperature', '0.7', 'Default AI temperature setting', false),
('max_voice_duration', '300', 'Maximum voice message duration in seconds', false)
ON CONFLICT (key) DO NOTHING;

-- Insert default ElevenLabs voices
INSERT INTO available_voices (voice_id, name, description, category, language) VALUES
('pNInz6obpgDQGcFmaJgB', 'Adam', 'A calm, confident male voice', 'male', 'en'),
('EXAVITQu4vr4xnSDxMaL', 'Bella', 'A warm, friendly female voice', 'female', 'en'),
('MF3mGyEYCl7XYWbV9V6O', 'Elli', 'A young, energetic female voice', 'female', 'en'),
('TxGEqnHWrfWFTfGW9XjX', 'Josh', 'A deep, authoritative male voice', 'male', 'en'),
('VR6AewLTigWG4xSOukaG', 'Arnold', 'A mature, professional male voice', 'male', 'en'),
('AZnzlk1XvdvUeBnXmlld', 'Domi', 'A clear, articulate female voice', 'female', 'en'),
('ErXwobaYiN019PkySvjV', 'Antoni', 'A smooth, charismatic male voice', 'male', 'en'),
('VR6AewLTigWG4xSOukaG', 'Thomas', 'A warm, conversational male voice', 'male', 'en'),
('EXAVITQu4vr4xnSDxMaL', 'Charlie', 'A cheerful, upbeat male voice', 'male', 'en'),
('MF3mGyEYCl7XYWbV9V6O', 'Emily', 'A professional, clear female voice', 'female', 'en')
ON CONFLICT (voice_id) DO NOTHING;
