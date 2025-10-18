"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Mic, Phone, Upload, FileText, TrendingUp, Users, Clock } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import Navigation from "@/components/Navigation"
import PendingCalls from "@/components/PendingCalls"
import { useActiveSessions } from "@/hooks/useActiveSessions"

export default function DashboardPage() {
  const router = useRouter()
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const { activeSessions, loading: sessionsLoading } = useActiveSessions()

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles([...uploadedFiles, ...Array.from(e.target.files)])
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files) {
      setUploadedFiles([...uploadedFiles, ...Array.from(e.dataTransfer.files)])
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const getTimeSince = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}:${String(minutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
    return `${minutes}:${String(seconds % 60).padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="dashboard" />

      <main className="container mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Monitor your AI voice assistant performance</p>
        </div>

        {/* Stats Cards */}
        <div className="mb-8 grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Calls Attended</CardTitle>
              <Phone className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1,284</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-500">+12.5%</span> from last month
              </p>
              <Progress value={65} className="mt-3" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Ongoing Calls</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {sessionsLoading ? '...' : activeSessions.length}
              </div>
              <p className="text-xs text-muted-foreground">Active conversations right now</p>
              <div className="mt-3 flex gap-2">
                {activeSessions.slice(0, 5).map((session) => (
                  <div key={session.id} className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Avg. Response Time
              </CardTitle>
              <CardDescription>Real-time monitoring of active conversations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1.2s</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-500">-0.3s</span> faster than average
              </p>
              <Progress value={85} className="mt-3" />
            </CardContent>
          </Card>
        </div>

        {/* Pending Call Requests */}
        <div className="mb-8">
          <PendingCalls />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Knowledge Base Upload */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Knowledge Base
              </CardTitle>
              <CardDescription>Upload documents to train your AI assistant</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                  isDragging ? "border-primary bg-primary/5" : "border-border"
                }`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">Drag and drop files here</p>
                <p className="text-xs text-muted-foreground">or click to browse</p>
                <Input
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  className="mt-4"
                  accept=".pdf,.doc,.docx,.txt"
                />
              </div>

              {uploadedFiles.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Uploaded Files ({uploadedFiles.length})</Label>
                  <div className="space-y-2">
                    {uploadedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between rounded-lg border border-border p-3"
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{file.name}</span>
                        </div>
                        <Badge variant="secondary">{(file.size / 1024).toFixed(1)} KB</Badge>
                      </div>
                    ))}
                  </div>
                  <Button className="w-full">Process Knowledge Base</Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Ongoing Calls */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Ongoing Calls ({activeSessions.length})
              </CardTitle>
              <CardDescription>Real-time monitoring of active conversations</CardDescription>
            </CardHeader>
            <CardContent>
              {sessionsLoading ? (
                <div className="text-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                  <p className="text-muted-foreground">Loading sessions...</p>
                </div>
              ) : activeSessions.length === 0 ? (
                <div className="text-center py-8">
                  <Phone className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                  <p className="text-muted-foreground">No active calls at the moment</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {activeSessions.map((session) => (
                    <div
                      key={session.id}
                      className="flex cursor-pointer items-center justify-between rounded-lg border border-border p-4 transition-colors hover:bg-accent"
                      onClick={() => router.push(`/session/${session.id}`)}
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                          <Phone className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{session.customer_name || 'Anonymous'}</p>
                          <p className="text-xs text-muted-foreground">Duration: {getTimeSince(session.created_at)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="default" className="bg-green-500">
                          Active
                        </Badge>
                        <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <Button
                variant="outline"
                className="mt-4 w-full bg-transparent"
                onClick={() => router.push("/transcripts")}
              >
                View All Calls
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
