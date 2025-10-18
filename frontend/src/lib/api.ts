/**
 * API utility functions for communicating with the backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ApiResponse<T = any> {
  data?: T
  error?: string
  status: number
}

class ApiClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`
    
    // Get auth token from localStorage
    const token = localStorage.getItem('token')
    
    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`
    }

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    }

    try {
      const response = await fetch(url, config)
      const data = await response.json()

      if (!response.ok) {
        return {
          error: data.detail || `HTTP ${response.status}: ${response.statusText}`,
          status: response.status,
        }
      }

      return {
        data,
        status: response.status,
      }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      }
    }
  }

  // Customer Service API
  async initiateCustomerServiceCall(callData: {
    customer_name?: string
    rep_id: string
    priority: string
    issue_type?: string
    description?: string
    metadata?: Record<string, any>
  }) {
    return this.request('/api/customer-service/call', {
      method: 'POST',
      body: JSON.stringify(callData),
    })
  }

  // Session API
  async createSession(sessionData: {
    customer_id?: string
    agent_id?: string
    session_type: string
    metadata?: Record<string, any>
  }) {
    return this.request('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    })
  }

  async getSessions(status?: string, limit = 50, offset = 0) {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    
    return this.request(`/api/sessions?${params.toString()}`)
  }

  async getSession(sessionId: string) {
    return this.request(`/api/sessions/${sessionId}`)
  }

  async closeSession(sessionId: string) {
    return this.request(`/api/sessions/${sessionId}/close`, {
      method: 'POST',
    })
  }

  async endCall(sessionId: string, callEndData: {
    reason?: string
    summary?: string
  }) {
    return this.request(`/api/sessions/${sessionId}/end-call`, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        ...callEndData,
      }),
    })
  }

  // Message API
  async getMessages(sessionId: string, limit = 50, offset = 0) {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    
    return this.request(`/api/sessions/${sessionId}/messages?${params.toString()}`)
  }

  async uploadVoiceMessage(sessionId: string, audioFile: File) {
    const formData = new FormData()
    formData.append('audio_file', audioFile)

    const token = localStorage.getItem('token')
    const headers: HeadersInit = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    return this.request(`/api/sessions/${sessionId}/messages/voice`, {
      method: 'POST',
      headers,
      body: formData,
    })
  }

  // Agent API
  async getPendingCalls() {
    return this.request('/api/agent/pending-calls')
  }

  async acceptCall(sessionId: string) {
    return this.request(`/api/agent/sessions/${sessionId}/accept`, {
      method: 'POST',
    })
  }

  async rejectCall(sessionId: string, reason?: string) {
    const params = new URLSearchParams()
    if (reason) params.append('reason', reason)
    
    return this.request(`/api/agent/sessions/${sessionId}/reject?${params.toString()}`, {
      method: 'POST',
    })
  }

  async getAgentSessions(status?: string) {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    
    return this.request(`/api/agent/sessions?${params.toString()}`)
  }

  async getAvailableAgents() {
    return this.request('/api/agent/available-agents')
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient()

// Export individual functions for convenience (properly bound)
export const initiateCustomerServiceCall = apiClient.initiateCustomerServiceCall.bind(apiClient)
export const createSession = apiClient.createSession.bind(apiClient)
export const getSessions = apiClient.getSessions.bind(apiClient)
export const getSession = apiClient.getSession.bind(apiClient)
export const closeSession = apiClient.closeSession.bind(apiClient)
export const endCall = apiClient.endCall.bind(apiClient)
export const getMessages = apiClient.getMessages.bind(apiClient)
export const uploadVoiceMessage = apiClient.uploadVoiceMessage.bind(apiClient)
export const getPendingCalls = apiClient.getPendingCalls.bind(apiClient)
export const acceptCall = apiClient.acceptCall.bind(apiClient)
export const rejectCall = apiClient.rejectCall.bind(apiClient)
export const getAgentSessions = apiClient.getAgentSessions.bind(apiClient)
export const getAvailableAgents = apiClient.getAvailableAgents.bind(apiClient)

export default apiClient
