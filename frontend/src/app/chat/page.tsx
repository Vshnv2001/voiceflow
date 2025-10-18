"use client"

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import VoiceChat from '@/components/VoiceChat'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Loader2, MessageSquare, Mic, Users } from 'lucide-react'

interface Session {
  id: string
  user_id: string
  customer_id?: string
  status: 'active' | 'closed' | 'paused'
  created_at: string
  updated_at: string
  closed_at?: string
  metadata: Record<string, any>
}

export default function ChatPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSession, setCurrentSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      loadSessions()
    }
  }, [user])

  const loadSessions = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/sessions')
      if (response.ok) {
        const data = await response.json()
        setSessions(data)
        
        // Auto-select the first active session or create a new one
        const activeSession = data.find((s: Session) => s.status === 'active')
        if (activeSession) {
          setCurrentSession(activeSession)
        } else {
          await createNewSession()
        }
      }
    } catch (error) {
      console.error('Error loading sessions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const createNewSession = async () => {
    try {
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metadata: {
            source: 'web_chat',
            created_at: new Date().toISOString()
          }
        }),
      })

      if (response.ok) {
        const newSession = await response.json()
        setCurrentSession(newSession)
        setSessions(prev => [newSession, ...prev])
      }
    } catch (error) {
      console.error('Error creating session:', error)
    }
  }

  const closeSession = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: 'closed'
        }),
      })

      if (response.ok) {
        setSessions(prev => 
          prev.map(s => 
            s.id === sessionId 
              ? { ...s, status: 'closed' as const, closed_at: new Date().toISOString() }
              : s
          )
        )
        
        // If we closed the current session, create a new one
        if (currentSession?.id === sessionId) {
          await createNewSession()
        }
      }
    } catch (error) {
      console.error('Error closing session:', error)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="default" className="bg-green-500">Active</Badge>
      case 'closed':
        return <Badge variant="secondary">Closed</Badge>
      case 'paused':
        return <Badge variant="outline" className="border-yellow-500 text-yellow-500">Paused</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sessions Sidebar */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                Chat Sessions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={createNewSession} 
                className="w-full"
                disabled={isLoading}
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                New Session
              </Button>
              
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      currentSession?.id === session.id
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50'
                    }`}
                    onClick={() => setCurrentSession(session)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">
                        Session {session.id.slice(0, 8)}...
                      </span>
                      {getStatusBadge(session.status)}
                    </div>
                    
                    <div className="text-xs text-muted-foreground">
                      {new Date(session.created_at).toLocaleDateString()}
                    </div>
                    
                    {session.status === 'active' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full mt-2"
                        onClick={(e) => {
                          e.stopPropagation()
                          closeSession(session.id)
                        }}
                      >
                        Close Session
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Chat Area */}
        <div className="lg:col-span-3">
          {currentSession ? (
            <VoiceChat 
              sessionId={currentSession.id}
              onSessionUpdate={(session) => {
                setSessions(prev => 
                  prev.map(s => s.id === session.id ? session : s)
                )
              }}
            />
          ) : (
            <Card className="h-[600px]">
              <CardContent className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Mic className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-medium mb-2">No Active Session</h3>
                  <p className="text-muted-foreground mb-4">
                    Create a new session to start chatting
                  </p>
                  <Button onClick={createNewSession}>
                    <MessageSquare className="w-4 h-4 mr-2" />
                    Start New Chat
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
