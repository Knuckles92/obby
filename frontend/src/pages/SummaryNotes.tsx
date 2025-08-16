import { useState, useEffect, useRef } from 'react'
import { FileText, Clock, Trash2, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ConfirmationDialog from '../components/ConfirmationDialog'
import { apiFetch } from '../utils/api'

// TypeScript interfaces
interface SummaryNote {
  filename: string
  timestamp: string
  title: string
  preview: string
  word_count: number
  created_time: string
  file_size: number
  last_modified: string
}

interface PaginationInfo {
  current_page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

interface SummaryListResponse {
  summaries: SummaryNote[]
  pagination: PaginationInfo
}

interface SummaryContentResponse {
  filename: string
  content: string
  timestamp: string
  title: string
  word_count: number
  created_time: string
  file_size: number
  last_modified: string
}

// TypeScript interface for ReactMarkdown code component props
interface CodeComponentProps {
  node?: any
  inline?: boolean
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

export default function SummaryNotes() {
  const [summaries, setSummaries] = useState<SummaryNote[]>([])
  const [pagination, setPagination] = useState<PaginationInfo>({
    current_page: 1,
    page_size: 1,
    total_count: 0,
    total_pages: 0,
    has_next: false,
    has_previous: false
  })
  const [loading, setLoading] = useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [selectedSummary, setSelectedSummary] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [currentSummaryContent, setCurrentSummaryContent] = useState<SummaryContentResponse | null>(null)
  const [contentLoading, setContentLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    try {
      fetchSummaries()
      connectToSSE()
    } catch (error) {
      console.error('Error initializing SummaryNotes component:', error)
      setLoading(false)
    }
    
    return () => {
      try {
        disconnectSSE()
      } catch (error) {
        console.error('Error disconnecting SSE:', error)
      }
    }
  }, [])

  const connectToSSE = () => {
    if (eventSourceRef.current) {
      return // Already connected
    }

    try {
      const eventSource = new EventSource('/api/summary-notes/events')
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        console.log('Connected to summary note updates')
        setIsConnected(true)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'summary_note_changed') {
            console.log('Summary note changed:', data.action, data.filename)
            // Refresh the current page when changes occur
            fetchSummaries()
          } else if (data.type === 'connected') {
            console.log('SSE connection established')
          }
        } catch (error) {
          console.error('Error parsing SSE message:', error)
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error)
        setIsConnected(false)
        
        if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
          disconnectSSE()
          setTimeout(() => {
            if (!eventSourceRef.current) {
              connectToSSE()
            }
          }, 10000)
        }
      }
    } catch (error) {
      console.error('Failed to establish SSE connection:', error)
      setIsConnected(false)
    }
  }

  const disconnectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
      setIsConnected(false)
    }
  }

  const fetchSummaries = async (page: number = pagination.current_page) => {
    try {
      setLoading(true)
      const response = await apiFetch(`/api/summary-notes/?page=${page}&page_size=1`)
      const data: SummaryListResponse = await response.json()
      setSummaries(data.summaries)
      setPagination(data.pagination)
      
      // Immediately load the content for the current summary
      if (data.summaries.length > 0) {
        await fetchSummaryContent(data.summaries[0].filename)
      } else {
        setCurrentSummaryContent(null)
      }
    } catch (error) {
      console.error('Error fetching summaries:', error)
      setHasError(true)
    } finally {
      setLoading(false)
    }
  }

  const fetchSummaryContent = async (filename: string) => {
    try {
      setContentLoading(true)
      const response = await apiFetch(`/api/summary-notes/${filename}`)
      const data: SummaryContentResponse = await response.json()
      setCurrentSummaryContent(data)
    } catch (error) {
      console.error('Error fetching summary content:', error)
      alert('Failed to load summary content')
    } finally {
      setContentLoading(false)
    }
  }

  const handleDeleteSummary = async () => {
    if (!selectedSummary) return

    try {
      setDeleteLoading(true)
      const response = await apiFetch(`/api/summary-notes/${selectedSummary}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        console.log('Summary deleted successfully')
        // Clear current content if we're deleting the currently displayed summary
        if (currentSummaryContent?.filename === selectedSummary) {
          setCurrentSummaryContent(null)
        }
        // Refresh the current page or go to previous page if this was the last item
        const shouldGoToPrevious = pagination.current_page > 1 && summaries.length === 1
        if (shouldGoToPrevious) {
          await fetchSummaries(pagination.current_page - 1)
        } else {
          await fetchSummaries()
        }
        setDeleteDialogOpen(false)
        setSelectedSummary(null)
      } else {
        const error = await response.json()
        console.error('Error deleting summary:', error.error)
        alert('Failed to delete summary: ' + error.error)
      }
    } catch (error) {
      console.error('Error deleting summary:', error)
      alert('Failed to delete summary. Please try again.')
    } finally {
      setDeleteLoading(false)
    }
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      fetchSummaries(newPage)
    }
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (hasError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <FileText className="h-6 w-6 text-gray-600 mr-3" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Obby Summary</h1>
              <p className="text-gray-600">Error loading component</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="text-center py-12">
            <p className="text-red-600">Something went wrong loading the Obby Summary page.</p>
            <button 
              onClick={() => {
                setHasError(false)
                window.location.reload()
              }}
              className="mt-4 btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <FileText className="h-6 w-6 text-gray-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Obby Summary</h1>
            <p className="text-gray-600">Individual AI-generated summaries with pagination</p>
          </div>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={() => fetchSummaries()}
            disabled={loading}
            className="btn-secondary flex items-center"
          >
            {loading && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
            )}
            Refresh
          </button>
          
          <div className={`flex items-center space-x-2 px-3 py-2 rounded-md ${
            isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            <div className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-sm font-medium">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-md">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Summaries</p>
              <p className="text-lg font-semibold text-gray-900">{pagination.total_count}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-md">
              <Clock className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Viewing</p>
              <p className="text-lg font-semibold text-gray-900">
                {pagination.current_page} of {pagination.total_count}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Single Summary Display */}
      <div className="space-y-4">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : currentSummaryContent ? (
          <div className="card">
            {/* Delete Button - Top Right */}
            <div className="flex justify-end mb-4">
              <button
                onClick={() => {
                  setSelectedSummary(currentSummaryContent.filename)
                  setDeleteDialogOpen(true)
                }}
                className="flex items-center px-3 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200 transition-colors"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete
              </button>
            </div>

            {/* Summary Content */}
            {contentLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              </div>
            ) : (
              <div className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-ul:mt-2 prose-li:my-1 marker:text-gray-500">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }: CodeComponentProps) {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-md !mt-0 !mb-4"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      )
                    }
                  }}
                >
                  {currentSummaryContent.content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        ) : pagination.total_count > 0 ? (
          <div className="card">
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading summary content...</p>
            </div>
          </div>
        ) : (
          <div className="card">
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No summary notes yet</p>
              <p className="text-sm text-gray-500 mt-2">
                AI-generated summaries will appear here as you make changes to your notes
              </p>
            </div>
          </div>
        )}
        
        {/* Navigation Controls */}
        {pagination.total_count > 1 && (
          <div className="card">
            <div className="flex items-center justify-between">
              <button
                onClick={() => handlePageChange(pagination.current_page - 1)}
                disabled={!pagination.has_previous}
                className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-5 w-5 mr-2" />
                Previous Summary
              </button>
              
              <div className="text-center">
                <p className="text-sm font-medium text-gray-900">
                  Summary {pagination.current_page} of {pagination.total_count}
                </p>
                <p className="text-xs text-gray-500">
                  {currentSummaryContent?.filename}
                </p>
              </div>
              
              <button
                onClick={() => handlePageChange(pagination.current_page + 1)}
                disabled={!pagination.has_next}
                className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next Summary
                <ChevronRight className="h-5 w-5 ml-2" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false)
          setSelectedSummary(null)
        }}
        onConfirm={handleDeleteSummary}
        title="Delete Summary"
        message={`Are you sure you want to delete this summary? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        danger={true}
        loading={deleteLoading}
        extraWarning="The summary file will be permanently removed from your system."
      />
    </div>
  )
}