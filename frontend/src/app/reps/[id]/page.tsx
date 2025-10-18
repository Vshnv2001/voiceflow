"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar } from "@/components/ui/avatar"
import { supabase } from "@/lib/supabase"
import { 
  Users, Phone, Mail, Building, Clock, TrendingUp, Star, 
  ArrowLeft, PhoneCall, MessageCircle, Calendar, Award,
  CheckCircle, XCircle, AlertCircle
} from "lucide-react"
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

export default function RepDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [rep, setRep] = useState<Rep | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [calling, setCalling] = useState(false)

  useEffect(() => {
    if (params.id) {
      loadRep(params.id as string)
    }
  }, [params.id])

  const loadRep = async (repId: string) => {
    try {
      setLoading(true)
      setError(null)
      
      const { data, error } = await supabase
        .from("reps")
        .select("*")
        .eq("id", repId)
        .single()

      if (error) {
        console.error("Error loading rep:", error)
        setError("Representative not found")
        return
      }

      setRep(data)
    } catch (err) {
      console.error("Error loading rep:", err)
      setError("Failed to load representative")
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case "break":
        return <AlertCircle className="h-4 w-4 text-yellow-600" />
      case "offline":
        return <XCircle className="h-4 w-4 text-gray-600" />
      default:
        return <XCircle className="h-4 w-4 text-gray-600" />
    }
  }

  const handleCall = async () => {
    setCalling(true)
    // Simulate call initiation (non-functional for now)
    setTimeout(() => {
      setCalling(false)
      alert("Call functionality will be implemented in the future!")
    }, 2000)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="home" />
        <div className="flex min-h-[calc(100vh-80px)] items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading representative...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error || !rep) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="home" />
        <div className="mx-auto max-w-4xl px-6 py-8">
          <div className="text-center">
            <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold mb-2">Representative Not Found</h1>
            <p className="text-muted-foreground mb-6">
              The representative you're looking for doesn't exist or has been removed.
            </p>
            <Button onClick={() => router.push('/reps')} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Representatives
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="home" />
      
      <div className="mx-auto max-w-4xl px-6 py-8">
        {/* Back Button */}
        <Button 
          onClick={() => router.push('/reps')} 
          variant="ghost" 
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Representatives
        </Button>

        {/* Rep Header */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
            <Avatar className="h-24 w-24">
              <div className="h-full w-full bg-primary/10 flex items-center justify-center">
                <span className="text-3xl font-bold text-primary">
                  {rep.display_name.charAt(0).toUpperCase()}
                </span>
              </div>
            </Avatar>
            
            <div className="flex-1">
              <div className="flex flex-col md:flex-row md:items-center gap-4 mb-4">
                <div>
                  <h1 className="text-3xl font-bold mb-2">{rep.display_name}</h1>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Building className="h-4 w-4" />
                    <span>{rep.organization}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className={getStatusColor(rep.status)}>
                    {getStatusIcon(rep.status)}
                    <span className="ml-1">{rep.status.charAt(0).toUpperCase() + rep.status.slice(1)}</span>
                  </Badge>
                </div>
              </div>
              
              {/* Contact Information */}
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="h-4 w-4" />
                  <span>{rep.email}</span>
                </div>
                {rep.phone && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Phone className="h-4 w-4" />
                    <span>{rep.phone}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Call Action */}
        <Card className="mb-8 border-primary/20 bg-primary/5">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold mb-2">Ready to Get Help?</h3>
                <p className="text-muted-foreground">
                  {rep.status === 'active' 
                    ? `${rep.display_name} is currently available and ready to assist you.`
                    : rep.status === 'break'
                    ? `${rep.display_name} is currently on a break but will be back soon.`
                    : `${rep.display_name} is currently offline. You can still leave a message.`
                  }
                </p>
              </div>
              <div className="flex gap-3">
                <Button 
                  onClick={handleCall}
                  disabled={calling || rep.status === 'offline'}
                  size="lg"
                  className="flex items-center gap-2"
                >
                  <PhoneCall className="h-5 w-5" />
                  {calling ? "Connecting..." : "Call Now"}
                </Button>
                <Button 
                  variant="outline" 
                  size="lg"
                  className="flex items-center gap-2"
                >
                  <MessageCircle className="h-5 w-5" />
                  Message
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{rep.calls_handled}</p>
                  <p className="text-sm text-muted-foreground">Calls Handled</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Star className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${getSatisfactionColor(rep.satisfaction)}`}>
                    {rep.satisfaction}%
                  </p>
                  <p className="text-sm text-muted-foreground">Satisfaction</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Clock className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{rep.avg_response_time}</p>
                  <p className="text-sm text-muted-foreground">Avg Response</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{rep.current_calls}</p>
                  <p className="text-sm text-muted-foreground">Active Calls</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Information */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Award className="h-5 w-5" />
                Performance Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Total Calls Handled</span>
                <span className="font-semibold">{rep.calls_handled}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Customer Satisfaction</span>
                <span className={`font-semibold ${getSatisfactionColor(rep.satisfaction)}`}>
                  {rep.satisfaction}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Average Response Time</span>
                <span className="font-semibold">{rep.avg_response_time}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Currently Active Calls</span>
                <span className="font-semibold">{rep.current_calls}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Availability
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Current Status</span>
                <Badge className={getStatusColor(rep.status)}>
                  {getStatusIcon(rep.status)}
                  <span className="ml-1">{rep.status.charAt(0).toUpperCase() + rep.status.slice(1)}</span>
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Member Since</span>
                <span className="font-semibold">
                  {new Date(rep.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Last Updated</span>
                <span className="font-semibold">
                  {new Date(rep.updated_at).toLocaleDateString()}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Call to Action */}
        <Card className="mt-8 bg-primary/5 border-primary/20">
          <CardContent className="p-8 text-center">
            <h3 className="text-2xl font-bold mb-4">Need Immediate Assistance?</h3>
            <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
              {rep.display_name} is here to help you with any questions or concerns. 
              {rep.status === 'active' 
                ? " They're currently available and ready to assist you right now."
                : " While they're currently " + rep.status + ", you can still reach out and they'll get back to you as soon as possible."
              }
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                onClick={handleCall}
                disabled={calling || rep.status === 'offline'}
                size="lg"
                className="flex items-center gap-2"
              >
                <PhoneCall className="h-5 w-5" />
                {calling ? "Connecting..." : "Call Now"}
              </Button>
              <Button 
                variant="outline" 
                size="lg"
                className="flex items-center gap-2"
              >
                <MessageCircle className="h-5 w-5" />
                Send Message
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
