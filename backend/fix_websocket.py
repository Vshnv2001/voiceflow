#!/usr/bin/env python3
"""
Script to replace old WebSocket endpoints with new proxy endpoint
"""

# Read the original file
with open('main.py', 'r') as f:
    lines = f.readlines()

# Keep everything up to line 738
new_lines = lines[:738]

# Add the new WebSocket endpoint
new_websocket_code = """
# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws/conversation/{session_id}")
async def websocket_conversation_proxy(websocket: WebSocket, session_id: str):
    \"\"\"
    WebSocket proxy endpoint that forwards messages between frontend and ElevenLabs API.
    
    This endpoint:
    1. Accepts WebSocket connection from frontend
    2. Establishes connection to ElevenLabs API
    3. Forwards messages bidirectionally
    4. Logs all conversation data
    
    Usage:
        Frontend connects to: ws://localhost:8000/ws/conversation/{session_id}
        
    Message Flow:
        Frontend → FastAPI → ElevenLabs (user audio, messages)
        ElevenLabs → FastAPI → Frontend (agent audio, transcripts)
    \"\"\"
    await websocket.accept()
    
    try:
        await handle_elevenlabs_proxy(
            frontend_ws=websocket,
            session_id=session_id,
            agent_id=elevenlabs_agent_id,
            db_service=db_service
        )
    except Exception as e:
        logger.error(f"WebSocket proxy error for session {session_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

"""

new_lines.append(new_websocket_code)

# Add everything from line 1022 onwards (HEALTH CHECK section)
new_lines.extend(lines[1021:])

# Write the new file
with open('main.py', 'w') as f:
    f.writelines(new_lines)

print("✅ WebSocket endpoints replaced successfully!")
print(f"   Removed lines: 739-1021 (old WebSocket code)")
print(f"   Added: New proxy endpoint")
print(f"   Total lines: {len(new_lines)}")

