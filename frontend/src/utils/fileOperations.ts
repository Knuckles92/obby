/**
 * File Operations API utilities
 * Handles file reading, writing, and searching operations
 */

import { apiRequest } from './api'

/**
 * File metadata and content response
 */
export interface FileContent {
  content: string
  path: string
  relativePath: string
  name: string
  size: number
  lastModified: number
  extension: string
  readable: boolean
}

/**
 * File write response
 */
export interface FileWriteResponse {
  success: boolean
  path: string
  relativePath: string
  name: string
  size: number
  lastModified: number
  backupCreated: boolean
  backupPath?: string | null
}

/**
 * Search result item
 */
export interface FileSearchResult {
  path: string
  relativePath: string
  name: string
  score: number
  size: number
  lastModified: number
  extension: string
  matchType: 'filename' | 'path' | 'fuzzy'
}

/**
 * Search response
 */
export interface FileSearchResponse {
  results: FileSearchResult[]
  query: string
  count: number
}

/**
 * File tree node
 */
export interface FileTreeNode {
  name: string
  path: string
  relativePath?: string
  type: 'file' | 'directory'
  size?: number
  lastModified?: number
  extension?: string
  children?: FileTreeNode[]
  childCount?: number
}

/**
 * Fetch file content
 *
 * @param filePath - Relative or absolute path to the file
 * @returns File content and metadata
 */
export const fetchFileContent = async (filePath: string): Promise<FileContent> => {
  // Encode the file path to handle special characters
  const encodedPath = filePath.split('/').map(encodeURIComponent).join('/')
  return apiRequest<FileContent>(`/api/files/content/${encodedPath}`)
}

/**
 * Save file content
 *
 * @param filePath - Relative or absolute path to the file
 * @param content - Content to write to the file
 * @param createBackup - Whether to create a backup before writing (default: true)
 * @returns Write operation result
 */
export const saveFileContent = async (
  filePath: string,
  content: string,
  createBackup: boolean = true
): Promise<FileWriteResponse> => {
  // Encode the file path to handle special characters
  const encodedPath = filePath.split('/').map(encodeURIComponent).join('/')

  return apiRequest<FileWriteResponse>(`/api/files/content/${encodedPath}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ content, createBackup })
  })
}

/**
 * Search files using fuzzy matching
 *
 * @param query - Search query string
 * @param maxResults - Maximum number of results to return (default: 50)
 * @returns Search results sorted by relevance
 */
export const searchFiles = async (
  query: string,
  maxResults: number = 50
): Promise<FileSearchResponse> => {
  return apiRequest<FileSearchResponse>('/api/files/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, maxResults })
  })
}

/**
 * Get file tree structure
 *
 * @returns Hierarchical file tree
 */
export const getFileTree = async (): Promise<FileTreeNode> => {
  const response = await apiRequest<{ tree: FileTreeNode }>('/api/files/tree')
  return response.tree
}

/**
 * Format file size for display
 *
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format timestamp for display
 *
 * @param timestamp - Unix timestamp in seconds
 * @returns Formatted date string
 */
export const formatFileDate = (timestamp: number): string => {
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  // Less than 1 day ago - show relative time
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    if (hours === 0) {
      const minutes = Math.floor(diff / 60000)
      return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
    }
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`
  }

  // Less than 7 days ago - show days
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days} day${days !== 1 ? 's' : ''} ago`
  }

  // Otherwise show date
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

/**
 * Get file icon based on extension
 *
 * @param fileName - Name of the file
 * @returns Icon name from lucide-react
 */
export const getFileIcon = (fileName: string): string => {
  const ext = fileName.split('.').pop()?.toLowerCase()

  switch (ext) {
    case 'md':
    case 'markdown':
      return 'FileText'
    case 'txt':
      return 'File'
    case 'json':
      return 'FileJson'
    case 'pdf':
      return 'FileType'
    default:
      return 'File'
  }
}
