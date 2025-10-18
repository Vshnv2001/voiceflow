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

export function useActiveSessions() {
  const { user } = useAuth()
  const [activeSessions, setActiveSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    console.log('useActiveSessions hook - user:', user)
    if (!user) {
      console.log('useActiveSessions: No user found, returning early')
      setLoading(false)
      return
    }
    
    console.log('useActiveSessions: User found, fetching active sessions for user.id:', user.id)

    // Initial fetch of active sessions
    const fetchActiveSessions = async () => {
      try {
        setLoading(true)
        console.log('Fetching active sessions from Supabase...')
        const { data, error } = await supabase
          .from('sessions')
          .select('*')
          .eq('customer_rep_id', user.id)
          .eq('status', 'active')
          .order('created_at', { ascending: false })

        if (error) {
          console.error('Supabase error:', error)
          throw error
        }

        console.log('Fetched active sessions:', data)
        console.log('Number of active sessions:', data?.length || 0)

        setActiveSessions(data || [])
        setError(null)
      } catch (err) {
        console.error('Error fetching active sessions:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch active sessions')
      } finally {
        setLoading(false)
      }
    }

    console.log('Calling fetchActiveSessions()...')
    fetchActiveSessions()

    // Set up real-time subscription
    const channel = supabase
      .channel('active-sessions-changes')
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
          
          // Only add if it's active
          if (newSession.status === 'active') {
            setActiveSessions((prev) => [newSession, ...prev])
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

          setActiveSessions((prev) => {
            // If status changed from active to something else, remove it
            if (updatedSession.status !== 'active') {
              return prev.filter((s) => s.id !== updatedSession.id)
            }
            
            // Otherwise update the session
            const index = prev.findIndex((s) => s.id === updatedSession.id)
            if (index >= 0) {
              const newSessions = [...prev]
              newSessions[index] = updatedSession
              return newSessions
            }
            
            // If not found and it's active, add it
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
          setActiveSessions((prev) => prev.filter((s) => s.id !== deletedSession.id))
        }
      )
      .subscribe()

    // Cleanup subscription on unmount
    return () => {
      supabase.removeChannel(channel)
    }
  }, [user])

  return {
    activeSessions,
    loading,
    error,
  }
}

