"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { usePendingSessions } from "@/hooks/usePendingSessions"
import { Phone, Clock, User, CheckCircle, XCircle, AlertCircle } from "lucide-react"
import { useState } from "react"
import { useRouter } from "next/navigation"

export default function PendingCalls() {
  console.log('PendingCalls component mounted')
  const router = useRouter()
  const { pendingSessions, loading, error, acceptSession, rejectSession } = usePendingSessions()
  console.log('PendingCalls - pendingSessions:', pendingSessions)
  console.log('PendingCalls - loading:', loading)
  console.log('PendingCalls - error:', error)
  const [processingId, setProcessingId] = useState<string | null>(null)

  const handleAccept = async (sessionId: string) => {
    setProcessingId(sessionId)
    const result = await acceptSession(sessionId)
    setProcessingId(null)
    
    if (result.success) {
      console.log('Session accepted successfully, navigating to conversation...')
      // Navigate to the agent conversation page
      router.push(`/agent/conversation/${sessionId}`)
    } else {
      alert(result.error || 'Failed to accept session')
    }
  }

  const handleReject = async (sessionId: string) => {
    if (!confirm('Are you sure you want to reject this call request?')) {
      return
    }
    
    setProcessingId(sessionId)
    const result = await rejectSession(sessionId)
    setProcessingId(null)
    
    if (result.success) {
      console.log('Session rejected successfully')
    } else {
      alert(result.error || 'Failed to reject session')
    }
  }

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (seconds < 60) return `${seconds}s ago`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return `${Math.floor(seconds / 86400)}d ago`
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5 animate-pulse" />
            Pending Call Requests
          </CardTitle>
          <CardDescription>Loading incoming calls...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Pending Call Requests
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-red-600">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Pending Call Requests
              {pendingSessions.length > 0 && (
                <Badge variant="destructive" className="ml-2">
                  {pendingSessions.length}
                </Badge>
              )}
            </CardTitle>
            <CardDescription>Incoming customer service requests</CardDescription>
          </div>
          {pendingSessions.length > 0 && (
            <div className="h-3 w-3 animate-pulse rounded-full bg-orange-500"></div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {pendingSessions.length === 0 ? (
          <div className="text-center py-8">
            <Phone className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-muted-foreground">No pending call requests</p>
            <p className="text-sm text-muted-foreground mt-2">
              You'll be notified when customers request a call
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {pendingSessions.map((session) => (
              <div
                key={session.id}
                className="border rounded-lg p-4 bg-orange-50/50 border-orange-200 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="h-4 w-4 text-orange-600" />
                      <span className="font-semibold text-lg">
                        {session.customer_name || 'Anonymous'}
                      </span>
                      <Badge variant="outline" className="text-orange-600 border-orange-600">
                        Pending
                      </Badge>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                      <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        <span>{getTimeAgo(session.created_at)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs bg-orange-100 px-2 py-1 rounded">
                          ID: {session.id.slice(0, 8)}...
                        </span>
                      </div>
                    </div>

                    {session.metadata && Object.keys(session.metadata).length > 0 && (
                      <div className="text-sm text-muted-foreground mb-3">
                        <span className="font-medium">Priority:</span>{' '}
                        {session.metadata.priority || 'Normal'}
                      </div>
                    )}

                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleAccept(session.id)}
                        disabled={processingId === session.id}
                        size="sm"
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle className="h-4 w-4 mr-1" />
                        {processingId === session.id ? 'Accepting...' : 'Accept Call'}
                      </Button>
                      <Button
                        onClick={() => handleReject(session.id)}
                        disabled={processingId === session.id}
                        variant="outline"
                        size="sm"
                        className="text-red-600 border-red-600 hover:bg-red-50"
                      >
                        <XCircle className="h-4 w-4 mr-1" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

