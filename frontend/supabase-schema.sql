-- Create the reps table
CREATE TABLE IF NOT EXISTS public.reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    organization TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    avatar_url TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'break', 'offline')),
    calls_handled INTEGER DEFAULT 0,
    avg_response_time TEXT DEFAULT '0s',
    satisfaction INTEGER DEFAULT 0 CHECK (satisfaction >= 0 AND satisfaction <= 100),
    current_calls INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.reps ENABLE ROW LEVEL SECURITY;

-- Create policies for the reps table
-- Allow users to read all reps (for the reps page)
CREATE POLICY "Allow read access to all reps" ON public.reps
    FOR SELECT USING (true);

-- Allow users to insert their own rep record
CREATE POLICY "Allow users to insert their own rep" ON public.reps
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Allow users to update their own rep record
CREATE POLICY "Allow users to update their own rep" ON public.reps
    FOR UPDATE USING (auth.uid() = user_id);

-- Create an index on user_id for better performance
CREATE INDEX IF NOT EXISTS idx_reps_user_id ON public.reps(user_id);

-- Create an index on organization for filtering
CREATE INDEX IF NOT EXISTS idx_reps_organization ON public.reps(organization);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update the updated_at column
CREATE TRIGGER update_reps_updated_at 
    BEFORE UPDATE ON public.reps 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
