"use client"

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Phone, Clock, User, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { getAgentSessions } from '@/lib/api'
import PendingCalls from '@/components/PendingCalls'

interface AgentSession {
  id: string
  user_id: string
  customer_id?: string
  agent_id?: string
  session_type: string
  status: string
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export default function AgentDashboard() {
  const { user } = useAuth()
  const [agentSessions, setAgentSessions] = useState<AgentSession[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    loadAgentSessions()
    
    // Refresh every 10 seconds
    const interval = setInterval(() => {
      loadAgentSessions()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const loadAgentSessions = async () => {
    try {
      const response = await getAgentSessions()
      if (response.data && Array.isArray(response.data)) {
        setAgentSessions(response.data as AgentSession[])
      } else {
        console.error('Error loading agent sessions:', response.error)
      }
    } catch (error) {
      console.error('Error loading agent sessions:', error)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="default" className="bg-green-500">Active</Badge>
      case 'closed':
        return <Badge variant="secondary">Closed</Badge>
      case 'pending':
        return <Badge variant="outline" className="border-yellow-500 text-yellow-500">Pending</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agent Dashboard</h1>
          <p className="text-muted-foreground">Manage customer service calls and sessions</p>
        </div>
        <div className="flex items-center gap-2">
          <User className="w-5 h-5" />
          <span className="font-medium">{user?.user_metadata?.full_name || user?.email}</span>
        </div>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700">
          <CheckCircle className="w-5 h-5" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Calls with Real-time Updates */}
        <PendingCalls />

        {/* Active Sessions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="w-5 h-5" />
              My Sessions ({agentSessions.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {agentSessions.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Phone className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>No active sessions</p>
              </div>
            ) : (
              agentSessions.map((session) => (
                <div key={session.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4" />
                      <span className="font-medium">
                        Session {session.id.slice(0, 8)}...
                      </span>
                    </div>
                    {getStatusBadge(session.status)}
                  </div>
                  
                  <div className="text-sm text-muted-foreground">
                    Customer: {session.customer_id || session.metadata?.customer_name || session.user_id.slice(0, 8) + '...'}
                  </div>
                  
                  <div className="text-xs text-muted-foreground">
                    <Clock className="w-3 h-3 inline mr-1" />
                    Started: {formatTime(session.created_at)}
                  </div>
                  
                  {session.status === 'active' && (
                    <Button
                      onClick={() => window.open(`/chat?session=${session.id}`, '_blank')}
                      size="sm"
                      className="w-full"
                    >
                      <Phone className="w-4 h-4 mr-1" />
                      Open Session
                    </Button>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
