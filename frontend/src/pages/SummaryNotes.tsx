import { useState, useEffect, useRef } from 'react'
import { FileText, Clock, Trash2, RefreshCw, ChevronLeft, ChevronRight, Grid, Square, Search } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ConfirmationDialog from '../components/ConfirmationDialog'
import SummaryGrid from '../components/SummaryGrid'
import SearchFilters from '../components/SearchFilters'
import { apiFetch } from '../utils/api'
import { SummaryNote, SummaryPaginationInfo, SummaryContentResponse, SummaryViewMode, SummarySearchFilters } from '../types'

// TypeScript interface for ReactMarkdown code component props

interface CodeComponentProps {
  node?: any
  inline?: boolean
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

interface SummaryListResponse {
  summaries: SummaryNote[]
  pagination: SummaryPaginationInfo
}

export default function SummaryNotes() {
  const [summaries, setSummaries] = useState<SummaryNote[]>([])
  const [pagination, setPagination] = useState<SummaryPaginationInfo>({
    current_page: 1,
    page_size: 1,
    total_count: 0,
    total_pages: 0,
    has_next: false,
    has_previous: false
  })
  const [viewMode, setViewMode] = useState<SummaryViewMode>('single')
  const [searchFilters, setSearchFilters] = useState<SummarySearchFilters>({
    searchTerm: '',
    sortBy: 'newest'
  })
  const [isFiltersExpanded, setIsFiltersExpanded] = useState(false)
  const [isSearchVisible, setIsSearchVisible] = useState(false)
  const [allSummaries, setAllSummaries] = useState<SummaryNote[]>([])
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
            fetchSummaries(pagination.current_page, viewMode, searchFilters)
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

  const fetchSummaries = async (page: number = pagination.current_page, mode: SummaryViewMode = viewMode, filters: SummarySearchFilters = searchFilters) => {
    try {
      setLoading(true)
      const pageSize = mode === 'single' ? 1 : 12 // Show 12 summaries in grid view
      
      // For filtering, we need to fetch more data to ensure we have enough results
      // We'll fetch a larger page size and handle pagination client-side for filtered results
      const fetchSize = (filters.searchTerm || filters.dateRange) ? 100 : pageSize
      const fetchPage = (filters.searchTerm || filters.dateRange) ? 1 : page
      
      const response = await apiFetch(`/api/summary-notes/?page=${fetchPage}&page_size=${fetchSize}`)
      const data: SummaryListResponse = await response.json()
      
      // Apply client-side filtering
      const filteredSummaries = applyFilters(data.summaries, filters)
      
      // Handle pagination of filtered results
      let displaySummaries: SummaryNote[]
      let paginationInfo: SummaryPaginationInfo
      
      if (filters.searchTerm || filters.dateRange) {
        // Client-side pagination for filtered results
        const startIndex = (page - 1) * pageSize
        const endIndex = startIndex + pageSize
        displaySummaries = filteredSummaries.slice(startIndex, endIndex)
        
        paginationInfo = {
          current_page: page,
          page_size: pageSize,
          total_count: filteredSummaries.length,
          total_pages: Math.ceil(filteredSummaries.length / pageSize),
          has_next: page < Math.ceil(filteredSummaries.length / pageSize),
          has_previous: page > 1
        }
      } else {
        // Server-side pagination for non-filtered results
        displaySummaries = filteredSummaries
        paginationInfo = data.pagination
      }
      
      setSummaries(displaySummaries)
      setPagination(paginationInfo)
      
      // Only load individual content in single view mode
      if (mode === 'single' && displaySummaries.length > 0) {
        await fetchSummaryContent(displaySummaries[0].filename)
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

  const applyFilters = (summariesList: SummaryNote[], filters: SummarySearchFilters): SummaryNote[] => {
    let filtered = [...summariesList]

    // Apply search filter
    if (filters.searchTerm) {
      const searchTerm = filters.searchTerm.toLowerCase()
      filtered = filtered.filter(summary => 
        summary.title.toLowerCase().includes(searchTerm) ||
        summary.preview.toLowerCase().includes(searchTerm)
      )
    }

    // Apply date range filter
    if (filters.dateRange?.start || filters.dateRange?.end) {
      filtered = filtered.filter(summary => {
        const summaryDate = new Date(summary.timestamp)
        const startDate = filters.dateRange?.start ? new Date(filters.dateRange.start) : null
        const endDate = filters.dateRange?.end ? new Date(filters.dateRange.end) : null
        
        if (startDate && summaryDate < startDate) return false
        if (endDate && summaryDate > endDate) return false
        return true
      })
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (filters.sortBy) {
        case 'oldest':
          return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        case 'word_count':
          return b.word_count - a.word_count
        case 'newest':
        default:
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      }
    })

    return filtered
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
      fetchSummaries(newPage, viewMode, searchFilters)
    }
  }

  const handleViewModeChange = async (newMode: SummaryViewMode) => {
    setViewMode(newMode)
    // Reset to first page when changing view modes
    await fetchSummaries(1, newMode, searchFilters)
  }

  const handleFiltersChange = async (newFilters: SummarySearchFilters) => {
    setSearchFilters(newFilters)
    // Reset to first page when filters change
    await fetchSummaries(1, viewMode, newFilters)
    
    // Auto-show search when filters are applied
    const hasActiveFilters = newFilters.searchTerm || newFilters.dateRange || newFilters.sortBy !== 'newest'
    if (hasActiveFilters && !isSearchVisible) {
      setIsSearchVisible(true)
    }
  }

  const handleViewSummary = async (filename: string) => {
    if (viewMode === 'grid') {
      // Switch to single view and load the specific summary
      setViewMode('single')
      setCurrentSummaryContent(null)
      await fetchSummaryContent(filename)
      // Find which page this summary would be on in single view
      const summaryIndex = summaries.findIndex(s => s.filename === filename)
      if (summaryIndex !== -1) {
        await fetchSummaries(summaryIndex + 1, 'single')
      }
    } else {
      await fetchSummaryContent(filename)
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
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
        <div className="flex items-center">
          <FileText className="h-6 w-6 text-gray-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Obby Summary</h1>
            <p className="text-gray-600">Individual AI-generated summaries with pagination</p>
          </div>
        </div>
        
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center space-y-3 sm:space-y-0 sm:space-x-4">
          {/* Search Toggle Button */}
          <button
            onClick={() => setIsSearchVisible(!isSearchVisible)}
            className={`flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-all duration-200 ${
              isSearchVisible || searchFilters.searchTerm || searchFilters.dateRange || searchFilters.sortBy !== 'newest'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
            }`}
            title={isSearchVisible ? "Hide Search" : "Show Search"}
          >
            <Search className={`h-4 w-4 mr-1 sm:mr-2 transition-transform duration-200 ${
              isSearchVisible ? 'rotate-90' : 'rotate-0'
            }`} />
            <span className="hidden sm:inline">Search</span>
            {(searchFilters.searchTerm || searchFilters.dateRange || searchFilters.sortBy !== 'newest') && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-white text-blue-600 rounded-full font-medium">
                !
              </span>
            )}
          </button>

          {/* View Mode Toggle */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleViewModeChange('single')}
              className={`flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'single'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
              }`}
            >
              <Square className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">Single View</span>
              <span className="sm:hidden">Single</span>
            </button>
            <button
              onClick={() => handleViewModeChange('grid')}
              className={`flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'grid'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
              }`}
            >
              <Grid className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">Grid View</span>
              <span className="sm:hidden">Grid</span>
            </button>
          </div>
          
          <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
            <button
              onClick={() => fetchSummaries()}
              disabled={loading}
              className="btn-secondary flex items-center justify-center"
            >
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
              )}
              Refresh
            </button>
            
            <div className={`flex items-center justify-center space-x-2 px-3 py-2 rounded-md ${
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
      </div>

      {/* Stats and Navigation - Different for single vs grid view */}
      {viewMode === 'grid' ? (
        /* Simple stats for grid view */
        <div className="flex items-center justify-center space-x-6 py-2 px-4 bg-gray-50 rounded-md text-xs text-gray-500">
          <div className="flex items-center space-x-1.5">
            <FileText className="h-3.5 w-3.5" />
            <span>{pagination.total_count} total</span>
          </div>
        </div>
      ) : (
        /* Summary navigation for single view */
        pagination.total_count > 1 && (
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
        )
      )}

      {/* Search and Filter Controls - Only show when search is visible */}
      <div className={`transition-all duration-300 ease-in-out ${
        isSearchVisible ? 'opacity-100 max-h-96 mb-6' : 'opacity-0 max-h-0 overflow-hidden'
      }`}>
        <SearchFilters
          filters={searchFilters}
          onFiltersChange={handleFiltersChange}
          isExpanded={isFiltersExpanded}
          onToggleExpanded={() => setIsFiltersExpanded(!isFiltersExpanded)}
        />
      </div>

      {/* Content Area - Conditional based on view mode */}
      {viewMode === 'grid' ? (
        <SummaryGrid
          summaries={summaries}
          pagination={pagination}
          loading={loading}
          onPageChange={handlePageChange}
          onViewSummary={handleViewSummary}
          onDeleteSummary={(filename) => {
            setSelectedSummary(filename)
            setDeleteDialogOpen(true)
          }}
          selectedSummary={selectedSummary}
        />
      ) : (
        /* Single Summary Display */
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : currentSummaryContent ? (
            <div className="card">
              {/* Summary Content */}
              {contentLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <>
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

                  {/* Delete button - subtle within container */}
                  <div className="flex justify-end mt-3">
                    <button
                      onClick={() => {
                        setSelectedSummary(currentSummaryContent.filename)
                        setDeleteDialogOpen(true)
                      }}
                      className="flex items-center px-2 py-1 text-xs font-medium text-gray-500 rounded-md hover:bg-red-50 hover:text-red-600 transition-colors"
                      title="Delete summary"
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      <span className="hidden sm:inline">Delete</span>
                    </button>
                  </div>
                </>
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
        </div>
      )}

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