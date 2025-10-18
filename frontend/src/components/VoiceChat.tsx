"use client"

import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Mic, MicOff, Play, Pause, Phone, PhoneOff, MessageSquare, Clock, User } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

interface Message {
  id: string
  session_id: string
  sender_type: 'customer' | 'agent' | 'system'
  message_type: 'voice' | 'text' | 'ai_generated'
  text_content?: string
  voice_audio_url?: string
  voice_transcription?: string
  created_at: string
  status: string
}

interface Session {
  id: string
  user_id: string
  customer_id?: string
  agent_id?: string
  session_type: string
  status: 'pending' | 'active' | 'closed' | 'paused' | 'rejected'
  created_at: string
  updated_at: string
  closed_at?: string
  metadata: Record<string, any>
}

interface VoiceChatProps {
  sessionId: string
  onSessionUpdate: (session: Session) => void
}

export default function VoiceChat({ sessionId, onSessionUpdate }: VoiceChatProps) {
  const { user } = useAuth()
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [callEndReason, setCallEndReason] = useState('')
  const [callSummary, setCallSummary] = useState('')
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (sessionId) {
      loadSession()
      loadMessages()
    }
  }, [sessionId])

  const loadSession = async () => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const sessionData = await response.json()
        setSession(sessionData)
        onSessionUpdate(sessionData)
      }
    } catch (error) {
      console.error('Error loading session:', error)
    }
  }

  const loadMessages = async () => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/messages`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const messagesData = await response.json()
        setMessages(messagesData)
      }
    } catch (error) {
      console.error('Error loading messages:', error)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        setAudioBlob(audioBlob)
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error('Error starting recording:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const uploadAudio = async () => {
    if (!audioBlob) return

    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('audio_file', audioBlob, 'recording.wav')

      const response = await fetch(`/api/sessions/${sessionId}/messages/voice`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      })

      if (response.ok) {
        const message = await response.json()
        setMessages(prev => [...prev, message])
        setAudioBlob(null)
        // Refresh messages after a delay to get transcription
        setTimeout(loadMessages, 2000)
      }
    } catch (error) {
      console.error('Error uploading audio:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const endCall = async () => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/end-call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          reason: callEndReason,
          summary: callSummary
        })
      })

      if (response.ok) {
        await loadSession()
        setCallEndReason('')
        setCallSummary('')
      }
    } catch (error) {
      console.error('Error ending call:', error)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="border-yellow-500 text-yellow-500">Waiting for Agent</Badge>
      case 'active':
        return <Badge variant="default" className="bg-green-500">Active</Badge>
      case 'closed':
        return <Badge variant="secondary">Closed</Badge>
      case 'rejected':
        return <Badge variant="destructive">Rejected</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString()
  }

  if (!session) {
    return (
      <Card className="h-[600px]">
        <CardContent className="flex items-center justify-center h-full">
          <div className="text-center">
            <Clock className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Loading Session</h3>
            <p className="text-muted-foreground">Please wait...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Session Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Phone className="w-5 h-5" />
              Customer Service Call
            </CardTitle>
            {getStatusBadge(session.status)}
          </div>
          <div className="text-sm text-muted-foreground">
            Session ID: {session.id.slice(0, 8)}... | 
            Created: {new Date(session.created_at).toLocaleString()}
            {session.agent_id && (
              <span> | Agent: {session.agent_id.slice(0, 8)}...</span>
            )}
          </div>
        </CardHeader>
      </Card>

      {/* Messages */}
      <Card className="h-[400px]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Conversation
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] overflow-y-auto">
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                No messages yet. Start recording to begin the conversation.
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender_type === 'customer' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-lg ${
                      message.sender_type === 'customer'
                        ? 'bg-primary text-primary-foreground'
                        : message.sender_type === 'agent'
                        ? 'bg-blue-100 text-blue-900'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <User className="w-4 h-4" />
                      <span className="text-xs font-medium">
                        {message.sender_type === 'customer' ? 'You' : 
                         message.sender_type === 'agent' ? 'Agent' : 'System'}
                      </span>
                      <span className="text-xs opacity-70">
                        {formatTime(message.created_at)}
                      </span>
                    </div>
                    
                    {message.voice_transcription && (
                      <p className="text-sm mb-2">{message.voice_transcription}</p>
                    )}
                    
                    {message.text_content && (
                      <p className="text-sm">{message.text_content}</p>
                    )}
                    
                    {message.voice_audio_url && (
                      <audio
                        ref={audioRef}
                        controls
                        className="w-full mt-2"
                        src={message.voice_audio_url}
                      />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Audio Recording Controls */}
      {session.status === 'active' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mic className="w-5 h-5" />
              Voice Recording
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              {!isRecording ? (
                <Button onClick={startRecording} className="flex items-center gap-2">
                  <Mic className="w-4 h-4" />
                  Start Recording
                </Button>
              ) : (
                <Button onClick={stopRecording} variant="destructive" className="flex items-center gap-2">
                  <MicOff className="w-4 h-4" />
                  Stop Recording
                </Button>
              )}

              {audioBlob && (
                <Button onClick={uploadAudio} disabled={isUploading}>
                  {isUploading ? 'Uploading...' : 'Send Audio'}
                </Button>
              )}
            </div>

            {audioBlob && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Audio recorded</p>
                <audio controls src={URL.createObjectURL(audioBlob)} />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Call End Controls */}
      {session.status === 'active' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PhoneOff className="w-5 h-5" />
              End Call
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="call-reason">Reason for ending call (optional)</Label>
              <Input
                id="call-reason"
                placeholder="e.g., Issue resolved, customer hung up"
                value={callEndReason}
                onChange={(e) => setCallEndReason(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="call-summary">Call summary (optional)</Label>
              <Textarea
                id="call-summary"
                placeholder="Brief summary of the call..."
                value={callSummary}
                onChange={(e) => setCallSummary(e.target.value)}
                rows={3}
              />
            </div>
            
            <Button onClick={endCall} variant="destructive" className="w-full">
              <PhoneOff className="w-4 h-4 mr-2" />
              End Call
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Session Status Messages */}
      {session.status === 'pending' && (
        <Card>
          <CardContent className="text-center py-8">
            <Clock className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
            <h3 className="text-lg font-medium mb-2">Waiting for Agent</h3>
            <p className="text-muted-foreground">
              Your call has been initiated and is waiting for an agent to accept it.
            </p>
          </CardContent>
        </Card>
      )}

      {session.status === 'rejected' && (
        <Card>
          <CardContent className="text-center py-8">
            <PhoneOff className="w-16 h-16 mx-auto mb-4 text-red-500" />
            <h3 className="text-lg font-medium mb-2">Call Rejected</h3>
            <p className="text-muted-foreground">
              Unfortunately, no agent was available to take your call at this time.
            </p>
            {session.metadata?.rejection_reason && (
              <p className="text-sm text-muted-foreground mt-2">
                Reason: {session.metadata.rejection_reason}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
