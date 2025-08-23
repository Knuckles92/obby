import { useState, useEffect, useRef, type ReactNode } from 'react'
import { FileText, Trash2, ChevronLeft, ChevronRight, Grid, Square, Search, Zap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ConfirmationDialog from '../components/ConfirmationDialog'
import SummaryGrid from '../components/SummaryGrid'
import SearchFilters from '../components/SearchFilters'
import SearchResultsPopup from '../components/SearchResultsPopup'
import { apiFetch, triggerLivingNoteUpdate } from '../utils/api'
import { 
  SummaryNote, 
  SummaryPaginationInfo, 
  SummaryContentResponse, 
  SummaryViewMode, 
  SummarySearchFilters,
  BulkDeleteResponse,
  BulkDeleteRequest
} from '../types'

// Local props for the code renderer to avoid implicit any
interface MarkdownCodeProps {
  inline?: boolean
  className?: string
  children?: ReactNode
  [key: string]: unknown
}

// Code renderer for ReactMarkdown
const CodeBlock: any = ({ inline, className, children, ...props }: MarkdownCodeProps) => {
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
  const [loading, setLoading] = useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [selectedSummary, setSelectedSummary] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [currentSummaryContent, setCurrentSummaryContent] = useState<SummaryContentResponse | null>(null)
  const [contentLoading, setContentLoading] = useState(false)
  
  // Multi-select state
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [isSelectMode, setIsSelectMode] = useState(false)
  const [bulkDeleteLoading, setBulkDeleteLoading] = useState(false)
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false)
  
  // Manual summary generation state
  const [generateLoading, setGenerateLoading] = useState(false)
  const [generateSuccess, setGenerateSuccess] = useState<string | null>(null)
  const [generateError, setGenerateError] = useState<string | null>(null)
  
  // Search popup state (for single view)
  const [searchPopupOpen, setSearchPopupOpen] = useState(false)
  const [allSearchResults, setAllSearchResults] = useState<SummaryNote[]>([])
  const [searchResultsLoading, setSearchResultsLoading] = useState(false)
  
  const eventSourceRef = useRef<EventSource | null>(null)

  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const fetchAllSearchResults = async (filters: SummarySearchFilters) => {
    if (!filters.searchTerm) {
      setAllSearchResults([])
      return
    }
    
    try {
      setSearchResultsLoading(true)
      // Fetch a large number of results for the popup (not paginated)
      const params = new URLSearchParams()
      params.append('page', '1')
      params.append('page_size', '50') // Get more results for the popup
      params.append('search', filters.searchTerm)
      
      const response = await apiFetch(`/api/summary-notes/?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      let results = data.summaries || []
      
      // Apply client-side filtering for date range and sorting
      if (filters.dateRange?.start || filters.dateRange?.end) {
        results = results.filter((summary: SummaryNote) => {
          const summaryDate = new Date(summary.timestamp)
          const startDate = filters.dateRange?.start ? new Date(filters.dateRange.start) : null
          const endDate = filters.dateRange?.end ? new Date(filters.dateRange.end) : null
          
          if (startDate && summaryDate < startDate) return false
          if (endDate && summaryDate > endDate) return false
          return true
        })
      }
      
      // Apply sorting
      results.sort((a: SummaryNote, b: SummaryNote) => {
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
      
      setAllSearchResults(results)
    } catch (error) {
      console.error('Error fetching search results:', error)
      setAllSearchResults([])
    } finally {
      setSearchResultsLoading(false)
    }
  }

  const fetchSummaries = async (page: number = pagination.current_page, mode: SummaryViewMode = viewMode, filters: SummarySearchFilters = searchFilters) => {
    try {
      setLoading(true)
      const pageSize = mode === 'single' ? 1 : 12 // Show 12 summaries in grid view
      
      // Build API URL with search and pagination parameters
      const params = new URLSearchParams()
      params.append('page', page.toString())
      params.append('page_size', pageSize.toString())
      
      // Add search parameter if present
      if (filters.searchTerm) {
        params.append('search', filters.searchTerm)
      }
      
      const response = await apiFetch(`/api/summary-notes/?${params.toString()}`)
      if (!response.ok) {
        // Try to extract error message but don't fail if body isn't JSON
        let errText = `HTTP ${response.status}`
        try {
          const err = await response.json()
          errText = err?.error || errText
        } catch {}
        throw new Error(errText)
      }
      const raw = await response.json().catch(() => ({} as any))
      const data: SummaryListResponse = {
        summaries: Array.isArray(raw?.summaries) ? raw.summaries : [],
        pagination: raw?.pagination || {
          current_page: page,
          page_size: pageSize,
          total_count: Array.isArray(raw?.summaries) ? raw.summaries.length : 0,
          total_pages: Array.isArray(raw?.summaries) ? Math.ceil(raw.summaries.length / pageSize) : 0,
          has_next: false,
          has_previous: false
        }
      }
      
      // Apply only date range filtering client-side (search is handled by backend now)
      let filteredSummaries = data.summaries || []
      
      // Apply date range filter client-side if needed
      if (filters.dateRange?.start || filters.dateRange?.end) {
        filteredSummaries = filteredSummaries.filter(summary => {
          const summaryDate = new Date(summary.timestamp)
          const startDate = filters.dateRange?.start ? new Date(filters.dateRange.start) : null
          const endDate = filters.dateRange?.end ? new Date(filters.dateRange.end) : null
          
          if (startDate && summaryDate < startDate) return false
          if (endDate && summaryDate > endDate) return false
          return true
        })
      }

      // Apply sorting client-side
      filteredSummaries.sort((a, b) => {
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
      
      // For date filtering, we need client-side pagination
      let displaySummaries: SummaryNote[]
      let paginationInfo: SummaryPaginationInfo
      
      if (filters.dateRange?.start || filters.dateRange?.end) {
        // Client-side pagination for date-filtered results
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
        // Server-side pagination for search and normal results
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

  // Note: Search filtering is now handled by the backend API
  // This function is kept for legacy date range filtering only

  const fetchSummaryContent = async (filename: string) => {
    try {
      setContentLoading(true)
      const response = await apiFetch(`/api/summary-notes/${filename}`)
      if (!response.ok) {
        let errText = `HTTP ${response.status}`
        try {
          const err = await response.json()
          errText = err?.error || errText
        } catch {}
        throw new Error(errText)
      }
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

  // Multi-select handlers
  const handleToggleSelectMode = () => {
    setIsSelectMode(!isSelectMode)
    if (isSelectMode) {
      // Exiting select mode, clear selection
      setSelectedItems(new Set())
    }
  }

  const handleSelectItem = (filename: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(filename)) {
        newSet.delete(filename)
      } else {
        newSet.add(filename)
      }
      return newSet
    })
  }

  const handleSelectAll = () => {
    if (selectedItems.size === summaries.length) {
      // If all visible items are selected, clear selection
      setSelectedItems(new Set())
    } else {
      // Select all visible items on current page
      setSelectedItems(new Set(summaries.map(s => s.filename)))
    }
  }

  const handleClearSelection = () => {
    setSelectedItems(new Set())
  }

  const handleBulkDelete = async () => {
    if (selectedItems.size === 0) return

    try {
      setBulkDeleteLoading(true)
      const filenames = Array.from(selectedItems)
      
      const response = await apiFetch('/api/summary-notes/bulk', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filenames } as BulkDeleteRequest)
      })

      const result: BulkDeleteResponse = await response.json()
      
      if (response.ok || response.status === 207) { // 207 = Multi-Status (partial success)
        console.log('Bulk delete completed:', result)
        
        // Show summary of results
        if (result.summary.failed > 0) {
          alert(`Bulk delete completed: ${result.summary.succeeded} succeeded, ${result.summary.failed} failed`)
        } else {
          console.log(`Successfully deleted ${result.summary.succeeded} files`)
        }
        
        // Clear selection and refresh
        setSelectedItems(new Set())
        setIsSelectMode(false)
        
        // Refresh the current page or go to previous page if current page is empty
        const remainingOnPage = summaries.length - result.summary.succeeded
        const shouldGoToPrevious = pagination.current_page > 1 && remainingOnPage === 0
        
        if (shouldGoToPrevious) {
          await fetchSummaries(pagination.current_page - 1)
        } else {
          await fetchSummaries()
        }
        
        setBulkDeleteDialogOpen(false)
      } else {
        console.error('Bulk delete failed:', result.message)
        alert('Bulk delete failed: ' + result.message)
      }
    } catch (error) {
      console.error('Error during bulk delete:', error)
      alert('Failed to delete selected items. Please try again.')
    } finally {
      setBulkDeleteLoading(false)
    }
  }

  const handleManualSummaryGeneration = async () => {
    try {
      setGenerateLoading(true)
      setGenerateError(null)
      setGenerateSuccess(null)
      
      console.log('Triggering Living Note update...')
      const result = await triggerLivingNoteUpdate(true)
      
      if (result.success) {
        if (result.updated && result.individual_summary_created) {
          setGenerateSuccess('Living Note updated and new summary created successfully!')
          // Refresh the summaries list to show the new entry
          await fetchSummaries()
        } else if (result.updated) {
          setGenerateSuccess('Living Note updated successfully!')
        } else {
          setGenerateSuccess(result.message || 'No new changes to summarize')
        }
        
        // Clear success message after 5 seconds
        setTimeout(() => setGenerateSuccess(null), 5000)
      } else {
        setGenerateError(result.message || 'Failed to generate summaries')
        // Clear error message after 8 seconds
        setTimeout(() => setGenerateError(null), 8000)
      }
    } catch (error) {
      console.error('Error generating summaries:', error)
      setGenerateError(error instanceof Error ? error.message : 'Failed to generate summaries. Please try again.')
      // Clear error message after 8 seconds
      setTimeout(() => setGenerateError(null), 8000)
    } finally {
      setGenerateLoading(false)
    }
  }


  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      // Clear selection when changing pages
      setSelectedItems(new Set())
      fetchSummaries(newPage, viewMode, searchFilters)
    }
  }

  const handleViewModeChange = async (newMode: SummaryViewMode) => {
    setViewMode(newMode)
    // Clear selection and exit select mode when changing view modes
    setSelectedItems(new Set())
    setIsSelectMode(false)
    
    // Close search popup when switching to grid view
    if (newMode === 'grid') {
      setSearchPopupOpen(false)
    }
    
    // Reset to first page when changing view modes
    await fetchSummaries(1, newMode, searchFilters)
  }

  const handleFiltersChange = async (newFilters: SummarySearchFilters) => {
    setSearchFilters(newFilters)
    
    // Close popup if search term is cleared
    if (!newFilters.searchTerm) {
      setSearchPopupOpen(false)
      setAllSearchResults([])
    }
    
    // Reset to first page when filters change
    await fetchSummaries(1, viewMode, newFilters)
    
    // Auto-show search when filters are applied
    const hasActiveFilters = newFilters.searchTerm || newFilters.dateRange || newFilters.sortBy !== 'newest'
    if (hasActiveFilters && !isSearchVisible) {
      setIsSearchVisible(true)
    }
  }

  const handleSearchExecute = async (searchTerm: string) => {
    // Only show popup in single view mode when search is executed
    if (viewMode === 'single' && searchTerm.trim()) {
      const newSearchFilters = { ...searchFilters, searchTerm }
      await fetchAllSearchResults(newSearchFilters)
      setSearchPopupOpen(true)
    }
  }

  const handleSearchResultSelect = async (filename: string) => {
    // Find the selected summary in all search results or current summaries
    let targetSummary = allSearchResults.find(s => s.filename === filename)
    if (!targetSummary) {
      targetSummary = summaries.find(s => s.filename === filename)
    }
    
    if (targetSummary) {
      // Load the specific summary content
      await fetchSummaryContent(filename)
      
      // Find which page this summary would be on if we cleared the search
      // For now, just load it directly
      const params = new URLSearchParams()
      params.append('page', '1')
      params.append('page_size', '1')
      
      try {
        const response = await apiFetch(`/api/summary-notes/?${params.toString()}`)
        await response.json()
        // Update pagination to show we're viewing a specific item
        setPagination(prev => ({
          ...prev,
          current_page: 1
        }))
      } catch (error) {
        console.error('Error updating pagination:', error)
      }
    }
    
    // Close the popup
    setSearchPopupOpen(false)
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

  // (helpers removed: formatDate, formatFileSize) — unused

  // Keyboard shortcuts - placed after function definitions
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle shortcuts in grid view
      if (viewMode !== 'grid') return
      
      // Handle Escape key to exit selection mode
      if (event.key === 'Escape' && isSelectMode) {
        setIsSelectMode(false)
        setSelectedItems(new Set())
        return
      }
      
      // Handle Ctrl/Cmd + A to select all (only in select mode)
      if (event.key === 'a' && (event.ctrlKey || event.metaKey) && isSelectMode) {
        event.preventDefault()
        handleSelectAll()
        return
      }
      
      // Handle Delete key to trigger bulk delete (only when items are selected)
      if (event.key === 'Delete' && isSelectMode && selectedItems.size > 0) {
        event.preventDefault()
        setBulkDeleteDialogOpen(true)
        return
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [viewMode, isSelectMode, selectedItems])

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
            <p className="text-gray-600">AI-generated summaries of your file changes</p>
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

          {/* Select Mode Toggle - Only show in grid view */}
          {viewMode === 'grid' && (
            <button
              onClick={handleToggleSelectMode}
              className={`flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                isSelectMode
                  ? 'bg-green-600 text-white'
                  : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
              }`}
              title={isSelectMode ? "Exit Select Mode" : "Select Multiple"}
            >
              <Trash2 className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">{isSelectMode ? 'Cancel' : 'Select'}</span>
              {selectedItems.size > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-white text-green-600 rounded-full font-medium">
                  {selectedItems.size}
                </span>
              )}
            </button>
          )}

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
            
            <button
              onClick={handleManualSummaryGeneration}
              disabled={generateLoading || loading}
              className="btn-primary btn-gradient flex items-center justify-center"
              title="Generate comprehensive summaries for all recent file changes"
            >
              {generateLoading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              ) : (
                <Zap className="h-4 w-4 mr-2" />
              )}
              Generate Summary
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

      {/* Success/Error Messages for Manual Generation */}
      {generateSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <Zap className="h-5 w-5 text-green-400" />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-green-800">
                {generateSuccess}
              </p>
            </div>
          </div>
        </div>
      )}

      {generateError && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <div className="h-5 w-5 text-red-400">⚠</div>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800">
                {generateError}
              </p>
            </div>
          </div>
        </div>
      )}


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
          onSearchExecute={handleSearchExecute}
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
          isSelectMode={isSelectMode}
          selectedItems={selectedItems}
          onSelectItem={handleSelectItem}
          onSelectAll={handleSelectAll}
          onClearSelection={handleClearSelection}
          onBulkDelete={() => setBulkDeleteDialogOpen(true)}
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
                      components={{ code: CodeBlock }}
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

      {/* Bulk Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={bulkDeleteDialogOpen}
        onClose={() => {
          setBulkDeleteDialogOpen(false)
        }}
        onConfirm={handleBulkDelete}
        title="Delete Multiple Summaries"
        message={`Are you sure you want to delete ${selectedItems.size} selected ${selectedItems.size === 1 ? 'summary' : 'summaries'}? This action cannot be undone.`}
        confirmText={`Delete ${selectedItems.size} ${selectedItems.size === 1 ? 'File' : 'Files'}`}
        cancelText="Cancel"
        danger={true}
        loading={bulkDeleteLoading}
        extraWarning="All selected summary files will be permanently removed from your system."
      />

      {/* Search Results Popup (Single View Only) */}
      <SearchResultsPopup
        isOpen={searchPopupOpen && viewMode === 'single'}
        onClose={() => setSearchPopupOpen(false)}
        searchTerm={searchFilters.searchTerm}
        searchResults={allSearchResults}
        loading={searchResultsLoading}
        onSelectResult={handleSearchResultSelect}
      />
    </div>
  )
}