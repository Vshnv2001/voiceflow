# Transcript Storage Implementation

## ✅ Complete! Conversation transcripts are now automatically saved to the database.

---

## 🎯 What Was Implemented

### **1. Database Schema**
- Added `transcripts` column to `sessions` table
- Type: JSONB (stores structured conversation data)
- Default: Empty array `[]`
- Indexed with GIN index for fast queries

### **2. Transcript Storage**
- **User transcripts**: What the customer said
- **Agent transcripts**: What the AI agent responded
- **Automatic saving**: Happens in real-time during conversation

### **3. Data Structure**
Each transcript entry contains:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "speaker": "user" or "agent",
  "text": "The actual transcript text"
}
```

---

## 📝 Step 1: Run Database Migration

### **Option A: Using Supabase Dashboard (Recommended)**

1. Go to your Supabase Dashboard
2. Navigate to **SQL Editor**
3. Click **New Query**
4. Copy and paste this SQL:

```sql
-- Add transcripts column to sessions table
ALTER TABLE sessions 
ADD COLUMN IF NOT EXISTS transcripts JSONB DEFAULT '[]'::jsonb;

-- Add an index for faster queries
CREATE INDEX IF NOT EXISTS idx_sessions_transcripts 
ON sessions USING GIN (transcripts);

-- Add documentation
COMMENT ON COLUMN sessions.transcripts IS 
'Stores conversation transcripts as array of objects with timestamp, speaker, and text';
```

5. Click **Run** or press `Cmd/Ctrl + Enter`
6. You should see: "Success. No rows returned"

### **Option B: Using psql (Alternative)**

```bash
# Connect to your database
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run the migration
\i backend/migrations/add_transcripts_to_sessions.sql
```

---

## 🔄 How It Works

### **Automatic Transcript Capture**

According to the [ElevenLabs WebSocket API](https://elevenlabs.io/docs/agents-platform/api-reference/agents-platform/websocket), the following events are captured:

1. **User Transcript Event** (`user_transcript`):
   ```json
   {
     "type": "user_transcript",
     "user_transcription_event": {
       "user_transcript": "I need help with my order"
     }
   }
   ```

2. **Agent Response Event** (`agent_response`):
   ```json
   {
     "type": "agent_response",
     "agent_response_event": {
       "agent_response": "I'd be happy to help with your order"
     }
   }
   ```

### **Code Flow**

```
ElevenLabs → FastAPI Proxy → Database
         (websocket)    (append_transcript)
```

**File: `backend/websocket_proxy.py`** (lines 107-121)
```python
elif message_type == 'user_transcript':
    transcript = message.get('user_transcription_event', {}).get('user_transcript', '')
    logger.info(f"  👤 User said: {transcript}")
    
    # Save user transcript to database
    if transcript:
        await db_service.append_transcript(session_id, 'user', transcript)

elif message_type == 'agent_response':
    response = message.get('agent_response_event', {}).get('agent_response', '')
    logger.info(f"  🤖 Agent response: {response}")
    
    # Save agent response to database
    if response:
        await db_service.append_transcript(session_id, 'agent', response)
```

**File: `backend/services/database_service.py`** (lines 150-195)
```python
async def append_transcript(self, session_id: str, speaker: str, text: str) -> bool:
    """
    Append a transcript entry to the session's transcripts array.
    
    Args:
        session_id: The session ID
        speaker: 'user' or 'agent'
        text: The transcript text
    """
    # Get current transcripts
    result = self.supabase.table("sessions").select("transcripts").eq("id", session_id).single().execute()
    
    # Get existing transcripts or initialize empty array
    current_transcripts = result.data.get("transcripts", [])
    if current_transcripts is None:
        current_transcripts = []
    
    # Create new transcript entry
    new_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "speaker": speaker,
        "text": text
    }
    
    # Append new entry
    current_transcripts.append(new_entry)
    
    # Update the session
    update_result = self.supabase.table("sessions").update({
        "transcripts": current_transcripts
    }).eq("id", session_id).execute()
    
    return len(update_result.data) > 0
```

---

## 🧪 Step 2: Test Transcript Storage

### **Test the Full Flow**

1. **Start the backend:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Make a call:**
   - Go to `/reps` page
   - Click on a representative
   - Enter your name and click "Call Now"
   - Rep accepts the call
   - Customer is redirected to conversation page

4. **Have a conversation:**
   - Speak: "Hello, I need help"
   - AI responds: "Hello! How can I assist you today?"

5. **Check the logs:**
   Backend terminal should show:
   ```
   INFO: ElevenLabs → Frontend: user_transcript
   INFO:   👤 User said: Hello, I need help
   INFO: ✅ Transcript saved: [user] Hello, I need help...
   INFO: ElevenLabs → Frontend: agent_response
   INFO:   🤖 Agent response: Hello! How can I assist you today?
   INFO: ✅ Transcript saved: [agent] Hello! How can I assist you today...
   ```

6. **Verify in database:**
   ```sql
   -- In Supabase SQL Editor
   SELECT 
     id,
     customer_name,
     status,
     transcripts
   FROM sessions
   WHERE id = 'your-session-id'
   ORDER BY created_at DESC
   LIMIT 1;
   ```

   You should see:
   ```json
   {
     "transcripts": [
       {
         "timestamp": "2025-10-18T10:30:00Z",
         "speaker": "user",
         "text": "Hello, I need help"
       },
       {
         "timestamp": "2025-10-18T10:30:05Z",
         "speaker": "agent",
         "text": "Hello! How can I assist you today?"
       }
     ]
   }
   ```

---

## 📊 Querying Transcripts

### **Get all transcripts for a session**
```sql
SELECT transcripts FROM sessions WHERE id = 'session-id';
```

### **Search for specific words in transcripts**
```sql
SELECT 
  id,
  customer_name,
  transcripts
FROM sessions
WHERE transcripts::text ILIKE '%order%'
  AND status = 'closed'
ORDER BY created_at DESC;
```

### **Count messages per session**
```sql
SELECT 
  id,
  customer_name,
  jsonb_array_length(transcripts) as message_count
FROM sessions
WHERE transcripts IS NOT NULL
ORDER BY message_count DESC;
```

### **Get conversations with user messages only**
```sql
SELECT 
  id,
  customer_name,
  jsonb_path_query_array(
    transcripts,
    '$[*] ? (@.speaker == "user").text'
  ) as user_messages
FROM sessions
WHERE transcripts IS NOT NULL;
```

---

## ✅ Benefits

1. **📝 Full Conversation History**: Every word is saved
2. **🔍 Searchable**: Use PostgreSQL's JSONB queries
3. **📊 Analytics**: Analyze conversation patterns
4. **🐛 Debugging**: Review what customers said
5. **📈 Training**: Use transcripts to improve AI
6. **⚖️ Compliance**: Keep records for auditing

---

## 🔧 Troubleshooting

### **"Column 'transcripts' does not exist"**
- Run the migration SQL in Supabase Dashboard
- Verify with: `SELECT column_name FROM information_schema.columns WHERE table_name='sessions';`

### **"No transcripts being saved"**
- Check backend logs for "✅ Transcript saved" messages
- Verify ElevenLabs is sending `user_transcript` and `agent_response` events
- Check your ElevenLabs agent configuration

### **"Transcripts column is null"**
- The column might not have been created with default value
- Manually set: `UPDATE sessions SET transcripts = '[]'::jsonb WHERE transcripts IS NULL;`

---

## 📂 Files Modified

- ✅ `backend/migrations/add_transcripts_to_sessions.sql` - NEW: Database migration
- ✅ `backend/services/database_service.py` - Added `append_transcript()` method
- ✅ `backend/websocket_proxy.py` - Capture and save transcripts
- ✅ `TRANSCRIPT_STORAGE_SETUP.md` - This documentation

---

## 🎉 Summary

✅ **Database migration created**
✅ **Transcripts column added to sessions table**  
✅ **Automatic transcript capture implemented**
✅ **Real-time saving during conversations**
✅ **User and agent messages stored separately**
✅ **Timestamped for chronological order**
✅ **Ready to test!**

**Next steps:**
1. Run the migration SQL in Supabase
2. Test with a real conversation
3. Query transcripts in your database
4. Use for analytics/debugging/training

