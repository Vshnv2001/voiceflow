"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { Mic, Zap, Shield, TrendingUp, Users, Clock } from "lucide-react"
import Navigation from "@/components/Navigation"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="home" />

      {/* Hero Section */}
      <section className="mx-auto max-w-7xl px-6 py-24 text-center">
        <Badge variant="secondary" className="mb-6">
          AI-Powered Customer Service
        </Badge>
        <h1 className="mb-6 text-balance text-5xl font-bold tracking-tight md:text-6xl lg:text-7xl">
          Cursor for <span className="text-primary">Customer Service</span>
        </h1>
        <p className="mx-auto mb-8 max-w-2xl text-pretty text-lg text-muted-foreground md:text-xl">
          Empower your support team with real-time AI suggestions. Respond faster, more accurately, and deliver
          exceptional customer experiences.
        </p>
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button size="lg" asChild>
            <Link href="/signup">Start Free Trial</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="#demo">Watch Demo</Link>
          </Button>
        </div>

        {/* Stats */}
        <div className="mx-auto mt-16 grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-3">
          <div>
            <div className="text-4xl font-bold text-primary">85%</div>
            <div className="mt-2 text-sm text-muted-foreground">Faster Response Time</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-primary">10k+</div>
            <div className="mt-2 text-sm text-muted-foreground">Active Users</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-primary">99.9%</div>
            <div className="mt-2 text-sm text-muted-foreground">Uptime</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="border-t border-border bg-muted/50 py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-16 text-center">
            <h2 className="mb-4 text-balance text-3xl font-bold md:text-4xl">Everything you need to excel</h2>
            <p className="mx-auto max-w-2xl text-pretty text-muted-foreground">
              Built for customer service teams who demand speed, accuracy, and reliability
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="p-6">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">Real-Time Suggestions</h3>
              <p className="text-sm text-muted-foreground">
                Get instant AI-powered response suggestions as you type, helping you respond faster and more accurately.
              </p>
            </Card>

            <Card className="p-6">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">Enterprise Security</h3>
              <p className="text-sm text-muted-foreground">
                Bank-level encryption and compliance with SOC 2, GDPR, and HIPAA standards to keep your data safe.
              </p>
            </Card>

            <Card className="p-6">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <TrendingUp className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">Performance Analytics</h3>
              <p className="text-sm text-muted-foreground">
                Track team performance, response times, and customer satisfaction with detailed analytics dashboards.
              </p>
            </Card>

            <Card className="p-6">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Users className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">Team Collaboration</h3>
              <p className="text-sm text-muted-foreground">
                Share knowledge, templates, and best practices across your entire support team seamlessly.
              </p>
            </Card>

            <Card className="p-6">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Clock className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">24/7 Availability</h3>
              <p className="text-sm text-muted-foreground">
                AI assistance that never sleeps, ensuring your team always has support when they need it most.
              </p>
            </Card>

            <Card className="p-6">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Mic className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mb-2 text-xl font-semibold">Voice Integration</h3>
              <p className="text-sm text-muted-foreground">
                Seamlessly integrate with voice channels for complete omnichannel support coverage.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="mb-4 text-balance text-3xl font-bold md:text-4xl">
            Ready to transform your customer service?
          </h2>
          <p className="mb-8 text-pretty text-lg text-muted-foreground">
            Join thousands of teams already using VoiceFlow AI to deliver exceptional support.
          </p>
          <Button size="lg" asChild>
            <Link href="/signup">Start Free Trial</Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded bg-primary">
                <Mic className="h-4 w-4 text-primary-foreground" />
              </div>
              <span className="font-semibold">VoiceFlow AI</span>
            </div>
            <p className="text-sm text-muted-foreground">© 2025 VoiceFlow AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
