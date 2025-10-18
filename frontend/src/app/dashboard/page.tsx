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
import { useState } from "react"

export default function DashboardPage() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)

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

  // Mock data for ongoing calls
  const ongoingCalls = [
    { id: 1, customer: "John Smith", duration: "5:23", status: "active", sentiment: "positive" },
    { id: 2, customer: "Sarah Johnson", duration: "2:45", status: "active", sentiment: "neutral" },
    { id: 3, customer: "Mike Davis", duration: "8:12", status: "active", sentiment: "positive" },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Mic className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">VoiceFlow AI</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Button variant="ghost">Settings</Button>
            <Button variant="ghost">Profile</Button>
          </nav>
        </div>
      </header>

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
              <div className="text-2xl font-bold">{ongoingCalls.length}</div>
              <p className="text-xs text-muted-foreground">Active conversations right now</p>
              <div className="mt-3 flex gap-2">
                {ongoingCalls.map((call) => (
                  <div key={call.id} className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg. Response Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
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
                Ongoing Calls
              </CardTitle>
              <CardDescription>Real-time monitoring of active conversations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {ongoingCalls.map((call) => (
                  <div key={call.id} className="flex items-center justify-between rounded-lg border border-border p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                        <Phone className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{call.customer}</p>
                        <p className="text-xs text-muted-foreground">Duration: {call.duration}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          call.sentiment === "positive"
                            ? "default"
                            : call.sentiment === "neutral"
                              ? "secondary"
                              : "destructive"
                        }
                      >
                        {call.sentiment}
                      </Badge>
                      <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                    </div>
                  </div>
                ))}
              </div>

              <Button variant="outline" className="mt-4 w-full bg-transparent">
                View All Calls
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
