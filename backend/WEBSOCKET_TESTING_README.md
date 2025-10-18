# WebSocket Testing Guide

This guide explains how to test the WebSocket connections in the VoiceFlow AI backend to ensure proper communication between:
1. Client ↔ Database WebSocket
2. Database ↔ ElevenLabs WebSocket
3. ElevenLabs → Database → Client response flow

## Prerequisites

1. **Backend Running**: Make sure the FastAPI backend is running on `localhost:8000`
2. **ElevenLabs Agent**: Ensure you have a valid ElevenLabs agent ID
3. **Environment Variables**: Set the required environment variables

### Required Environment Variables

```bash
export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
export ELEVENLABS_AGENT_ID="your_agent_id"  # Optional, defaults to test agent
```

## Test Scripts

### 1. Simple WebSocket Test (`test_websocket_simple.py`)

**Purpose**: Test basic WebSocket connections without audio files

**What it tests**:
- Backend health check
- WebSocket connection establishment
- ElevenLabs connection establishment
- Text message sending
- Response receiving
- Complete round-trip communication

**Usage**:
```bash
cd /Users/chaitanya/Documents/Coding/voiceflow/backend
python test_websocket_simple.py
```

**Expected Output**:
```
🚀 Starting Simple WebSocket Connection Tests
🔍 Checking backend health...
✅ Backend is running and healthy
🔌 Testing WebSocket flow: ws://localhost:8000/ws/elevenlabs/agent_xxx?session_id=test_session_xxx&user_id=test_user_xxx
✅ WebSocket connected successfully!
📨 Connection confirmation: {'type': 'connection_established', ...}
✅ Connection established successfully
⏳ Waiting for ElevenLabs initiation metadata...
✅ ElevenLabs initiation received: {...}
✅ ElevenLabs connection established
📤 Sending text message to ElevenLabs...
✅ Text message sent
👂 Listening for responses from ElevenLabs...
📨 Response 1: conversation_initiation_metadata
📨 Response 2: agent_response
🤖 Agent response: Hello! I can hear you. How can I help you today?
✅ Responses received successfully
```

### 2. Comprehensive WebSocket Test (`test_websocket_flow.py`)

**Purpose**: Test complete WebSocket flow including audio processing

**What it tests**:
- All simple test features
- Audio file processing (if available)
- Audio WebSocket endpoint testing
- Audio response collection and playback
- File saving capabilities

**Requirements**:
- Audio file at `test/test.mp3` (optional)
- `pydub` library for audio processing

**Usage**:
```bash
# Install audio processing dependencies
pip install pydub

# Run the comprehensive test
python test_websocket_flow.py
```

## Understanding the Test Results

### Test Components

1. **Backend Health**: Verifies the FastAPI server is running
2. **WebSocket Connection**: Tests connection to `/ws/elevenlabs/{agent_id}`
3. **ElevenLabs Connection**: Verifies ElevenLabs agent connection
4. **Text Message Sending**: Tests sending text messages to ElevenLabs
5. **Response Receiving**: Verifies responses are received from ElevenLabs
6. **Complete Flow**: Overall assessment of the entire flow

### Success Indicators

✅ **All tests pass** means:
- WebSocket connections are working
- ElevenLabs agent is responding
- Data flows correctly in both directions
- The complete round-trip communication works

❌ **Test failures** indicate:
- Backend not running (check `python main.py`)
- Invalid ElevenLabs agent ID
- Network connectivity issues
- ElevenLabs API problems

## Troubleshooting

### Common Issues

1. **"Cannot connect to backend"**
   - Ensure backend is running: `python main.py`
   - Check if port 8000 is available
   - Verify no firewall blocking

2. **"ElevenLabs agent not found"**
   - Verify `ELEVENLABS_AGENT_ID` is correct
   - Check agent exists in ElevenLabs dashboard
   - Run `python create_elevenlabs_agent.py` to create agent

3. **"No responses received"**
   - Check ElevenLabs API key is valid
   - Verify agent is properly configured
   - Check network connectivity to ElevenLabs

4. **"Timeout waiting for initiation metadata"**
   - ElevenLabs connection may be slow
   - Check ElevenLabs service status
   - Verify agent configuration

### Debug Mode

Enable debug logging for more detailed output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## WebSocket Endpoints

### 1. ElevenLabs Agent WebSocket
- **URL**: `ws://localhost:8000/ws/elevenlabs/{agent_id}?session_id={session_id}&user_id={user_id}`
- **Purpose**: Main conversation endpoint with ElevenLabs agent
- **Features**: Text messages, audio chunks, user activity

### 2. Audio WebSocket
- **URL**: `ws://localhost:8000/ws/audio/{session_id}`
- **Purpose**: Direct audio streaming endpoint
- **Features**: Raw audio data streaming, silence detection

## Message Types

### Client → ElevenLabs
- `user_message`: Text messages
- `user_audio_chunk`: Audio data (base64 encoded)
- `user_activity`: User activity indicators
- `pong`: Response to ping

### ElevenLabs → Client
- `conversation_initiation_metadata`: Initial setup
- `agent_response`: Text responses from agent
- `audio`: Audio responses (base64 encoded)
- `user_transcript`: Transcribed user speech
- `ping`: Keep-alive ping

## Configuration

### Environment Variables
```bash
# Required
ELEVENLABS_API_KEY=your_api_key_here

# Optional
ELEVENLABS_AGENT_ID=your_agent_id_here
```

### Test Configuration
Edit the test scripts to modify:
- Backend URL
- Agent ID
- Timeout values
- Audio file paths
- Response handling

## Monitoring

### Logs to Watch
- Backend logs: Check console output from `python main.py`
- ElevenLabs service logs: Check connection status
- Test script logs: Detailed test execution info

### Health Checks
- Backend: `GET http://localhost:8000/health`
- WebSocket connections: Check active connections in logs
- ElevenLabs: Monitor response times and success rates

## Next Steps

After successful testing:
1. Integrate WebSocket client into your frontend
2. Implement proper error handling
3. Add reconnection logic
4. Optimize audio processing
5. Add user authentication

## Support

If tests fail:
1. Check this troubleshooting guide
2. Review backend logs
3. Verify ElevenLabs configuration
4. Test with simple text messages first
5. Check network connectivity
