/**
 * API utility for handling environment-specific API calls
 */



// Determine the API base URL based on the environment
const getApiBaseUrl = (): string => {
  // In development mode (Vite dev server), the proxy handles the routing
  // Force empty string in development to ensure proxy usage
  if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
    return ''
  }
  
  // In production mode, we need to specify the full backend URL
  // You can customize this URL based on your production setup
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001'
  return apiUrl
}

const API_BASE_URL = getApiBaseUrl()

/**
 * Wrapper around fetch that handles the API base URL
 */
export const apiFetch = async (endpoint: string, options?: RequestInit): Promise<Response> => {
  // Ensure the endpoint starts with /api
  if (!endpoint.startsWith('/api')) {
    throw new Error('API endpoints must start with /api')
  }
  
  const url = API_BASE_URL + endpoint
  return fetch(url, options)
}

/**
 * Helper function for JSON API calls
 */
export const apiRequest = async <T = any>(
  endpoint: string, 
  options?: RequestInit
): Promise<T> => {
  const response = await apiFetch(endpoint, options)
  
  if (!response.ok) {
    let errorMessage = 'Unknown error'
    try {
      const errorData = await response.json()
      // Try multiple possible error field names
      errorMessage = errorData.error || errorData.message || errorData.details || `HTTP ${response.status}: ${response.statusText}`
      
      // For 404 errors, provide clearer messaging
      if (response.status === 404) {
        if (endpoint.includes('/files/content/')) {
          throw new Error(`File not found: The file may have been deleted or moved`)
        }
        throw new Error(`Resource not found: ${errorMessage}`)
      }
      
    } catch (parseError) {
      if (parseError instanceof Error) throw parseError
      errorMessage = `HTTP ${response.status}: ${response.statusText}`
    }
    throw new Error(errorMessage)
  }
  
  return response.json()
}

/**
 * Session Summary update API response type
 */
export interface SessionSummaryUpdateResponse {
  success: boolean
  message: string
  updated: boolean
  summary?: string
  individual_summary_created?: boolean
}

/**
 * Trigger Session Summary update (for hybrid summary system)
 */
export const triggerSessionSummaryUpdate = async (force: boolean = true): Promise<any> => {
  return apiRequest<any>('/api/session-summary/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ force, async: true, lock_timeout: 0.2, max_duration_secs: 2 })
  })
}

/**
 * Comprehensive summary generation API response type
 */
export interface ComprehensiveSummaryGenerationResponse {
  success: boolean
  message: string
  result?: {
    processed: boolean
    summary_id?: number
    changes_count: number
    files_count: number
    time_range_start: string
    time_range_end: string
    processing_time: number
    time_span: string
    summary_preview?: string
    reason?: string
    error?: string
  }
}

/**
 * Comprehensive summary data type
 */
export interface ComprehensiveSummary {
  id: number
  timestamp: string
  time_range_start: string
  time_range_end: string
  summary_content: string
  key_topics: string[]
  key_keywords: string[]
  overall_impact: 'brief' | 'moderate' | 'significant'
  files_affected_count: number
  changes_count: number
  time_span: string
  created_at: string
}

/**
 * Comprehensive summaries list response type
 */
export interface ComprehensiveSummariesResponse {
  summaries: ComprehensiveSummary[]
  pagination: {
    current_page: number
    page_size: number
    total_count: number
    total_pages: number
    has_next: boolean
    has_previous: boolean
  }
}

/**
 * Generate comprehensive summary covering everything since last summary
 */
export const triggerComprehensiveSummaryGeneration = async (force: boolean = true): Promise<any> => {
  return apiRequest<any>('/api/monitor/comprehensive-summary/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ force, async: true, max_duration_secs: 2 })
  })
}

/**
 * Get comprehensive summary generation status
 */
export interface ComprehensiveStatusEntry {
  step: string
  message: string
  details?: string | null
  progress?: number | null
  timestamp?: string
}

export interface ComprehensiveStatusResponse {
  running: boolean
  status?: ComprehensiveStatusEntry | null
  history?: ComprehensiveStatusEntry[]
  last?: any
}

export const getComprehensiveSummaryStatus = async (): Promise<ComprehensiveStatusResponse> => {
  return apiRequest<ComprehensiveStatusResponse>('/api/monitor/comprehensive-summary/status')
}

/**
 * Get paginated list of comprehensive summaries
 */
export const getComprehensiveSummaries = async (page: number = 1, pageSize: number = 10): Promise<ComprehensiveSummariesResponse> => {
  return apiRequest<ComprehensiveSummariesResponse>(`/api/monitor/comprehensive-summary/list?page=${page}&page_size=${pageSize}`)
}

/**
 * Get details of a specific comprehensive summary
 */
export const getComprehensiveSummary = async (summaryId: number): Promise<ComprehensiveSummary> => {
  return apiRequest<ComprehensiveSummary>(`/api/monitor/comprehensive-summary/${summaryId}`)
}

/**
 * Delete a comprehensive summary
 */
export const deleteComprehensiveSummary = async (summaryId: number): Promise<{success: boolean, message: string}> => {
  return apiRequest(`/api/monitor/comprehensive-summary/${summaryId}`, {
    method: 'DELETE'
  })
}

/**
 * Convenience API object with REST-style methods
 */
export const api = {
  get: async <T = any>(endpoint: string, options?: RequestInit): Promise<T> => {
    return apiRequest<T>(endpoint, {
      ...options,
      method: 'GET'
    })
  },

  post: async <T = any>(endpoint: string, body?: any, options?: RequestInit): Promise<T> => {
    return apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: body ? JSON.stringify(body) : undefined
    })
  },

  put: async <T = any>(endpoint: string, body?: any, options?: RequestInit): Promise<T> => {
    return apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: body ? JSON.stringify(body) : undefined
    })
  },

  delete: async <T = any>(endpoint: string, options?: RequestInit): Promise<T> => {
    return apiRequest<T>(endpoint, {
      ...options,
      method: 'DELETE'
    })
  },

  patch: async <T = any>(endpoint: string, body?: any, options?: RequestInit): Promise<T> => {
    return apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      },
      body: body ? JSON.stringify(body) : undefined
    })
  }
}
