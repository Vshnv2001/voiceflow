"use client"

import { useState, useEffect, useRef } from "react"
import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Phone, Clock, ArrowLeft } from "lucide-react"
import Link from "next/link"
import Navigation from "@/components/Navigation"
import { useAllSessions } from "@/hooks/useAllSessions"
import { supabase } from "@/lib/supabase"

// Format database transcripts for UI display
const formatTranscripts = (transcripts: any[]) => {
  if (!transcripts || !Array.isArray(transcripts)) return []
  
  return transcripts.map((entry) => ({
    speaker: entry.speaker === 'user' ? 'customer' : 'agent',
    message: entry.text,
    time: new Date(entry.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
  }))
}

export default function TranscriptsPage() {
  const { activeSessions, loading } = useAllSessions()
  const [selectedCall, setSelectedCall] = useState<any>(null)
  const transcriptEndRef = useRef<HTMLDivElement>(null)
  const previousTranscriptLengthRef = useRef<number>(0)

  // Set first active session as selected when data loads
  useEffect(() => {
    if (activeSessions.length > 0 && !selectedCall) {
      setSelectedCall(activeSessions[0])
    }
  }, [activeSessions, selectedCall])

  // Aggressive polling for real-time transcript updates
  useEffect(() => {
    if (!selectedCall?.id) return

    console.log('🔄 Setting up aggressive polling for session:', selectedCall.id)

    // Function to fetch latest transcripts
    const fetchLatestTranscripts = async () => {
      try {
        const { data, error } = await supabase
          .from('sessions')
          .select('transcripts')
          .eq('id', selectedCall.id)
          .single()

        if (error) {
          console.error('Error fetching transcripts:', error)
          return
        }

        if (data && data.transcripts) {
          // Only update if transcripts have changed
          const currentLength = selectedCall.transcripts?.length || 0
          const newLength = data.transcripts?.length || 0
          
          if (newLength !== currentLength) {
            console.log('📨 New transcripts detected! Updating...', {
              old: currentLength,
              new: newLength
            })
            
            setSelectedCall((prev: any) => ({
              ...prev,
              transcripts: data.transcripts
            }))
          }
        }
      } catch (err) {
        console.error('Error in polling:', err)
      }
    }

    // Initial fetch
    fetchLatestTranscripts()

    // Poll every 500ms (twice per second) for near real-time updates
    const pollInterval = setInterval(() => {
      fetchLatestTranscripts()
    }, 500)

    // Also set up Supabase real-time subscription as backup
    const channel = supabase
      .channel(`transcripts-${selectedCall.id}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'sessions',
          filter: `id=eq.${selectedCall.id}`
        },
        (payload: any) => {
          console.log('🔔 Real-time update via Supabase subscription:', payload)
          
          if (payload.new && payload.new.transcripts) {
            setSelectedCall((prev: any) => ({
              ...prev,
              transcripts: payload.new.transcripts
            }))
          }
        }
      )
      .subscribe((status) => {
        console.log('📡 Supabase subscription status:', status)
      })

    return () => {
      console.log('🧹 Cleaning up polling and subscription for session:', selectedCall.id)
      clearInterval(pollInterval)
      supabase.removeChannel(channel)
    }
  }, [selectedCall?.id])

  // Smart auto-scroll: only scroll when NEW messages arrive (not on every poll)
  useEffect(() => {
    if (!selectedCall?.transcripts) return

    const currentLength = selectedCall.transcripts.length
    const previousLength = previousTranscriptLengthRef.current

    // Only scroll if there are NEW messages (length increased)
    // Skip on initial load (previousLength === 0) to prevent auto-scroll on page load
    if (currentLength > previousLength && previousLength > 0) {
      console.log('📜 New message detected, auto-scrolling to bottom')
      setTimeout(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" })
      }, 100)
    }

    // Update the reference
    previousTranscriptLengthRef.current = currentLength
  }, [selectedCall?.transcripts])

  const getTimeSince = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${String(hours).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
    return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  }


  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-green-500/10 text-green-500 border-green-500/20"
      case "negative":
        return "bg-red-500/10 text-red-500 border-red-500/20"
      default:
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="dashboard" />
      
      {/* Page Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold">Call Transcripts</h1>
              <p className="text-sm text-muted-foreground">Real-time conversation monitoring</p>
            </div>
          </div>
          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
            <Phone className="h-3 w-3 mr-1" />
            {loading ? '...' : activeSessions.length} Active Calls
          </Badge>
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Left Sidebar - Call List */}
        <aside className="w-80 border-r border-border bg-card/30">
          <div className="p-4 border-b border-border">
            <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Ongoing Calls</h2>
          </div>
          <ScrollArea className="h-[calc(100vh-145px)]">
            {loading ? (
              <div className="p-4 text-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                <p className="text-sm text-muted-foreground">Loading sessions...</p>
              </div>
            ) : activeSessions.length === 0 ? (
              <div className="p-4 text-center">
                <Phone className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="text-sm text-muted-foreground">No active calls</p>
              </div>
            ) : (
              <div className="p-2 space-y-2">
                {activeSessions.map((session) => (
                  <Card
                    key={session.id}
                    className={`p-4 cursor-pointer transition-all hover:bg-accent/50 ${
                      selectedCall?.id === session.id ? "bg-accent border-primary" : "bg-card/50"
                    }`}
                    onClick={() => setSelectedCall(session)}
                  >
                    <div className="flex items-start gap-3">
                      <Avatar className="h-10 w-10">
                        <AvatarFallback className="bg-primary/10 text-primary">
                          {(session.customer_name || 'A')
                            .split(" ")
                            .map((n) => n[0])
                            .join("")
                            .toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <p className="font-medium text-sm truncate">{session.customer_name || 'Anonymous'}</p>
                          <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                            active
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>{getTimeSince(session.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </ScrollArea>
        </aside>

        {/* Right Side - Transcript View */}
        <main className="flex-1 flex flex-col">
          {!selectedCall ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Phone className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">Select a call to view transcript</p>
              </div>
            </div>
          ) : (
            <>
              {/* Call Header */}
              <div className="p-6 border-b border-border bg-card/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Avatar className="h-12 w-12">
                      <AvatarFallback className="bg-primary/10 text-primary text-lg">
                        {(selectedCall.customer_name || 'A')
                          .split(" ")
                          .map((n: string) => n[0])
                          .join("")
                          .toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h2 className="text-xl font-semibold">{selectedCall.customer_name || 'Anonymous'}</h2>
                      <div className="flex items-center gap-3 mt-1">
                        <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                          {selectedCall.status}
                        </Badge>
                        <span className="text-sm text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {selectedCall.created_at ? getTimeSince(selectedCall.created_at) : '00:00'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                    <div className="h-2 w-2 bg-green-500 rounded-full mr-2 animate-pulse" />
                    Live
                  </Badge>
                </div>
              </div>

              {/* Transcript Messages */}
              <ScrollArea className="flex-1 p-6">
                <div className="space-y-4 max-w-4xl mx-auto">
                  {selectedCall.transcripts && selectedCall.transcripts.length > 0 ? (
                    formatTranscripts(selectedCall.transcripts).map((message: any, index: number) => (
                <div key={index} className={`flex gap-3 ${message.speaker === "agent" ? "flex-row-reverse" : ""}`}>
                  <Avatar className="h-8 w-8 flex-shrink-0">
                    <AvatarFallback
                      className={message.speaker === "agent" ? "bg-primary text-primary-foreground" : "bg-muted"}
                    >
                      {message.speaker === "agent" ? "AI" : "C"}
                    </AvatarFallback>
                  </Avatar>
                  <div className={`flex flex-col gap-1 max-w-[70%] ${message.speaker === "agent" ? "items-end" : ""}`}>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="font-medium">{message.speaker === "agent" ? "AI Agent" : "Customer"}</span>
                      <span>{message.time}</span>
                    </div>
                    <Card
                      className={`p-3 ${
                        message.speaker === "agent" ? "bg-primary text-primary-foreground" : "bg-muted"
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{message.message}</p>
                    </Card>
                  </div>
                </div>
              ))
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-muted-foreground">No transcript messages yet</p>
                      <p className="text-sm text-muted-foreground mt-2">Messages will appear here as the conversation progresses</p>
                    </div>
                  )}
                  {/* Auto-scroll anchor */}
                  <div ref={transcriptEndRef} />
                </div>
              </ScrollArea>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
