"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useAuth } from "@/contexts/AuthContext"
import { supabase } from "@/lib/supabase"
import { useRouter } from "next/navigation"
import { Settings, Save, User, Building, Mail, Phone, MapPin } from "lucide-react"
import Navigation from "@/components/Navigation"

interface RepData {
  id?: string
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
  created_at?: string
  updated_at?: string
}

export default function SettingsPage() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [repData, setRepData] = useState<RepData | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error', message: string } | null>(null)

  // Form state
  const [formData, setFormData] = useState({
    display_name: "",
    organization: "",
    email: "",
    phone: "",
  })

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login")
    }
  }, [user, authLoading, router])

  // Load existing rep data
  useEffect(() => {
    if (user) {
      loadRepData()
    }
  }, [user])

  const loadRepData = async () => {
    if (!user) return

    try {
      setLoading(true)
      const { data, error } = await supabase
        .from("reps")
        .select("*")
        .eq("user_id", user.id)
        .single()

      if (error && error.code !== "PGRST116") {
        // PGRST116 is "not found" error, which is expected for new users
        console.error("Error loading rep data:", error)
        setNotification({ type: 'error', message: 'Failed to load settings' })
        return
      }

      if (data) {
        setRepData(data)
        setFormData({
          display_name: data.display_name || "",
          organization: data.organization || "",
          email: data.email || user.email || "",
          phone: data.phone || "",
        })
      } else {
        // Initialize with user data
        setFormData({
          display_name: user.user_metadata?.full_name || "",
          organization: user.user_metadata?.organization || "",
          email: user.email || "",
          phone: "",
        })
      }
    } catch (error) {
      console.error("Error loading rep data:", error)
      setNotification({ type: 'error', message: 'Failed to load settings' })
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSave = async () => {
    if (!user) return

    // Basic validation
    if (!formData.display_name.trim()) {
      setNotification({ type: 'error', message: 'Display name is required' })
      return
    }
    if (!formData.organization.trim()) {
      setNotification({ type: 'error', message: 'Organization is required' })
      return
    }
    if (!formData.email.trim()) {
      setNotification({ type: 'error', message: 'Email is required' })
      return
    }

    try {
      setSaving(true)

      const repRecord = {
        user_id: user.id,
        display_name: formData.display_name.trim(),
        organization: formData.organization.trim(),
        email: formData.email.trim(),
        phone: formData.phone.trim() || null,
        status: "active",
        calls_handled: repData?.calls_handled || 0,
        avg_response_time: repData?.avg_response_time || "0s",
        satisfaction: repData?.satisfaction || 0,
        current_calls: repData?.current_calls || 0,
      }

      if (repData) {
        // Update existing record
        const { error } = await supabase
          .from("reps")
          .update(repRecord)
          .eq("user_id", user.id)

        if (error) {
          console.error("Error updating rep data:", error)
          setNotification({ type: 'error', message: 'Failed to save settings' })
          return
        }
      } else {
        // Insert new record
        const { error } = await supabase
          .from("reps")
          .insert(repRecord)

        if (error) {
          console.error("Error inserting rep data:", error)
          setNotification({ type: 'error', message: 'Failed to save settings' })
          return
        }
      }

      setNotification({ type: 'success', message: 'Settings saved successfully!' })
      
      // Reload the data to get the updated record
      await loadRepData()
    } catch (error) {
      console.error("Error saving rep data:", error)
      setNotification({ type: 'error', message: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation variant="dashboard" />
        <div className="flex min-h-[calc(100vh-80px)] items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading settings...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="dashboard" />
      
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground mt-2">
            Manage your organization details and contact information
          </p>
        </div>

        {/* Notification */}
        {notification && (
          <div className={`mb-6 p-4 rounded-md border ${
            notification.type === 'success' 
              ? 'bg-green-50 border-green-200 text-green-800' 
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <div className="flex items-center justify-between">
              <span>{notification.message}</span>
              <button
                onClick={() => setNotification(null)}
                className="ml-4 text-current hover:opacity-70"
              >
                ×
              </button>
            </div>
          </div>
        )}

        <div className="grid gap-6">
          {/* Profile Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Profile Information
              </CardTitle>
              <CardDescription>
                Update your personal details and organization information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="display_name">Display Name *</Label>
                  <Input
                    id="display_name"
                    value={formData.display_name}
                    onChange={(e) => handleInputChange("display_name", e.target.value)}
                    placeholder="Enter your display name"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="organization">Organization *</Label>
                  <div className="relative">
                    <Building className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="organization"
                      value={formData.organization}
                      onChange={(e) => handleInputChange("organization", e.target.value)}
                      placeholder="Enter your organization"
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address *</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleInputChange("email", e.target.value)}
                      placeholder="Enter your email"
                      className="pl-10"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="phone"
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => handleInputChange("phone", e.target.value)}
                      placeholder="Enter your phone number"
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button 
              onClick={handleSave} 
              disabled={saving}
              className="flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {saving ? "Saving..." : "Save Settings"}
            </Button>
          </div>

          {/* Information Card */}
          <Card className="border-blue-200 bg-blue-50/50">
            <CardHeader>
              <CardTitle className="text-blue-900 flex items-center gap-2">
                <Settings className="h-5 w-5" />
                About Your Settings
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-blue-800 text-sm">
                Your settings will be saved to your representative profile in the system. 
                This information will be used to identify you in calls and transcripts. 
                Make sure to keep your contact details up to date.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
