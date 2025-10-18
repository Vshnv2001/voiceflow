-- Migration: Add transcripts column to sessions table
-- This stores the conversation history between user and AI agent

-- Add transcripts column as JSONB to store structured conversation data
ALTER TABLE sessions 
ADD COLUMN IF NOT EXISTS transcripts JSONB DEFAULT '[]'::jsonb;

-- Add an index for faster queries on transcripts
CREATE INDEX IF NOT EXISTS idx_sessions_transcripts ON sessions USING GIN (transcripts);

-- Add comment to document the column
COMMENT ON COLUMN sessions.transcripts IS 'Stores conversation transcripts as array of objects with timestamp, speaker, and text';

-- Example transcript structure:
-- [
--   {
--     "timestamp": "2024-01-15T10:30:00Z",
--     "speaker": "user",
--     "text": "Hello, I need help with my order"
--   },
--   {
--     "timestamp": "2024-01-15T10:30:05Z",
--     "speaker": "agent",
--     "text": "Hello! I'd be happy to help with your order. Could you provide your order number?"
--   }
-- ]

