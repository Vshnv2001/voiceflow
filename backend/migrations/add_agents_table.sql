-- Add agents table for storing ElevenLabs agent configurations
-- This table stores the mapping between users and their ElevenLabs agents

-- 11. Agents table - stores ElevenLabs agent configurations per user
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    elevenlabs_agent_id TEXT NOT NULL UNIQUE, -- ElevenLabs agent ID
    agent_name TEXT NOT NULL,
    voice_id TEXT NOT NULL, -- ElevenLabs voice ID used for this agent
    first_message TEXT NOT NULL, -- Initial message the agent will say
    knowledge_base_file_ids TEXT[] NOT NULL DEFAULT '{}', -- Array of ElevenLabs file IDs
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deleted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add elevenlabs_file_id column to knowledge_documents table if it doesn't exist
ALTER TABLE knowledge_documents 
ADD COLUMN IF NOT EXISTS elevenlabs_file_id TEXT;

-- Create indexes for agents table
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_elevenlabs_agent_id ON agents(elevenlabs_agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at);

-- Enable RLS for agents table
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- RLS Policies for agents
CREATE POLICY "Users can view their own agents" ON agents
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own agents" ON agents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own agents" ON agents
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own agents" ON agents
    FOR DELETE USING (auth.uid() = user_id);

-- Create trigger for agents table
CREATE TRIGGER update_agents_updated_at 
    BEFORE UPDATE ON agents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
