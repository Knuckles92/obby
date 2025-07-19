/**
 * API utility for handling environment-specific API calls
 */

// Determine the API base URL based on the environment
const getApiBaseUrl = (): string => {
  // In development mode (Vite dev server), the proxy handles the routing
  if (import.meta.env.DEV) {
    return ''
  }
  
  // In production mode, we need to specify the full backend URL
  // You can customize this URL based on your production setup
  return import.meta.env.VITE_API_URL || 'http://localhost:8001'
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
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}