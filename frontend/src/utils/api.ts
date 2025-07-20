/**
 * API utility for handling environment-specific API calls
 */

import type { SearchResult, SemanticMetadata, SearchFilters } from '../types/index'

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

/**
 * Search the semantic index with optional filters
 */
export const searchSemanticIndex = async (filters: SearchFilters): Promise<{
  results: SearchResult[];
  total: number;
  metadata: SemanticMetadata;
}> => {
  const queryParams = new URLSearchParams()
  
  if (filters.query) queryParams.append('query', filters.query)
  if (filters.topics?.length) queryParams.append('topics', filters.topics.join(','))
  if (filters.keywords?.length) queryParams.append('keywords', filters.keywords.join(','))
  if (filters.dateFrom) queryParams.append('date_from', filters.dateFrom)
  if (filters.dateTo) queryParams.append('date_to', filters.dateTo)
  if (filters.minRelevance !== undefined) queryParams.append('min_relevance', filters.minRelevance.toString())
  if (filters.impact?.length) queryParams.append('impact', filters.impact.join(','))
  if (filters.sortBy) queryParams.append('sort_by', filters.sortBy)
  if (filters.limit !== undefined) queryParams.append('limit', filters.limit.toString())
  if (filters.offset !== undefined) queryParams.append('offset', filters.offset.toString())
  
  const endpoint = `/api/search${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
  return apiRequest(endpoint)
}

/**
 * Get all available topics with their counts
 */
export const getTopics = async (): Promise<Record<string, number>> => {
  return apiRequest('/api/search/topics')
}

/**
 * Get all available keywords with their counts
 */
export const getKeywords = async (): Promise<Record<string, number>> => {
  return apiRequest('/api/search/keywords')
}