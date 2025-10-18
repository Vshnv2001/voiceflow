"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { supabase } from "@/lib/supabase"
import { Users, Phone, Mail, Building, Clock, TrendingUp, Star } from "lucide-react"
import Navigation from "@/components/Navigation"

interface Rep {
  id: string
  user_id: string
  display_name: string
  organization: string
  email: string
  phone?: string
  avatar_url?: string
  status: string
  calls_handled: number
  avg_response_time: string
  satisfaction: number
  current_calls: number
  created_at: string
  updated_at: string
}

export default function RepsPage() {
  const [reps, setReps] = useState<Rep[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadReps()
  }, [])

  const loadReps = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const { data, error } = await supabase
        .from("reps")
        .select("*")
        .eq("status", "active")
        .order("calls_handled", { ascending: false })

      if (error) {
        console.error("Error loading reps:", error)
        setError("Failed to load representatives")
        return
      }

      setReps(data || [])
    } catch (err) {
      console.error("Error loading reps:", err)
      setError("Failed to load representatives")
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800 border-green-200"
      case "break":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "offline":
        return "bg-gray-100 text-gray-800 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getSatisfactionColor = (satisfaction: number) => {
    if (satisfaction >= 90) return "text-green-600"
    if (satisfaction >= 70) return "text-yellow-600"
    return "text-red-600"
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="home" />
        <div className="flex min-h-[calc(100vh-80px)] items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading representatives...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="home" />
      
      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight mb-4">Our Representatives</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Meet our dedicated customer service representatives who are here to help you with exceptional support.
          </p>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 rounded-md border bg-red-50 border-red-200 text-red-800 text-center">
            {error}
          </div>
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Users className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{reps.length}</p>
                  <p className="text-sm text-muted-foreground">Active Reps</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {reps.reduce((sum, rep) => sum + rep.calls_handled, 0)}
                  </p>
                  <p className="text-sm text-muted-foreground">Total Calls</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Star className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {reps.length > 0 ? Math.round(reps.reduce((sum, rep) => sum + rep.satisfaction, 0) / reps.length) : 0}%
                  </p>
                  <p className="text-sm text-muted-foreground">Avg Satisfaction</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Clock className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {reps.length > 0 ? Math.round(reps.reduce((sum, rep) => sum + parseInt(rep.avg_response_time.replace('s', '')), 0) / reps.length) : 0}s
                  </p>
                  <p className="text-sm text-muted-foreground">Avg Response</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Representatives Grid */}
        {reps.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Representatives Found</h3>
              <p className="text-muted-foreground">
                There are currently no active representatives. Check back later!
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {reps.map((rep) => (
              <Card key={rep.id} className="hover:shadow-lg transition-shadow">
                <CardHeader className="pb-4">
                  <div className="flex items-center gap-4">
                    <Avatar className="h-12 w-12">
                      <div className="h-full w-full bg-primary/10 flex items-center justify-center">
                        <span className="text-lg font-semibold text-primary">
                          {rep.display_name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    </Avatar>
                    <div className="flex-1">
                      <CardTitle className="text-lg">{rep.display_name}</CardTitle>
                      <CardDescription className="flex items-center gap-1 mt-1">
                        <Building className="h-3 w-3" />
                        {rep.organization}
                      </CardDescription>
                    </div>
                    <Badge className={getStatusColor(rep.status)}>
                      {rep.status.charAt(0).toUpperCase() + rep.status.slice(1)}
                    </Badge>
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  {/* Contact Information */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Mail className="h-4 w-4" />
                      <span>{rep.email}</span>
                    </div>
                    {rep.phone && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Phone className="h-4 w-4" />
                        <span>{rep.phone}</span>
                      </div>
                    )}
                  </div>

                  {/* Performance Metrics */}
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-primary">{rep.calls_handled}</p>
                      <p className="text-xs text-muted-foreground">Calls Handled</p>
                    </div>
                    <div className="text-center">
                      <p className={`text-2xl font-bold ${getSatisfactionColor(rep.satisfaction)}`}>
                        {rep.satisfaction}%
                      </p>
                      <p className="text-xs text-muted-foreground">Satisfaction</p>
                    </div>
                  </div>

                  <div className="text-center pt-2 border-t">
                    <p className="text-sm text-muted-foreground">
                      Avg Response: <span className="font-semibold">{rep.avg_response_time}</span>
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Call to Action */}
        <div className="mt-12 text-center">
          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="p-8">
              <h3 className="text-2xl font-bold mb-4">Ready to Get Started?</h3>
              <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
                Join our team of exceptional customer service representatives and start delivering outstanding support today.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a 
                  href="/signup" 
                  className="inline-flex items-center justify-center px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                >
                  Get Started
                </a>
                <a 
                  href="/login" 
                  className="inline-flex items-center justify-center px-6 py-3 border border-input bg-background rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  Sign In
                </a>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
