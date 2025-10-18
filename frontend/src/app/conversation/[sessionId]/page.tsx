"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { 
  Phone, PhoneOff, Mic, MicOff, Volume2, VolumeX, 
  User, Clock, ArrowLeft, Settings, MessageCircle,
  Video, VideoOff, MoreVertical, Loader2
} from "lucide-react"
import Navigation from "@/components/Navigation"
import { useSessionStatus } from "@/hooks/useSessionStatus"
import { supabase } from "@/lib/supabase"

interface Rep {
  id: string
  display_name: string
  organization: string
  avatar_url?: string
  status: string
}

// Add after imports, before the interface
const ELEVENLABS_AGENT_ID = 'agent_4901k7vt2tdffjw9qrkhk4by8ecp' // Replace with your agent ID

export default function ConversationPage() {
  const params = useParams()
  const router = useRouter()
  const sessionId = params.sessionId as string
  
  const { session, loading: sessionLoading } = useSessionStatus(sessionId)
  const [rep, setRep] = useState<Rep | null>(null)
  const [loading, setLoading] = useState(true)
  
  // Call controls
  const [isMuted, setIsMuted] = useState(false)
  const [isSpeakerOn, setIsSpeakerOn] = useState(true)
  const [isVideoOn, setIsVideoOn] = useState(false)
  const [callDuration, setCallDuration] = useState(0)
  
  // WebSocket and audio
  const [isConnected, setIsConnected] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [statusMessage, setStatusMessage] = useState("")
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const isPlayingAudioRef = useRef(false)
  const audioQueueRef = useRef<string[]>([])

  useEffect(() => {
    if (session && session.customer_rep_id) {
      loadRep(session.customer_rep_id)
    }
  }, [session?.customer_rep_id])

  // Call duration timer
  useEffect(() => {
    if (session?.status === 'active') {
      const startTime = new Date(session.created_at).getTime()
      
      const interval = setInterval(() => {
        const now = new Date().getTime()
        const duration = Math.floor((now - startTime) / 1000)
        setCallDuration(duration)
      }, 1000)

      return () => clearInterval(interval)
    }
  }, [session?.status, session?.created_at])

  const loadRep = async (repId: string) => {
    if (rep && rep.id === repId) {
      return
    }
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from("reps")
        .select("id, display_name, organization, avatar_url, status")
        .eq("user_id", repId)
        .single()

      if (error) {
        console.error("Error loading rep:", error)
        return
      }

      setRep(data)
    } catch (err) {
      console.error("Error loading rep:", err)
    } finally {
      setLoading(false)
    }
  }

  // Connect to ElevenLabs WebSocket directly
  const connectWebSocket = async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })
      
      streamRef.current = stream
      setStatusMessage("Microphone access granted")
      
      // Connect to FastAPI backend proxy (which forwards to ElevenLabs)
      const wsUrl = `ws://localhost:8000/ws/conversation/${sessionId}`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws
      
      ws.onopen = () => {
        console.log("Connected to FastAPI backend (proxying to ElevenLabs)")
        setIsConnected(true)
        setStatusMessage("Connected to AI Agent")
        
        // Send conversation initiation (without prompt override since agent doesn't allow it)
        const initMessage = {
          type: "conversation_initiation_client_data",
          conversation_config_override: {
            agent: {
              language: "en"
            }
          }
        }
        
        ws.send(JSON.stringify(initMessage))
        console.log("Sent conversation initiation")
        setStatusMessage("Ready - Speak now!")
      }
      
      ws.onmessage = async (event) => {
        try {
          // ElevenLabs sends JSON messages
          const message = JSON.parse(event.data)
          const messageType = message.type || ''
          
          console.log("ElevenLabs message:", messageType, message)
          
          switch (messageType) {
            case 'conversation_initiation_metadata':
              console.log("Conversation initialized:", message)
              setStatusMessage("Ready - Start speaking!")
              startAudioCapture(stream, ws)
              break
              
            case 'audio':
              // Handle audio response from ElevenLabs
              const audioEvent = message.audio_event
              if (audioEvent && audioEvent.audio_base_64) {
                console.log("Received audio chunk from ElevenLabs")
                
                // Add to queue
                audioQueueRef.current.push(audioEvent.audio_base_64)
                
                // Process queue if not already playing
                if (!isPlayingAudioRef.current) {
                  processAudioQueue()
                }
              }
              break
              
            case 'user_transcript':
              // Handle user transcript
              const userTranscript = message.user_transcription_event?.user_transcript
              if (userTranscript) {
                console.log("User said:", userTranscript)
                setStatusMessage(`You: ${userTranscript}`)
              }
              break
              
            case 'agent_response':
              // Handle agent text response
              const agentResponse = message.agent_response_event?.agent_response
              if (agentResponse) {
                console.log("Agent response:", agentResponse)
                setIsProcessing(true)
              }
              break
              
            case 'ping':
              // Respond to ping with pong
              const pingEvent = message.ping_event
              if (pingEvent) {
                ws.send(JSON.stringify({
                  type: 'pong',
                  event_id: pingEvent.event_id
                }))
              }
              break
              
            default:
              console.log("Unhandled message type:", messageType)
          }
          
        } catch (error) {
          console.error("Error handling ElevenLabs message:", error)
        }
      }
      
      ws.onerror = (error) => {
        console.error("Backend WebSocket error:", error)
        setStatusMessage("Connection error")
        setIsConnected(false)
      }
      
      ws.onclose = (event) => {
        console.log("Backend WebSocket closed:", event.code, event.reason)
        setIsConnected(false)
        setStatusMessage("Disconnected")
        stopAudioCapture()
      }
      
    } catch (error) {
      console.error("Error connecting to backend:", error)
      setStatusMessage(`Error: ${error instanceof Error ? error.message : 'Failed to connect'}`)
    }
  }
  
  // Start capturing audio from microphone and send to ElevenLabs
  const startAudioCapture = (stream: MediaStream, ws: WebSocket) => {
    const audioContext = new AudioContext({ sampleRate: 16000 })
    audioContextRef.current = audioContext
    
    const source = audioContext.createMediaStreamSource(stream)
    const processor = audioContext.createScriptProcessor(4096, 1, 1)
    processorRef.current = processor
    
    source.connect(processor)
    processor.connect(audioContext.destination)
    
    processor.onaudioprocess = (e) => {
      if (ws.readyState === WebSocket.OPEN && !isMuted) {
        const inputData = e.inputBuffer.getChannelData(0)
        
        // Convert float32 to int16 PCM
        const int16Data = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]))
          int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }
        
        // Convert to base64 for ElevenLabs
        const base64Audio = btoa(
          String.fromCharCode(...new Uint8Array(int16Data.buffer))
        )
        
        // Send to ElevenLabs in the correct format
        ws.send(JSON.stringify({
          user_audio_chunk: base64Audio
        }))
      }
    }
  }
  
  // Stop audio capture
  const stopAudioCapture = () => {
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
  }
  
  // Process audio queue sequentially
  const processAudioQueue = async () => {
    if (isPlayingAudioRef.current || audioQueueRef.current.length === 0) {
      return
    }
    
    isPlayingAudioRef.current = true
    setStatusMessage("Playing response...")
    setIsProcessing(true)
    
    while (audioQueueRef.current.length > 0) {
      const audioChunk = audioQueueRef.current.shift()
      if (audioChunk) {
        await playBase64Audio(audioChunk)
      }
    }
    
    isPlayingAudioRef.current = false
    setIsProcessing(false)
    setStatusMessage("Ready - Speak again!")
  }

  // Play base64 encoded audio from ElevenLabs
  const playBase64Audio = async (base64Audio: string) => {
    try {
      // Decode base64 to binary string
      const binaryString = atob(base64Audio)
      
      // Convert binary string to Int16Array (PCM data)
      const len = binaryString.length
      const bytes = new Uint8Array(len)
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      
      // Create Int16Array from the bytes
      const pcmData = new Int16Array(bytes.buffer)
      
      // Create audio context
      const audioContext = new AudioContext({ sampleRate: 16000 })
      
      // Create audio buffer
      const audioBuffer = audioContext.createBuffer(1, pcmData.length, 16000)
      const channelData = audioBuffer.getChannelData(0)
      
      // Convert Int16 PCM to Float32 for Web Audio API
      for (let i = 0; i < pcmData.length; i++) {
        channelData[i] = pcmData[i] / 32768.0
      }
      
      // Play the audio
      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.destination)
      
      return new Promise<void>((resolve) => {
        source.onended = () => {
          audioContext.close()
          resolve()
        }
        source.start(0)
      })
    } catch (error) {
      console.error("Error playing audio:", error)
    }
  }
  
  // Disconnect WebSocket
  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    stopAudioCapture()
    
    // Clear audio queue
    audioQueueRef.current = []
    isPlayingAudioRef.current = false
    
    setIsConnected(false)
    setStatusMessage("")
  }
  
  // Connect once when session becomes active
  useEffect(() => {
    if (session?.status === 'active' && !isConnected && !wsRef.current) {
      console.log('Session is active, connecting to WebSocket...')
      connectWebSocket()
    }
    // Don't disconnect on unmount - only disconnect via End Call button
  }, [session?.status])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleEndCall = () => {
    disconnectWebSocket()
    console.log('Ending call...')
    router.push('/reps')
  }

  const toggleMute = () => {
    setIsMuted(!isMuted)
    setStatusMessage(isMuted ? "Microphone unmuted" : "Microphone muted")
  }

  const toggleSpeaker = () => {
    setIsSpeakerOn(!isSpeakerOn)
  }

  const toggleVideo = () => {
    setIsVideoOn(!isVideoOn)
  }

  if (sessionLoading || loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="home" />
        <div className="flex min-h-[calc(100vh-80px)] items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading conversation...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="home" />
        <div className="mx-auto max-w-4xl px-6 py-8">
          <div className="text-center">
            <Phone className="h-16 w-16 text-red-500 mx-auto mb-4 opacity-50" />
            <h1 className="text-2xl font-bold mb-2">Session Not Found</h1>
            <p className="text-muted-foreground mb-6">
              The conversation session you're looking for doesn't exist.
            </p>
            <Button onClick={() => router.push('/reps')} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Representatives
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-primary/10">
      <Navigation variant="home" />
      
      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Header with back button */}
        <div className="flex items-center justify-between mb-6">
          <Button 
            onClick={() => router.push('/reps')} 
            variant="ghost" 
            size="sm"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          
          <Badge variant="outline" className="bg-green-100 text-green-800 border-green-200">
            <div className="h-2 w-2 rounded-full bg-green-600 animate-pulse mr-2"></div>
            Active Call
          </Badge>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Call Interface */}
          <div className="lg:col-span-2">
            <Card className="border-2 shadow-lg">
              <CardContent className="p-8">
                {/* Video/Avatar Area */}
                <div className="bg-gradient-to-br from-primary/20 to-primary/5 rounded-2xl aspect-video mb-8 flex flex-col items-center justify-center relative overflow-hidden">
                  {/* Decorative background pattern */}
                  <div className="absolute inset-0 opacity-10">
                    <div className="absolute top-0 left-0 w-full h-full" 
                         style={{
                           backgroundImage: `radial-gradient(circle at 25px 25px, currentColor 2%, transparent 0%), 
                                           radial-gradient(circle at 75px 75px, currentColor 2%, transparent 0%)`,
                           backgroundSize: '100px 100px'
                         }}>
                    </div>
                  </div>
                  
                  {/* Rep Avatar and Info */}
                  <div className="relative z-10 text-center">
                    <Avatar className="h-32 w-32 mx-auto mb-4 border-4 border-background shadow-xl">
                      <div className="h-full w-full bg-primary/20 flex items-center justify-center">
                        <span className="text-5xl font-bold text-primary">
                          {rep?.display_name?.charAt(0).toUpperCase() || session.customer_name?.charAt(0).toUpperCase() || 'R'}
                        </span>
                      </div>
                    </Avatar>
                    
                    <h2 className="text-3xl font-bold mb-2">
                      {rep?.display_name || 'Customer Representative'}
                    </h2>
                    
                    {rep?.organization && (
                      <p className="text-muted-foreground text-lg mb-4">
                        {rep.organization}
                      </p>
                    )}
                    
                    {/* Call Duration */}
                    <div className="inline-flex items-center gap-2 bg-background/80 backdrop-blur-sm px-4 py-2 rounded-full">
                      <Clock className="h-4 w-4 text-primary" />
                      <span className="font-mono text-lg font-semibold">
                        {formatDuration(callDuration)}
                      </span>
                    </div>
                  </div>

                  {/* Status indicators */}
                  {isVideoOn && (
                    <Badge className="absolute top-4 right-4 bg-green-500">
                      <Video className="h-3 w-3 mr-1" />
                      Video On
                    </Badge>
                  )}
                  
                  {/* WebSocket Status */}
                  {statusMessage && (
                    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 w-full px-4">
                      <div className="bg-background/90 backdrop-blur-sm border rounded-lg px-4 py-2 text-sm font-medium text-center shadow-lg">
                        {isProcessing && <Loader2 className="h-4 w-4 animate-spin inline mr-2" />}
                        {statusMessage}
                      </div>
                    </div>
                  )}
                </div>

                {/* Call Controls */}
                <div className="flex items-center justify-center gap-4">
                  {/* Mute Button */}
                  <Button
                    variant={isMuted ? "destructive" : "outline"}
                    size="lg"
                    onClick={toggleMute}
                    className="rounded-full h-16 w-16"
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

                  {/* Video Button */}
                  <Button
                    variant={isVideoOn ? "default" : "outline"}
                    size="lg"
                    onClick={toggleVideo}
                    className="rounded-full h-16 w-16"
                  >
                    {isVideoOn ? <Video className="h-6 w-6" /> : <VideoOff className="h-6 w-6" />}
                  </Button>

                  {/* More Options */}
                  <Button
                    variant="outline"
                    size="lg"
                    className="rounded-full h-16 w-16"
                  >
                    <MoreVertical className="h-6 w-6" />
                  </Button>
                </div>

                {/* Control Labels */}
                <div className="flex items-center justify-center gap-4 mt-4 text-sm text-muted-foreground">
                  <span className="w-16 text-center">{isMuted ? 'Unmute' : 'Mute'}</span>
                  <span className="w-16 text-center">{isSpeakerOn ? 'Speaker' : 'Speaker Off'}</span>
                  <span className="w-20 text-center">End Call</span>
                  <span className="w-16 text-center">{isVideoOn ? 'Video On' : 'Video'}</span>
                  <span className="w-16 text-center">More</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar with Session Info and Notes */}
          <div className="space-y-6">
            {/* Session Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Session Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Customer Name</p>
                  <p className="font-semibold">{session.customer_name || 'Anonymous'}</p>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Session ID</p>
                  <p className="font-mono text-xs bg-muted px-2 py-1 rounded">
                    {session.id}
                  </p>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Status</p>
                  <Badge className="bg-green-100 text-green-800 border-green-200">
                    {session.status}
                  </Badge>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Audio Connection</p>
                  <div className="flex items-center gap-2">
                    <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
                    <span className="text-sm font-medium">
                      {isConnected ? 'Connected' : 'Not Connected'}
                    </span>
                  </div>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Started At</p>
                  <p className="text-sm">
                    {new Date(session.created_at).toLocaleString()}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start" disabled>
                  <MessageCircle className="h-4 w-4 mr-2" />
                  Send Message
                  <Badge variant="outline" className="ml-auto text-xs">Coming Soon</Badge>
                </Button>
                
                <Button variant="outline" className="w-full justify-start" disabled>
                  <Video className="h-4 w-4 mr-2" />
                  Start Screen Share
                  <Badge variant="outline" className="ml-auto text-xs">Coming Soon</Badge>
                </Button>
              </CardContent>
            </Card>

            {/* Call Quality */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Connection Quality</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Audio</span>
                    <Badge className="bg-green-100 text-green-800">Excellent</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Latency</span>
                    <span className="text-sm font-mono">45ms</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Packet Loss</span>
                    <span className="text-sm font-mono">0.2%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Status Message for Customer */}
        <Card className="mt-6 bg-blue-50 border-blue-200">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-blue-500 rounded-full">
                <Phone className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-blue-900 mb-1">
                  You're now connected with {rep?.display_name || 'a representative'}
                </h3>
                <p className="text-blue-800 text-sm">
                  Feel free to speak naturally. The conversation is being recorded for quality assurance purposes.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

