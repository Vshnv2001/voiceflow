import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'

interface Session {
  id: string
  customer_rep_id: string
  customer_name: string
  status: string
  created_at: string
  updated_at: string
  closed_at: string | null
  metadata: Record<string, any>
}

export function usePendingSessions() {
  const { user } = useAuth()
  const [pendingSessions, setPendingSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    console.log('usePendingSessions hook - user:', user)
    if (!user) {
      console.log('usePendingSessions: No user found, returning early')
      setLoading(false)
      return
    }
    
    console.log('usePendingSessions: User found, fetching pending sessions for user.id:', user.id)

    // Initial fetch of pending sessions
    const fetchPendingSessions = async () => {
      try {
        setLoading(true)
        console.log('Fetching pending sessions from Supabase...')
        const { data, error } = await supabase
          .from('sessions')
          .select('*')
          .eq('customer_rep_id', user.id)
          .eq('status', 'pending')
          .order('created_at', { ascending: false })

        if (error) {
          console.error('Supabase error:', error)
          throw error
        }

        console.log('Fetched pending sessions:', data)
        console.log('Number of pending sessions:', data?.length || 0)

        setPendingSessions(data || [])
        setError(null)
      } catch (err) {
        console.error('Error fetching pending sessions:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch pending sessions')
      } finally {
        setLoading(false)
      }
    }

    console.log('Calling fetchPendingSessions()...')
    fetchPendingSessions()

    // Set up polling - refetch every 5 seconds
    const pollInterval = setInterval(() => {
      console.log('Polling: Refetching pending sessions...')
      fetchPendingSessions()
    }, 5000) // Poll every 5 seconds

    // Set up real-time subscription
    const channel = supabase
      .channel('pending-sessions-changes')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'sessions',
          filter: `customer_rep_id=eq.${user.id}`,
        },
        (payload) => {
          console.log('New session inserted:', payload)
          const newSession = payload.new as Session
          
          // Only add if it's pending
          if (newSession.status === 'pending') {
            setPendingSessions((prev) => [newSession, ...prev])
          }
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'sessions',
          filter: `customer_rep_id=eq.${user.id}`,
        },
        (payload) => {
          console.log('Session updated:', payload)
          const updatedSession = payload.new as Session

          setPendingSessions((prev) => {
            // If status changed from pending to something else, remove it
            if (updatedSession.status !== 'pending') {
              return prev.filter((s) => s.id !== updatedSession.id)
            }
            
            // Otherwise update the session
            const index = prev.findIndex((s) => s.id === updatedSession.id)
            if (index >= 0) {
              const newSessions = [...prev]
              newSessions[index] = updatedSession
              return newSessions
            }
            
            // If not found and it's pending, add it
            return [updatedSession, ...prev]
          })
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'sessions',
          filter: `customer_rep_id=eq.${user.id}`,
        },
        (payload) => {
          console.log('Session deleted:', payload)
          const deletedSession = payload.old as Session
          setPendingSessions((prev) => prev.filter((s) => s.id !== deletedSession.id))
        }
      )
      .subscribe()

    // Cleanup subscription and polling on unmount
    return () => {
      clearInterval(pollInterval)
      supabase.removeChannel(channel)
    }
  }, [user])

  const acceptSession = async (sessionId: string) => {
    try {
      const { error } = await supabase
        .from('sessions')
        .update({ status: 'active' })
        .eq('id', sessionId)
        .eq('customer_rep_id', user?.id)

      if (error) throw error

      // Remove from pending list (realtime will handle this too, but this is immediate)
      setPendingSessions((prev) => prev.filter((s) => s.id !== sessionId))
      
      return { success: true, sessionId }
    } catch (err) {
      console.error('Error accepting session:', err)
      return { 
        success: false, 
        error: err instanceof Error ? err.message : 'Failed to accept session' 
      }
    }
  }

  const rejectSession = async (sessionId: string) => {
    try {
      const { error } = await supabase
        .from('sessions')
        .update({ status: 'closed' })
        .eq('id', sessionId)
        .eq('customer_rep_id', user?.id)

      if (error) throw error

      // Remove from pending list
      setPendingSessions((prev) => prev.filter((s) => s.id !== sessionId))
      
      return { success: true }
    } catch (err) {
      console.error('Error rejecting session:', err)
      return { 
        success: false, 
        error: err instanceof Error ? err.message : 'Failed to reject session' 
      }
    }
  }

  return {
    pendingSessions,
    loading,
    error,
    acceptSession,
    rejectSession,
    refresh: () => {
      // Trigger a refetch by setting loading and fetching again
      setLoading(true)
    }
  }
}

