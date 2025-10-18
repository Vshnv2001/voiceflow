import { useState, useEffect } from "react"
import { supabase } from "@/lib/supabase"

interface Session {
  id: string
  customer_rep_id: string | null
  customer_name: string | null
  status: 'active' | 'pending' | 'closed' | 'paused'
  created_at: string
  updated_at: string
  closed_at: string | null
  metadata: Record<string, any>
}

export function useSessionStatus(sessionId: string | null) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) {
      console.log('useSessionStatus: No sessionId provided, skipping')
      setLoading(false)
      return
    }

    console.log('useSessionStatus: Tracking session:', sessionId)
    console.log('useSessionStatus: sessionId type:', typeof sessionId)

    const fetchSession = async () => {
      if (!sessionId) {
        setLoading(false)
        return
      }

      try {
        console.log('Fetching session status for session id:', sessionId)
        // Temp - pull all IDs for debugging
        const { data: ids, error: idsError } = await supabase
          .from('sessions')
          .select('id')

        if (idsError) {
          console.error('Error fetching session IDs:', idsError)
          throw idsError
        }
        console.log('Session IDs:', ids)

        const { data, error } = await supabase
          .from('sessions')
          .select('*')
          .eq('id', sessionId)
          .maybeSingle() // Use maybeSingle() instead of single() to handle 0 rows gracefully

        if (error) {
          console.error('Error fetching session:', error)
          throw error
        }

        if (data) {
          console.log('✅ Session found! Status:', data.status, 'ID:', data.id)
          setSession(data)
          setError(null)
        } else {
          console.warn('❌ Session not found in database. Looking for ID:', sessionId)
          console.warn('Available session IDs:', ids?.map(s => s.id))
          setError('Session not found')
        }
      } catch (err) {
        console.error('Error in fetchSession:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch session status')
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchSession()

    // Set up polling - check every 2 seconds for status changes
    const pollInterval = setInterval(() => {
      console.log('Polling: Checking session status...')
      fetchSession()
    }, 2000) // Poll every 2 seconds for faster response

    // Set up real-time subscription for instant updates
    const channel = supabase
      .channel(`session-${sessionId}-changes`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'sessions',
          filter: `id=eq.${sessionId}`
        },
        (payload) => {
          console.log('Realtime update received for session:', payload.new)
          setSession(payload.new as Session)
        }
      )
      .subscribe()

    // Cleanup
    return () => {
      clearInterval(pollInterval)
      supabase.removeChannel(channel)
    }
  }, [sessionId])

  return { session, loading, error }
}

