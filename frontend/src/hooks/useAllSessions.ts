import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/contexts/AuthContext'

interface TranscriptEntry {
  timestamp: string
  speaker: 'user' | 'agent'
  text: string
}

interface Session {
  id: string
  customer_rep_id: string
  customer_name: string
  status: string
  created_at: string
  updated_at: string
  closed_at: string | null
  metadata: Record<string, any>
  transcripts?: TranscriptEntry[]
}

export function useAllSessions() {
  const { user } = useAuth()
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    console.log('useAllSessions hook - user:', user)
    if (!user) {
      console.log('useAllSessions: No user found, returning early')
      setLoading(false)
      return
    }
    
    console.log('useAllSessions: User found, fetching all sessions for user.id:', user.id)

    // Initial fetch of all sessions (active, pending, closed) including transcripts
    const fetchAllSessions = async () => {
      try {
        setLoading(true)
        console.log('Fetching all sessions from Supabase with transcripts...')
        const { data, error } = await supabase
          .from('sessions')
          .select('id, customer_rep_id, customer_name, status, created_at, updated_at, closed_at, metadata, transcripts')
          .eq('customer_rep_id', user.id)
          .order('created_at', { ascending: false })

        if (error) {
          console.error('Supabase error:', error)
          throw error
        }

        console.log('Fetched all sessions:', data)
        console.log('Number of sessions:', data?.length || 0)

        setSessions(data || [])
        setError(null)
      } catch (err) {
        console.error('Error fetching all sessions:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch sessions')
      } finally {
        setLoading(false)
      }
    }

    console.log('Calling fetchAllSessions()...')
    fetchAllSessions()

    // Set up polling - refetch every 2 seconds for faster updates
    const pollInterval = setInterval(() => {
      console.log('Polling: Refetching all sessions...')
      fetchAllSessions()
    }, 2000) // Poll every 2 seconds

    // Set up real-time subscription
    const channel = supabase
      .channel('all-sessions-changes')
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
          setSessions((prev) => [newSession, ...prev])
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

          setSessions((prev) => {
            const index = prev.findIndex((s) => s.id === updatedSession.id)
            if (index >= 0) {
              const newSessions = [...prev]
              newSessions[index] = updatedSession
              return newSessions
            }
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
          setSessions((prev) => prev.filter((s) => s.id !== deletedSession.id))
        }
      )
      .subscribe()

    // Cleanup subscription and polling on unmount
    return () => {
      clearInterval(pollInterval)
      supabase.removeChannel(channel)
    }
  }, [user])

  return {
    sessions,
    activeSessions: sessions.filter(s => s.status === 'active'),
    pendingSessions: sessions.filter(s => s.status === 'pending'),
    closedSessions: sessions.filter(s => s.status === 'closed'),
    loading,
    error,
  }
}

