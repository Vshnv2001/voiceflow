"use client"

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Phone, PhoneCall, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { initiateCustomerServiceCall } from '@/lib/api'

interface CustomerServiceCallProps {
  onCallInitiated: (sessionId: string) => void
}

export default function CustomerServiceCall({ onCallInitiated }: CustomerServiceCallProps) {
  const { user } = useAuth()
  const [isInitiating, setIsInitiating] = useState(false)
  const [callData, setCallData] = useState({
    customer_name: '',
    priority: 'normal',
    issue_type: '',
    description: ''
  })
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleInputChange = (field: string, value: string) => {
    setCallData(prev => ({
      ...prev,
      [field]: value
    }))
    setError(null)
    setSuccess(null)
  }

  const initiateCall = async () => {
    if (!user) {
      setError('You must be logged in to initiate a call')
      return
    }

    setIsInitiating(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await initiateCustomerServiceCall({
        customer_name: callData.customer_name,
        priority: callData.priority,
        issue_type: callData.issue_type || undefined,
        description: callData.description || undefined,
        metadata: {
          initiated_from: 'web_interface'
        }
      })

      if (response.data) {
        setSuccess('Call initiated successfully! Waiting for agent to accept...')
        onCallInitiated((response.data as any).id)
        
        // Reset form
        setCallData({
          customer_name: '',
          priority: 'normal',
          issue_type: '',
          description: ''
        })
      } else {
        setError(response.error || 'Failed to initiate call')
      }
    } catch (error) {
      console.error('Error initiating call:', error)
      setError('Network error. Please try again.')
    } finally {
      setIsInitiating(false)
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PhoneCall className="w-6 h-6" />
          Initiate Customer Service Call
        </CardTitle>
        <p className="text-muted-foreground">
          Start a customer service call and wait for an agent to accept it.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Customer Name */}
        <div className="space-y-2">
          <Label htmlFor="customer-name">Customer Name *</Label>
          <Input
            id="customer-name"
            placeholder="Enter customer name"
            value={callData.customer_name}
            onChange={(e) => handleInputChange('customer_name', e.target.value)}
            required
          />
        </div>

        {/* Priority */}
        <div className="space-y-2">
          <Label htmlFor="priority">Priority Level</Label>
          <Select value={callData.priority} onValueChange={(value: string) => handleInputChange('priority', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Low - General inquiry</SelectItem>
              <SelectItem value="normal">Normal - Standard support</SelectItem>
              <SelectItem value="high">High - Urgent issue</SelectItem>
              <SelectItem value="urgent">Urgent - Critical problem</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Issue Type */}
        <div className="space-y-2">
          <Label htmlFor="issue-type">Issue Type (optional)</Label>
          <Select value={callData.issue_type} onValueChange={(value: string) => handleInputChange('issue_type', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select issue type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="technical">Technical Support</SelectItem>
              <SelectItem value="billing">Billing Inquiry</SelectItem>
              <SelectItem value="account">Account Management</SelectItem>
              <SelectItem value="product">Product Information</SelectItem>
              <SelectItem value="complaint">Complaint</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea
            id="description"
            placeholder="Brief description of your issue or inquiry..."
            value={callData.description}
            onChange={(e) => handleInputChange('description', e.target.value)}
            rows={4}
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700">
            <CheckCircle className="w-5 h-5" />
            <span>{success}</span>
          </div>
        )}

        {/* Submit Button */}
        <Button 
          onClick={initiateCall} 
          disabled={isInitiating}
          className="w-full"
          size="lg"
        >
          {isInitiating ? (
            <>
              <Phone className="w-4 h-4 mr-2 animate-pulse" />
              Initiating Call...
            </>
          ) : (
            <>
              <Phone className="w-4 h-4 mr-2" />
              Initiate Customer Service Call
            </>
          )}
        </Button>

        {/* Info */}
        <div className="text-sm text-muted-foreground text-center">
          <p>Once you initiate the call, an agent will be notified and can accept or reject it.</p>
          <p>You'll be able to communicate via voice messages once the call is accepted.</p>
        </div>
      </CardContent>
    </Card>
  )
}
