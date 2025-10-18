"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Phone, Clock, ArrowLeft } from "lucide-react"
import Link from "next/link"
import Navigation from "@/components/Navigation"

// Mock data for ongoing calls
const ongoingCalls = [
  {
    id: 1,
    customer: "Sarah Johnson",
    duration: "00:03:24",
    sentiment: "positive",
    status: "active",
    transcript: [
      { speaker: "customer", message: "Hi, I need help with my recent order.", time: "00:00:05" },
      {
        speaker: "agent",
        message: "Hello Sarah! I'd be happy to help you with your order. Could you please provide your order number?",
        time: "00:00:12",
      },
      { speaker: "customer", message: "Sure, it's #ORD-12345", time: "00:00:18" },
      {
        speaker: "agent",
        message:
          "Thank you! Let me pull up your order details. I can see your order was placed on March 15th. What seems to be the issue?",
        time: "00:00:25",
      },
      { speaker: "customer", message: "I haven't received it yet and it's been over a week.", time: "00:00:35" },
      {
        speaker: "agent",
        message: "I understand your concern. Let me check the shipping status for you right away.",
        time: "00:00:42",
      },
      { speaker: "customer", message: "Thank you, I appreciate it.", time: "00:00:48" },
      {
        speaker: "agent",
        message:
          "I can see that your package is currently in transit and should arrive by tomorrow. I'll send you a tracking link via email.",
        time: "00:00:55",
      },
    ],
  },
  {
    id: 2,
    customer: "Michael Chen",
    duration: "00:01:45",
    sentiment: "neutral",
    status: "active",
    transcript: [
      { speaker: "customer", message: "Hello, I want to upgrade my subscription plan.", time: "00:00:03" },
      {
        speaker: "agent",
        message: "Great! I can help you with that. Which plan are you currently on?",
        time: "00:00:08",
      },
      { speaker: "customer", message: "I'm on the Basic plan right now.", time: "00:00:14" },
      {
        speaker: "agent",
        message:
          "Perfect! We have Pro and Enterprise plans available. The Pro plan includes advanced analytics and priority support. Would you like to hear more about it?",
        time: "00:00:20",
      },
      { speaker: "customer", message: "Yes, what's the pricing difference?", time: "00:00:32" },
    ],
  },
  {
    id: 3,
    customer: "Emily Rodriguez",
    duration: "00:05:12",
    sentiment: "negative",
    status: "active",
    transcript: [
      {
        speaker: "customer",
        message: "I'm very frustrated. My account has been locked for no reason!",
        time: "00:00:02",
      },
      {
        speaker: "agent",
        message:
          "I'm so sorry to hear that, Emily. Let me help you resolve this immediately. Can you tell me when you first noticed the issue?",
        time: "00:00:10",
      },
      {
        speaker: "customer",
        message: "This morning when I tried to log in. I've been a customer for 3 years!",
        time: "00:00:18",
      },
      {
        speaker: "agent",
        message:
          "I completely understand your frustration, and I apologize for the inconvenience. Let me check your account security logs.",
        time: "00:00:26",
      },
      { speaker: "customer", message: "Please hurry, I need to access my files urgently.", time: "00:00:35" },
      {
        speaker: "agent",
        message:
          "I see the issue - there was an unusual login attempt from a different location which triggered our security protocol. I'm unlocking your account now.",
        time: "00:00:42",
      },
      { speaker: "customer", message: "Oh, that might have been me traveling. Can you unlock it?", time: "00:00:52" },
      {
        speaker: "agent",
        message:
          "Yes, your account is now unlocked. I've also added a note to prevent this in the future. You should be able to log in now.",
        time: "00:01:00",
      },
    ],
  },
  {
    id: 4,
    customer: "David Park",
    duration: "00:02:30",
    sentiment: "positive",
    status: "active",
    transcript: [
      { speaker: "customer", message: "Hi there! I just wanted to say your product is amazing!", time: "00:00:04" },
      {
        speaker: "agent",
        message:
          "Thank you so much, David! We're thrilled to hear that. Is there anything specific you'd like to share or any way we can help you today?",
        time: "00:00:11",
      },
      {
        speaker: "customer",
        message: "Actually, yes. I'd like to refer some colleagues. Do you have a referral program?",
        time: "00:00:20",
      },
      {
        speaker: "agent",
        message:
          "We have a great referral program. For each person you refer who signs up, you both get a 20% discount on your next month.",
        time: "00:00:28",
      },
    ],
  },
]

export default function TranscriptsPage() {
  const [selectedCall, setSelectedCall] = useState(ongoingCalls[0])

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-green-500/10 text-green-500 border-green-500/20"
      case "negative":
        return "bg-red-500/10 text-red-500 border-red-500/20"
      default:
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="dashboard" />
      
      {/* Page Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold">Call Transcripts</h1>
              <p className="text-sm text-muted-foreground">Real-time conversation monitoring</p>
            </div>
          </div>
          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
            <Phone className="h-3 w-3 mr-1" />
            {ongoingCalls.length} Active Calls
          </Badge>
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Left Sidebar - Call List */}
        <aside className="w-80 border-r border-border bg-card/30">
          <div className="p-4 border-b border-border">
            <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Ongoing Calls</h2>
          </div>
          <ScrollArea className="h-[calc(100vh-145px)]">
            <div className="p-2 space-y-2">
              {ongoingCalls.map((call) => (
                <Card
                  key={call.id}
                  className={`p-4 cursor-pointer transition-all hover:bg-accent/50 ${
                    selectedCall.id === call.id ? "bg-accent border-primary" : "bg-card/50"
                  }`}
                  onClick={() => setSelectedCall(call)}
                >
                  <div className="flex items-start gap-3">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-primary/10 text-primary">
                        {call.customer
                          .split(" ")
                          .map((n) => n[0])
                          .join("")}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="font-medium text-sm truncate">{call.customer}</p>
                        <Badge variant="outline" className={`text-xs ${getSentimentColor(call.sentiment)}`}>
                          {call.sentiment}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{call.duration}</span>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </aside>

        {/* Right Side - Transcript View */}
        <main className="flex-1 flex flex-col">
          {/* Call Header */}
          <div className="p-6 border-b border-border bg-card/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Avatar className="h-12 w-12">
                  <AvatarFallback className="bg-primary/10 text-primary text-lg">
                    {selectedCall.customer
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="text-xl font-semibold">{selectedCall.customer}</h2>
                  <div className="flex items-center gap-3 mt-1">
                    <Badge variant="outline" className={getSentimentColor(selectedCall.sentiment)}>
                      {selectedCall.sentiment}
                    </Badge>
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {selectedCall.duration}
                    </span>
                  </div>
                </div>
              </div>
              <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                <div className="h-2 w-2 bg-green-500 rounded-full mr-2 animate-pulse" />
                Live
              </Badge>
            </div>
          </div>

          {/* Transcript Messages */}
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4 max-w-4xl mx-auto">
              {selectedCall.transcript.map((message, index) => (
                <div key={index} className={`flex gap-3 ${message.speaker === "agent" ? "flex-row-reverse" : ""}`}>
                  <Avatar className="h-8 w-8 flex-shrink-0">
                    <AvatarFallback
                      className={message.speaker === "agent" ? "bg-primary text-primary-foreground" : "bg-muted"}
                    >
                      {message.speaker === "agent" ? "AI" : "C"}
                    </AvatarFallback>
                  </Avatar>
                  <div className={`flex flex-col gap-1 max-w-[70%] ${message.speaker === "agent" ? "items-end" : ""}`}>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="font-medium">{message.speaker === "agent" ? "AI Agent" : "Customer"}</span>
                      <span>{message.time}</span>
                    </div>
                    <Card
                      className={`p-3 ${
                        message.speaker === "agent" ? "bg-primary text-primary-foreground" : "bg-muted"
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{message.message}</p>
                    </Card>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </main>
      </div>
    </div>
  )
}
