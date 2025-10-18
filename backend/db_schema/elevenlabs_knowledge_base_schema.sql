-- ElevenLabs Knowledge Base Integration Schema
-- This schema tracks files uploaded to ElevenLabs knowledge base API

-- 1. ElevenLabs knowledge base files table - tracks files uploaded to ElevenLabs
CREATE TABLE IF NOT EXISTS elevenlabs_knowledge_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    elevenlabs_file_id TEXT NOT NULL UNIQUE, -- ElevenLabs API returned file ID
    elevenlabs_name TEXT NOT NULL, -- Name returned by ElevenLabs API
    original_filename TEXT NOT NULL, -- Original filename from upload
    file_type TEXT NOT NULL, -- File extension/type
    file_size BIGINT NOT NULL, -- File size in bytes
    upload_status TEXT NOT NULL DEFAULT 'uploading' CHECK (upload_status IN ('uploading', 'completed', 'failed')),
    error_message TEXT, -- Error message if upload failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. ElevenLabs knowledge base collections table - tracks collections created in ElevenLabs
CREATE TABLE IF NOT EXISTS elevenlabs_knowledge_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    elevenlabs_collection_id TEXT NOT NULL UNIQUE, -- ElevenLabs API returned collection ID
    elevenlabs_name TEXT NOT NULL, -- Name returned by ElevenLabs API
    local_name TEXT NOT NULL, -- Local name for reference
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. File-collection mapping table for ElevenLabs
CREATE TABLE IF NOT EXISTS elevenlabs_file_collections (
    file_id UUID NOT NULL REFERENCES elevenlabs_knowledge_files(id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES elevenlabs_knowledge_collections(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (file_id, collection_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_elevenlabs_files_user_id ON elevenlabs_knowledge_files(user_id);
CREATE INDEX IF NOT EXISTS idx_elevenlabs_files_elevenlabs_id ON elevenlabs_knowledge_files(elevenlabs_file_id);
CREATE INDEX IF NOT EXISTS idx_elevenlabs_files_status ON elevenlabs_knowledge_files(upload_status);
CREATE INDEX IF NOT EXISTS idx_elevenlabs_files_created_at ON elevenlabs_knowledge_files(created_at);

CREATE INDEX IF NOT EXISTS idx_elevenlabs_collections_user_id ON elevenlabs_knowledge_collections(user_id);
CREATE INDEX IF NOT EXISTS idx_elevenlabs_collections_elevenlabs_id ON elevenlabs_knowledge_collections(elevenlabs_collection_id);

CREATE INDEX IF NOT EXISTS idx_elevenlabs_file_collections_file_id ON elevenlabs_file_collections(file_id);
CREATE INDEX IF NOT EXISTS idx_elevenlabs_file_collections_collection_id ON elevenlabs_file_collections(collection_id);

-- Enable Row Level Security (RLS)
ALTER TABLE elevenlabs_knowledge_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE elevenlabs_knowledge_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE elevenlabs_file_collections ENABLE ROW LEVEL SECURITY;

-- RLS Policies for elevenlabs_knowledge_files
CREATE POLICY "Users can view their own ElevenLabs files" ON elevenlabs_knowledge_files
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own ElevenLabs files" ON elevenlabs_knowledge_files
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own ElevenLabs files" ON elevenlabs_knowledge_files
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own ElevenLabs files" ON elevenlabs_knowledge_files
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for elevenlabs_knowledge_collections
CREATE POLICY "Users can view their own ElevenLabs collections" ON elevenlabs_knowledge_collections
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own ElevenLabs collections" ON elevenlabs_knowledge_collections
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own ElevenLabs collections" ON elevenlabs_knowledge_collections
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own ElevenLabs collections" ON elevenlabs_knowledge_collections
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for elevenlabs_file_collections
CREATE POLICY "Users can view file-collection mappings for their files" ON elevenlabs_file_collections
    FOR SELECT USING (
        file_id IN (
            SELECT id FROM elevenlabs_knowledge_files WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create file-collection mappings for their files" ON elevenlabs_file_collections
    FOR INSERT WITH CHECK (
        file_id IN (
            SELECT id FROM elevenlabs_knowledge_files WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete file-collection mappings for their files" ON elevenlabs_file_collections
    FOR DELETE USING (
        file_id IN (
            SELECT id FROM elevenlabs_knowledge_files WHERE user_id = auth.uid()
        )
    );

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_elevenlabs_files_updated_at 
    BEFORE UPDATE ON elevenlabs_knowledge_files 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_elevenlabs_collections_updated_at 
    BEFORE UPDATE ON elevenlabs_knowledge_collections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add foreign key constraint to link with existing knowledge_documents table
-- This allows us to maintain a relationship between our local knowledge base and ElevenLabs
-- Note: elevenlabs_file_id is TEXT because ElevenLabs returns string IDs, not UUIDs
ALTER TABLE knowledge_documents 
ADD COLUMN IF NOT EXISTS elevenlabs_file_id TEXT;

-- Create index for the new foreign key
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_elevenlabs_file_id ON knowledge_documents(elevenlabs_file_id);

-- Add RLS policy for the new column
-- Users can view the elevenlabs_file_id for their own documents
-- (This is already covered by existing RLS policies on knowledge_documents)
