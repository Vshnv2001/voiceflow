"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  Phone, PhoneOff, Mic, MicOff, Volume2, VolumeX, 
  User, Clock, ArrowLeft, Send, MessageCircle,
  MoreVertical, AlertCircle, CheckCircle, Loader2
} from "lucide-react"
import Navigation from "@/components/Navigation"
import { useSessionStatus } from "@/hooks/useSessionStatus"
import { useAuth } from "@/contexts/AuthContext"
import { supabase } from "@/lib/supabase"

interface Message {
  id: string
  speaker: 'customer' | 'agent' | 'system'
  content: string
  timestamp: Date
  type?: 'text' | 'system'
}

export default function AgentConversationPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const sessionId = params.sessionId as string
  
  const { session, loading: sessionLoading } = useSessionStatus(sessionId)
  const [loading, setLoading] = useState(true)
  
  // Call controls
  const [isMuted, setIsMuted] = useState(false)
  const [isSpeakerOn, setIsSpeakerOn] = useState(true)
  const [callDuration, setCallDuration] = useState(0)
  
  // Chat
  const [message, setMessage] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const previousMessageCountRef = useRef<number>(0)
  const agentWsRef = useRef<WebSocket | null>(null)
  const [isSending, setIsSending] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Load transcripts from database and set up aggressive real-time polling
  useEffect(() => {
    if (!sessionId) {
      setLoading(false)
      return
    }

    const loadTranscripts = async () => {
      try {
        const { data, error } = await supabase
          .from('sessions')
          .select('transcripts, customer_name, created_at')
          .eq('id', sessionId)
          .single()

        if (error) {
          console.error('Error loading transcripts:', error)
          setLoading(false)
          return
        }

        // Convert database transcripts to message format
        const formattedMessages: Message[] = [
          {
            id: 'system-1',
          speaker: 'system',
            content: `Call started with ${data.customer_name || 'Customer'}`,
            timestamp: new Date(data.created_at),
          type: 'system'
          }
        ]

        if (data.transcripts && Array.isArray(data.transcripts)) {
          data.transcripts.forEach((entry: any, index: number) => {
            formattedMessages.push({
              id: `transcript-${index}`,
              speaker: entry.speaker === 'user' ? 'customer' : 'agent',
              content: entry.text,
              timestamp: new Date(entry.timestamp),
          type: 'text'
            })
          })
        }

        setMessages(formattedMessages)
        setLoading(false)
      } catch (err) {
        console.error('Failed to load transcripts:', err)
        setLoading(false)
      }
    }

    // Initial load
    loadTranscripts()

    // Aggressive polling every 500ms for real-time updates
    console.log('🔄 Starting aggressive polling for agent conversation')
    const pollInterval = setInterval(() => {
      loadTranscripts()
    }, 500)

    // Set up real-time subscription as backup
    const channel = supabase
      .channel(`session-${sessionId}-transcripts`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'sessions',
          filter: `id=eq.${sessionId}`
        },
        (payload: any) => {
          console.log('🔔 Real-time update received, reloading transcripts')
          loadTranscripts()
        }
      )
      .subscribe()

    return () => {
      console.log('🧹 Cleaning up polling and subscription')
      clearInterval(pollInterval)
      supabase.removeChannel(channel)
    }
  }, [sessionId])

  // Connect to agent WebSocket to receive AI suggestions
  useEffect(() => {
    if (!sessionId) return
    
    // Only connect if session is active
    if (session?.status !== 'active') {
      console.log('⏸️ Session not active yet, waiting to connect agent WebSocket...')
      return
    }

    console.log('🔌 Connecting to agent WebSocket for session:', sessionId)
    
    let reconnectTimeout: NodeJS.Timeout
    let shouldReconnect = true

    const connectAgentWebSocket = () => {
      try {
        const ws = new WebSocket(`ws://localhost:8000/ws/agent/${sessionId}`)
        agentWsRef.current = ws

        ws.onopen = () => {
          console.log('✅ Agent WebSocket connected')
          
          // Send ping every 30 seconds to keep connection alive
          const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping' }))
            }
          }, 30000)

          // Store interval to clear later
          ;(ws as any).pingInterval = pingInterval
        }

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            console.log('📨 Received from backend:', message)

            if (message.type === 'suggested_response') {
              // Populate the input box with the suggested response
              console.log('💡 AI Suggestion:', message.text)
              setMessage(message.text)
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }

        ws.onerror = (error) => {
          console.warn('⚠️ Agent WebSocket connection error (this is normal if customer hasn\'t started talking yet)')
        }

        ws.onclose = (event) => {
          console.log('🔌 Agent WebSocket closed:', event.code, event.reason)
          
          // Clear ping interval
          if ((ws as any).pingInterval) {
            clearInterval((ws as any).pingInterval)
          }
          
          // Attempt to reconnect after 3 seconds if still needed
          if (shouldReconnect && session?.status === 'active') {
            console.log('🔄 Reconnecting agent WebSocket in 3 seconds...')
            reconnectTimeout = setTimeout(() => {
              connectAgentWebSocket()
            }, 3000)
          }
        }
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        
        // Retry connection after 3 seconds
        if (shouldReconnect && session?.status === 'active') {
          reconnectTimeout = setTimeout(() => {
            connectAgentWebSocket()
          }, 3000)
        }
      }
    }

    connectAgentWebSocket()

    return () => {
      shouldReconnect = false
      
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      
      if (agentWsRef.current) {
        console.log('🧹 Closing agent WebSocket')
        // Clear ping interval
        if ((agentWsRef.current as any).pingInterval) {
          clearInterval((agentWsRef.current as any).pingInterval)
        }
        agentWsRef.current.close()
      }
    }
  }, [sessionId, session?.status])

  // Smart auto-scroll: only scroll when NEW messages arrive (not on every re-render)
  useEffect(() => {
    const currentCount = messages.length
    const previousCount = previousMessageCountRef.current

    // Only scroll if there are NEW messages (count increased)
    // Skip on initial load (previousCount === 0) to prevent auto-scroll on page load
    if (currentCount > previousCount && previousCount > 0) {
      console.log('📜 New message detected, auto-scrolling to bottom')
      setTimeout(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
      }, 100)
    }

    // Update the reference
    previousMessageCountRef.current = currentCount
  }, [messages])

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

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    })
  }

  const handleEndCall = () => {
    // TODO: Implement call ending logic
    console.log('Ending call...')
    if (confirm('Are you sure you want to end this call?')) {
      router.push('/agent')
    }
  }

  const toggleMute = () => {
    setIsMuted(!isMuted)
    // TODO: Implement actual mute logic
  }

  const toggleSpeaker = () => {
    setIsSpeakerOn(!isSpeakerOn)
    // TODO: Implement actual speaker logic
  }

  const handleSendMessage = async () => {
    if (!message.trim() || isSending) return

    console.log('📤 Sending approved response:', message)
    setIsSending(true)

    try {
      // Call backend API to approve and send response
      const response = await fetch(`http://localhost:8000/api/agent/send-response/${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: message
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to send response')
      }

      console.log('✅ Response sent successfully!')

      // Clear the input
      setMessage("")

      // Message is now in chat history (saved when Send clicked)
      // The polling will pick it up automatically

    } catch (error) {
      console.error('❌ Error sending response:', error)
      alert(`Failed to send response: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Auto-resize textarea as content grows
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto'
      // Set height to scrollHeight (content height)
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [message])

  if (sessionLoading || loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="dashboard" />
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
        <Navigation variant="dashboard" />
        <div className="mx-auto max-w-4xl px-6 py-8">
          <div className="text-center">
            <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4 opacity-50" />
            <h1 className="text-2xl font-bold mb-2">Session Not Found</h1>
            <p className="text-muted-foreground mb-6">
              The conversation session you're looking for doesn't exist.
            </p>
            <Button onClick={() => router.push('/agent')} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="dashboard" />
      
      <div className="mx-auto max-w-7xl px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button 
              onClick={() => router.push('/agent')} 
              variant="ghost" 
              size="sm"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            
            <div className="flex items-center gap-3">
              <Avatar className="h-10 w-10">
                <div className="h-full w-full bg-primary/10 flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">
                    {session.customer_name?.charAt(0).toUpperCase() || 'C'}
                  </span>
                </div>
              </Avatar>
              <div>
                <h2 className="font-semibold">{session.customer_name || 'Customer'}</h2>
                <p className="text-sm text-muted-foreground">Session: {session.id.slice(0, 8)}...</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
              <Clock className="h-4 w-4 text-primary" />
              <span className="font-mono font-semibold">{formatDuration(callDuration)}</span>
            </div>
            
            <Badge variant="outline" className="bg-green-100 text-green-800 border-green-200">
              <div className="h-2 w-2 rounded-full bg-green-600 animate-pulse mr-2"></div>
              Active Call
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Chat Area */}
          <div className="lg:col-span-2">
            <Card className="h-[calc(100vh-240px)] flex flex-col">
              <CardHeader className="border-b">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <MessageCircle className="h-5 w-5" />
                    Conversation Transcript
                  </CardTitle>
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              
              <CardContent className="flex-1 overflow-hidden p-0">
                <ScrollArea className="h-full px-6 py-4">
                  <div className="space-y-4">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex ${
                          msg.type === 'system' 
                            ? 'justify-center' 
                            : msg.speaker === 'agent' 
                            ? 'justify-end' 
                            : 'justify-start'
                        }`}
                      >
                        {msg.type === 'system' ? (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
                            <CheckCircle className="h-3 w-3" />
                            {msg.content}
                          </div>
                        ) : (
                          <div className={`flex gap-3 max-w-[70%] ${msg.speaker === 'agent' ? 'flex-row-reverse' : ''}`}>
                            <Avatar className="h-8 w-8 mt-1">
                              <div className={`h-full w-full ${
                                msg.speaker === 'agent' ? 'bg-primary/10' : 'bg-blue-100'
                              } flex items-center justify-center`}>
                                <span className={`text-xs font-bold ${
                                  msg.speaker === 'agent' ? 'text-primary' : 'text-blue-600'
                                }`}>
                                  {msg.speaker === 'agent' ? 'A' : session.customer_name?.charAt(0).toUpperCase() || 'C'}
                                </span>
                              </div>
                            </Avatar>
                            
                            <div className={`flex flex-col ${msg.speaker === 'agent' ? 'items-end' : 'items-start'}`}>
                              <div className={`rounded-2xl px-4 py-2 ${
                                msg.speaker === 'agent'
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-muted'
                              }`}>
                                <p className="text-sm">{msg.content}</p>
                              </div>
                              <span className="text-xs text-muted-foreground mt-1">
                                {formatTime(msg.timestamp)}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>
              </CardContent>

              {/* Message Input */}
              <div className="border-t p-4">
                <div className="flex gap-2 items-end">
                  <textarea
                    ref={textareaRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="AI suggestions will appear here..."
                    className="flex-1 min-h-[40px] max-h-[200px] px-3 py-2 text-sm border border-input rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    rows={1}
                  />
                  <Button 
                    onClick={handleSendMessage} 
                    size="icon"
                    disabled={isSending || !message.trim()}
                  >
                    {isSending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                    <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  AI will suggest responses - Review and click Send to play audio to customer
                </p>
              </div>
            </Card>
          </div>

          {/* Sidebar - Call Controls & Info */}
          <div className="space-y-6">
            {/* Call Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Call Controls</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant={isMuted ? "destructive" : "outline"}
                  onClick={toggleMute}
                  className="w-full justify-start"
                >
                  {isMuted ? <MicOff className="h-4 w-4 mr-2" /> : <Mic className="h-4 w-4 mr-2" />}
                  {isMuted ? 'Unmute' : 'Mute'}
                </Button>

                <Button
                  variant={!isSpeakerOn ? "destructive" : "outline"}
                  onClick={toggleSpeaker}
                  className="w-full justify-start"
                >
                  {isSpeakerOn ? <Volume2 className="h-4 w-4 mr-2" /> : <VolumeX className="h-4 w-4 mr-2" />}
                  {isSpeakerOn ? 'Speaker On' : 'Speaker Off'}
                </Button>

                <Button
                  variant="destructive"
                  onClick={handleEndCall}
                  className="w-full justify-start"
                >
                  <PhoneOff className="h-4 w-4 mr-2" />
                  End Call
                </Button>
              </CardContent>
            </Card>

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
                  <p className="text-sm text-muted-foreground mb-1">Customer</p>
                  <p className="font-semibold">{session.customer_name || 'Anonymous'}</p>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Status</p>
                  <Badge className="bg-green-100 text-green-800 border-green-200">
                    {session.status}
                  </Badge>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Call Duration</p>
                  <p className="font-mono text-lg font-semibold">{formatDuration(callDuration)}</p>
                </div>
                
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Started At</p>
                  <p className="text-sm">
                    {new Date(session.created_at).toLocaleString()}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

