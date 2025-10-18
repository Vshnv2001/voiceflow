"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Mic, MicOff, Volume2, VolumeX, Phone, PhoneOff } from "lucide-react"

interface RealtimeVoiceChatProps {
  sessionId: string
  onCallEnd: () => void
}

interface WebSocketMessage {
  type: string
  status?: string
  message?: string
  audio_url?: string
  text?: string
  timestamp: number
}

export default function RealtimeVoiceChat({ sessionId, onCallEnd }: RealtimeVoiceChatProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isSpeakerOn, setIsSpeakerOn] = useState(true)
  const [status, setStatus] = useState("Connecting...")
  const [currentText, setCurrentText] = useState("")
  
  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const audioQueueRef = useRef<HTMLAudioElement[]>([])
  const isPlayingRef = useRef(false)
  const streamRef = useRef<MediaStream | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isMutedRef = useRef(false)

  // Initialize WebSocket connection
  useEffect(() => {
    connectWebSocket()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [sessionId])

  // Initialize mute ref
  useEffect(() => {
    isMutedRef.current = isMuted
  }, [isMuted])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording()
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const connectWebSocket = useCallback(() => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const wsUrl = `${protocol}//${apiBase.replace(/^https?:\/\//, '')}/ws/conversation/${sessionId}`
      
      console.log('Connecting to WebSocket:', wsUrl)
      wsRef.current = new WebSocket(wsUrl)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setStatus("Connected - Ready to speak")
      }
      
      wsRef.current.onmessage = (event) => {
        const message: WebSocketMessage = JSON.parse(event.data)
        handleWebSocketMessage(message)
      }
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        setStatus("Disconnected")
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connectWebSocket()
        }, 3000)
      }
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setStatus("Connection error - Check if backend is running")
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setStatus("Connection failed")
    }
  }, [sessionId])

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'status_update':
        setStatus(message.message || message.status || '')
        break
      case 'audio_response':
        if (message.audio_url && isSpeakerOn) {
          playAudioResponse(message.audio_url)
        }
        if (message.text) {
          setCurrentText(message.text)
        }
        break
      case 'pong':
        // Handle ping/pong for connection health
        break
    }
  }, [isSpeakerOn])

  const playAudioResponse = useCallback(async (audioUrl: string) => {
    try {
      if (!isSpeakerOn) return
      
      const audio = new Audio(audioUrl)
      audioQueueRef.current.push(audio)
      
      if (!isPlayingRef.current) {
        playNextAudio()
      }
    } catch (error) {
      console.error('Error playing audio:', error)
    }
  }, [isSpeakerOn])

  const playNextAudio = useCallback(async () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false
      return
    }
    
    isPlayingRef.current = true
    const audio = audioQueueRef.current.shift()!
    
    audio.onended = () => {
      playNextAudio()
    }
    
    audio.onerror = () => {
      console.error('Audio playback error')
      playNextAudio()
    }
    
    try {
      await audio.play()
    } catch (error) {
      console.error('Error playing audio:', error)
      playNextAudio()
    }
  }, [])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      })
      
      streamRef.current = stream
      
      // Create MediaRecorder with fallback MIME types
      let mimeType = 'audio/webm;codecs=opus'
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm'
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/wav'
        }
      }
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType
      })
      
      mediaRecorderRef.current = mediaRecorder
      
      // Handle data available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN && !isMutedRef.current) {
          // Convert blob to base64
          const reader = new FileReader()
          reader.onload = () => {
            const base64 = (reader.result as string).split(',')[1]
            wsRef.current?.send(JSON.stringify({
              type: 'audio_chunk',
              audio_data: base64,
              timestamp: Date.now()
            }))
          }
          reader.readAsDataURL(event.data)
        }
      }
      
      // Handle recording errors
      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event)
        setStatus("Recording error")
      }
      
      // Start recording with 100ms chunks
      mediaRecorder.start(100)
      setIsRecording(true)
      setStatus("Listening...")
      console.log('Recording started with MIME type:', mimeType)
      
    } catch (error) {
      console.error('Error starting recording:', error)
      setStatus("Error accessing microphone - Check permissions")
    }
  }, [])

  const stopRecording = useCallback(() => {
    console.log('Stopping recording, current state:', mediaRecorderRef.current?.state)
    
    if (mediaRecorderRef.current) {
      if (mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
      mediaRecorderRef.current = null
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop()
        console.log('Stopped track:', track.kind)
      })
      streamRef.current = null
    }
    
    setIsRecording(false)
    if (!isMuted) {
      setStatus("Processing...")
    }
  }, [isMuted])

  const toggleMute = useCallback(() => {
    console.log('Toggling mute, current state:', isMuted)
    setIsMuted(prev => {
      const newMutedState = !prev
      isMutedRef.current = newMutedState
      
      // Disconnect WebSocket when muting, reconnect when unmuting
      if (newMutedState) {
        console.log('Muting - disconnecting WebSocket to stop audio processing')
        if (wsRef.current) {
          wsRef.current.close()
        }
        // Clear any pending reconnection
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      } else {
        console.log('Unmuting - reconnecting WebSocket to resume audio processing')
        // Reconnect after a short delay to ensure state is updated
        setTimeout(() => {
          connectWebSocket()
        }, 100)
      }
      
      return newMutedState
    })
  }, [isMuted, connectWebSocket])

  const toggleSpeaker = useCallback(() => {
    setIsSpeakerOn(!isSpeakerOn)
    if (!isSpeakerOn) {
      // Clear audio queue when turning speaker off
      audioQueueRef.current.forEach(audio => audio.pause())
      audioQueueRef.current = []
      isPlayingRef.current = false
    }
  }, [isSpeakerOn])

  const handleEndCall = useCallback(() => {
    stopRecording()
    if (wsRef.current) {
      wsRef.current.close()
    }
    onCallEnd()
  }, [stopRecording, onCallEnd])

  // Auto-start recording when connected
  useEffect(() => {
    console.log('Auto-start check:', { isConnected, isRecording, isMuted })
    if (isConnected && !isRecording && !isMuted) {
      console.log('Auto-starting recording')
      startRecording()
    }
  }, [isConnected, isRecording, isMuted, startRecording])

  // Update recording state when mute changes
  useEffect(() => {
    console.log('Mute state changed:', { isMuted, isConnected, isRecording })
    if (isMuted) {
      console.log('Muted - stopping recording and disconnecting')
      stopRecording()
      setStatus("Muted - WebSocket disconnected")
    } else if (isConnected && !isRecording) {
      console.log('Unmuted and connected - starting recording')
      startRecording()
    }
  }, [isMuted, isConnected, isRecording, startRecording, stopRecording])

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`h-3 w-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="font-medium">{status}</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={isConnected ? "default" : "destructive"}>
                {isConnected ? "Connected" : "Disconnected"}
              </Badge>
              {!isConnected && (
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={connectWebSocket}
                >
                  Retry Connection
                </Button>
              )}
            </div>
          </div>
          
          {currentText && (
            <div className="mt-4 p-3 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">AI Response:</p>
              <p className="text-sm">{currentText}</p>
            </div>
          )}
          
          {/* Debug Information */}
          <div className="mt-4 p-2 bg-gray-100 rounded text-xs text-gray-600">
            <p>Session ID: {sessionId}</p>
            <p>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</p>
            <p>Recording: {isRecording ? 'Yes' : 'No'}</p>
            <p>Muted: {isMuted ? 'Yes' : 'No'}</p>
            <p>Speaker: {isSpeakerOn ? 'On' : 'Off'}</p>
            {isMuted && (
              <p className="text-red-600 font-semibold">🔇 Microphone is muted - WebSocket disconnected to prevent processing</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Controls */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center gap-4">
            {/* Mute Button */}
            <Button
              variant={isMuted ? "destructive" : "outline"}
              size="lg"
              onClick={toggleMute}
              className="rounded-full h-16 w-16"
              disabled={!isConnected}
            >
              {isMuted ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
            </Button>

            {/* Speaker Button */}
            <Button
              variant={!isSpeakerOn ? "destructive" : "outline"}
              size="lg"
              onClick={toggleSpeaker}
              className="rounded-full h-16 w-16"
            >
              {isSpeakerOn ? <Volume2 className="h-6 w-6" /> : <VolumeX className="h-6 w-6" />}
            </Button>

            {/* End Call Button */}
            <Button
              variant="destructive"
              size="lg"
              onClick={handleEndCall}
              className="rounded-full h-20 w-20 bg-red-500 hover:bg-red-600"
            >
              <PhoneOff className="h-8 w-8" />
            </Button>
          </div>

          {/* Control Labels */}
          <div className="flex items-center justify-center gap-4 mt-4 text-sm text-muted-foreground">
            <span className="w-16 text-center">{isMuted ? 'Unmute' : 'Mute'}</span>
            <span className="w-16 text-center">{isSpeakerOn ? 'Speaker' : 'Speaker Off'}</span>
            <span className="w-20 text-center">End Call</span>
          </div>
        </CardContent>
      </Card>

      {/* Instructions */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <h3 className="font-semibold text-blue-900 mb-2">How to use:</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Speak naturally - the system will detect when you stop talking</li>
            <li>• After 2 seconds of silence, your message will be processed</li>
            <li>• The AI will respond with both text and voice</li>
            <li>• Use the mute button to pause/resume listening (disconnects WebSocket when muted)</li>
            <li>• When muted, no audio processing occurs to save resources</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
