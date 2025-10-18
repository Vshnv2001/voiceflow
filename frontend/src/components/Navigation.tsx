"use client"

import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Mic, LogOut, User } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { useRouter } from "next/navigation"
import { useState } from "react"

interface NavigationProps {
  variant?: "home" | "dashboard"
}

export default function Navigation({ variant = "home" }: NavigationProps) {
  const { user, signOut, loading } = useAuth()
  const router = useRouter()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true)
      const { error } = await signOut()
      if (error) {
        console.error('Logout error:', error)
      } else {
        router.push('/home')
      }
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      setIsLoggingOut(false)
    }
  }

  if (loading) {
    return (
      <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Mic className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">VoiceFlow AI</span>
          </div>
        </div>
      </nav>
    )
  }

  return (
    <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Mic className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold">VoiceFlow AI</span>
        </div>

        {/* Navigation Links */}
        <div className="hidden items-center gap-8 md:flex">
          {variant === "home" && (
            <>
              <Link href="#features" className="text-sm text-muted-foreground hover:text-foreground">
                Features
              </Link>
              <Link href="#pricing" className="text-sm text-muted-foreground hover:text-foreground">
                Pricing
              </Link>
              <Link href="/reps" className="text-sm text-muted-foreground hover:text-foreground">
                Reps
              </Link>
              <Link href="#about" className="text-sm text-muted-foreground hover:text-foreground">
                About
              </Link>
            </>
          )}
          {variant === "dashboard" && (
            <>
              <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
                Dashboard
              </Link>
              <Link href="/transcripts" className="text-sm text-muted-foreground hover:text-foreground">
                Transcripts
              </Link>
              <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground">
                Settings
              </Link>
            </>
          )}
        </div>

        {/* User Actions */}
        <div className="flex items-center gap-3">
          {user ? (
            // Authenticated user actions
            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 text-sm text-muted-foreground md:flex">
                <User className="h-4 w-4" />
                <span>{user.user_metadata?.full_name || user.email}</span>
              </div>
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                {isLoggingOut ? "Signing out..." : "Sign out"}
              </Button>
            </div>
          ) : (
            // Unauthenticated user actions
            <>
              <Button variant="ghost" asChild>
                <Link href="/login">Log in</Link>
              </Button>
              <Button asChild>
                <Link href="/signup">Get Started</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
