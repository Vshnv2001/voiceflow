"use client"

import React, { useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import AgentDashboard from '@/components/AgentDashboard'
import { Loader2 } from 'lucide-react'

export default function AgentPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    )
  }

  if (!user || (user.role !== 'agent' && user.role !== 'admin')) {
    return null
  }

  return (
    <div className="container mx-auto p-6">
      <AgentDashboard />
    </div>
  )
}
