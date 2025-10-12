import { useState, useEffect, useRef, type ReactNode } from 'react'
import { FileText, Trash2, ChevronLeft, ChevronRight, Grid, Square, Search, Zap, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ConfirmationDialog from '../components/ConfirmationDialog'
import SummaryGrid from '../components/SummaryGrid'
import SearchFilters from '../components/SearchFilters'
import SearchResultsPopup from '../components/SearchResultsPopup'
import { 
  apiFetch, 
  triggerComprehensiveSummaryGeneration, 
  getComprehensiveSummaryStatus,
  type ComprehensiveStatusResponse
} from '../utils/api'
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

type GenerationStatusPhase = 'idle' | 'starting' | 'running'

interface GenerationStatusStep {
  id: string
  label: string
  detail: string | null
  timestamp: string | null
}

interface GenerationStatusState {
  phase: GenerationStatusPhase
  currentMessage: string
  details: string | null
  progress: number | null
  steps: GenerationStatusStep[]
}

export default function SummaryNotes() {
  const [summaries, setSummaries] = useState<SummaryNote[]>([])
  const [pagination, setPagination] = useState<SummaryPaginationInfo>({
    current_page: 1,
    page_size: 12,
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
  
  // Summary generation state
  const [generateLoading, setGenerateLoading] = useState(false)
  const [generateSuccess, setGenerateSuccess] = useState<string | null>(null)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [generationStatus, setGenerationStatus] = useState<GenerationStatusState>({
    phase: 'idle',
    currentMessage: '',
    details: null,
    progress: null,
    steps: []
  })
  
  // Search popup state (for single view)
  const [searchPopupOpen, setSearchPopupOpen] = useState(false)
  const [allSearchResults, setAllSearchResults] = useState<SummaryNote[]>([])
  const [searchResultsLoading, setSearchResultsLoading] = useState(false)
  
  const eventSourceRef = useRef<EventSource | null>(null)
  const pollIntervalRef = useRef<number | null>(null)
  const statusStepCounterRef = useRef(0)

  const createStatusStep = (label: string, detail: string | null = null): GenerationStatusStep => {
    statusStepCounterRef.current += 1
    return {
      id: `local-step-${statusStepCounterRef.current}`,
      label,
      detail,
      timestamp: new Date().toISOString()
    }
  }

  const clampProgress = (value: number | null | undefined): number | null => {
    if (typeof value !== 'number' || Number.isNaN(value)) return null
    const clamped = Math.max(0, Math.min(1, value))
    return Number(clamped.toFixed(2))
  }

  const progressToPercent = (value: number): number =>
    Math.min(100, Math.max(0, Math.round(value * 100)))

  const mapStatusResponseToState = (
    status: ComprehensiveStatusResponse,
    prev: GenerationStatusState
  ): GenerationStatusState => {
    const history = status.history ?? []
    const stepsFromServer: GenerationStatusStep[] = history.map((entry, index) => {
      const label =
        typeof entry.message === 'string' && entry.message.trim().length > 0
          ? entry.message
          : entry.step || 'Processing…'
      const detail =
        typeof entry.details === 'string' && entry.details.trim().length > 0
          ? entry.details
          : null
      const timestamp = entry.timestamp ?? null
      const identifier =
        timestamp && entry.step
          ? `${timestamp}-${entry.step}`
          : timestamp || `${entry.step || 'step'}-${index}`

      return {
        id: identifier,
        label,
        detail,
        timestamp
      }
    })

    const current = status.status
    const messageFromCurrent =
      typeof current?.message === 'string' && current.message.trim().length > 0
        ? current.message
        : null
    const detailsFromCurrent =
      typeof current?.details === 'string' && current.details.trim().length > 0
        ? current.details
        : null
    const progress = clampProgress(current?.progress)

    const effectiveSteps =
      stepsFromServer.length > 0 ? stepsFromServer : status.running ? prev.steps : []

    const currentMessage =
      messageFromCurrent ??
      (effectiveSteps.length > 0
        ? effectiveSteps[effectiveSteps.length - 1].label
        : status.running
          ? prev.currentMessage || 'Summary generation in progress…'
          : '')

    const currentDetails =
      detailsFromCurrent ?? (status.running ? prev.details : null)

    const effectiveProgress =
      progress !== null ? progress : status.running ? prev.progress : null

    return {
      phase: status.running ? 'running' : 'idle',
      currentMessage,
      details: currentDetails,
      progress: effectiveProgress,
      steps: effectiveSteps
    }
  }

  const formatStatusTimestamp = (timestamp: string | null): string | null => {
    if (!timestamp) return null
    const date = new Date(timestamp)
    if (Number.isNaN(date.getTime())) return null
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

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
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
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
      console.log(`Fetching summary content for: ${filename}`)
      const response = await apiFetch(`/api/summary-notes/${filename}`)
      
      if (!response.ok) {
        // Try to get detailed error message
        let errText = `HTTP ${response.status}`
        try {
          const err = await response.json()
          errText = err?.error || errText
          console.error(`Failed to load ${filename}: ${response.status} - ${errText}`)
        } catch {
          // If JSON parsing fails, try to get text
          try {
            const textError = await response.text()
            errText = textError || errText
            console.error(`Failed to load ${filename}: ${response.status} - ${errText}`)
          } catch {}
        }
        throw new Error(errText)
      }
      
      const data: SummaryContentResponse = await response.json()
      console.log(`Successfully loaded summary: ${filename}`)
      setCurrentSummaryContent(data)
    } catch (error) {
      console.error('Error fetching summary content:', error, 'filename:', filename)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      alert(`Failed to load summary content: ${errorMsg}`)
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

  const handleSummaryGeneration = async () => {
    try {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }

      setGenerateLoading(true)
      setGenerateError(null)
      setGenerateSuccess(null)

      const initialStep = createStatusStep(
        'Preparing comprehensive summary request…',
        'Sending request to the monitoring service.'
      )

      setGenerationStatus({
        phase: 'starting',
        currentMessage: initialStep.label,
        details: initialStep.detail,
        progress: 0.05,
        steps: [initialStep]
      })
      
      console.log('Triggering comprehensive summary generation (async)...')
      const result = await triggerComprehensiveSummaryGeneration(true)
      
      // Treat 202 Accepted or accepted:true as an in-progress success
      const accepted = result?.accepted === true || (result?.success === true && !result?.result?.processed)
      if (accepted) {
        setGenerateSuccess('Summary generation started. Follow the status feed below.')
        const acceptedStep = createStatusStep(
          'Summary generation job accepted.',
          'Background worker is analyzing recent changes.'
        )
        setGenerationStatus(prev => ({
          phase: 'running',
          currentMessage: 'Summary generation has started. Monitoring progress…',
          details: acceptedStep.detail,
          progress: clampProgress((prev.progress ?? 0) + 0.05) ?? 0.1,
          steps: [...prev.steps, acceptedStep]
        }))
        
        let pollCount = 0
        const maxPolls = 20 // Poll for up to ~60 seconds
        pollIntervalRef.current = window.setInterval(async () => {
          try {
            const status = await getComprehensiveSummaryStatus()

            if (status.running) {
              setGenerationStatus(prev => mapStatusResponseToState(status, prev))
            } else if (status.last) {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
              }
              setGenerateLoading(false)
              setGenerationStatus({
                phase: 'idle',
                currentMessage: '',
                details: null,
                progress: null,
                steps: []
              })
              
              if (status.last.success) {
                setGenerateSuccess('Summary generated successfully!')
                // Refresh summaries list
                await fetchSummaries()
              } else {
                setGenerateError(status.last.message || 'Generation failed')
              }
              
              setTimeout(() => {
                setGenerateSuccess(null)
                setGenerateError(null)
              }, 5000)
              return
            }
            
            pollCount++
            if (pollCount >= maxPolls) {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
              }
              setGenerateLoading(false)
              setGenerationStatus({
                phase: 'idle',
                currentMessage: '',
                details: null,
                progress: null,
                steps: []
              })
              setGenerateSuccess('Generation is taking longer than expected. Check back soon.')
              setTimeout(() => setGenerateSuccess(null), 5000)
              return
            }
          } catch (error) {
            console.error('Error polling comprehensive status:', error)
            setGenerationStatus(prev => {
              if (prev.phase !== 'running') {
                return prev
              }
              const detailMessage =
                error instanceof Error
                  ? error.message
                  : 'Encountered a polling issue, retrying…'
              return {
                ...prev,
                currentMessage: prev.currentMessage || 'Summary generation in progress…',
                details: detailMessage
              }
            })
          }
        }, 3000) // Poll every 3 seconds
        
        return
      }
      
      if (result?.success && result?.result?.processed) {
        setGenerationStatus({
          phase: 'idle',
          currentMessage: '',
          details: null,
          progress: null,
          steps: []
        })
        setGenerateLoading(false)
        setGenerateSuccess('Summary generated successfully!')
        await fetchSummaries()
        setTimeout(() => setGenerateSuccess(null), 5000)
      } else {
        setGenerationStatus({
          phase: 'idle',
          currentMessage: '',
          details: null,
          progress: null,
          steps: []
        })
        setGenerateLoading(false)
        setGenerateError(result?.message || 'Failed to generate summary')
        setTimeout(() => setGenerateError(null), 8000)
      }
    } catch (error) {
      console.error('Error generating summary:', error)
      setGenerationStatus({
        phase: 'idle',
        currentMessage: '',
        details: null,
        progress: null,
        steps: []
      })
      setGenerateLoading(false)
      setGenerateError(error instanceof Error ? error.message : 'Failed to generate summary. Please try again.')
      setTimeout(() => setGenerateError(null), 8000)
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
              <h1 className="text-2xl font-bold text-gray-900">Summary</h1>
              <p className="text-gray-600">Error loading component</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="text-center py-12">
            <p className="text-red-600">Something went wrong loading the Summary page.</p>
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
    <div className="min-h-screen">
      {/* Modern Header */}
      <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
      }}>
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

        <div className="relative z-10">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-6 lg:space-y-0">
            <div className="space-y-2">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <FileText className="h-6 w-6" />
                </div>
                <h1 className="text-3xl font-bold tracking-tight">Summary Notes</h1>
              </div>
              <p className="text-blue-100 text-lg">AI-powered insights from your file changes</p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Connection Status */}
              <div className={`flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border transition-all duration-300 ${
                isConnected
                  ? 'bg-green-500/20 border-green-400/30 text-green-100'
                  : 'bg-red-500/20 border-red-400/30 text-red-100'
              }`}>
                <div className={`w-2 h-2 rounded-full animate-pulse ${
                  isConnected ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
                <span className="text-sm font-medium">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              {/* Generate Summary Button - Keep the gradient! */}
              <button
                onClick={handleSummaryGeneration}
                disabled={loading || generateLoading || generationStatus.phase !== 'idle'}
                className="relative overflow-hidden px-6 py-3 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 hover:shadow-xl hover:scale-105"
                title="Generate comprehensive summary of all changes since last summary"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                <div className="relative flex items-center space-x-2">
                  {generateLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                      <span>Generating...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4" />
                      <span>Generate Summary</span>
                    </>
                  )}
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Control Bar */}
      <div className="group relative overflow-hidden rounded-2xl p-6 mb-6 shadow-lg border transition-all duration-300" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-primary) 3%, var(--color-accent) 3%)'
        }}></div>
        
        <div className="relative flex flex-col sm:flex-row sm:items-center gap-4">
          {/* Left side controls */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Search Toggle Button */}
            <button
              onClick={() => setIsSearchVisible(!isSearchVisible)}
              className={`relative overflow-hidden flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 ${
                isSearchVisible || searchFilters.searchTerm || searchFilters.dateRange || searchFilters.sortBy !== 'newest'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
              }`}
              title={isSearchVisible ? "Hide Search" : "Show Search"}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
              <div className="relative flex items-center">
                <Search className={`h-4 w-4 mr-2 transition-transform duration-200 ${
                  isSearchVisible ? 'rotate-90' : 'rotate-0'
                }`} />
                <span>Search</span>
                {(searchFilters.searchTerm || searchFilters.dateRange || searchFilters.sortBy !== 'newest') && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-white text-blue-600 rounded-full font-bold">
                    •
                  </span>
                )}
              </div>
            </button>

            {/* View Mode Toggle */}
            <div className="flex items-center space-x-2 p-1 rounded-xl" style={{ backgroundColor: 'var(--color-surface)' }}>
              <button
                onClick={() => handleViewModeChange('single')}
                className={`flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 ${
                  viewMode === 'single'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Square className="h-4 w-4 mr-2" />
                <span>Single</span>
              </button>
              <button
                onClick={() => handleViewModeChange('grid')}
                className={`flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 ${
                  viewMode === 'grid'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Grid className="h-4 w-4 mr-2" />
                <span>Grid</span>
              </button>
            </div>
            
            {/* Refresh Button */}
            <button
              onClick={() => fetchSummaries()}
              disabled={loading}
              className="relative overflow-hidden flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 text-gray-700 bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
              <div className="relative flex items-center">
                {loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                ) : (
                  <FileText className="h-4 w-4 mr-2" />
                )}
                Refresh
              </div>
            </button>
          </div>

          {/* Right side controls */}
          <div className="flex flex-wrap items-center gap-3 sm:ml-auto">
            {/* Select Mode Toggle - Only show in grid view */}
            {viewMode === 'grid' && (
              <button
                onClick={handleToggleSelectMode}
                className={`relative overflow-hidden flex items-center justify-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 ${
                  isSelectMode
                    ? 'bg-green-600 text-white shadow-lg'
                    : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
                }`}
                title={isSelectMode ? "Exit Select Mode" : "Select Multiple"}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                <div className="relative flex items-center">
                  <Trash2 className="h-4 w-4 mr-2" />
                  <span>{isSelectMode ? 'Cancel' : 'Select'}</span>
                  {selectedItems.size > 0 && (
                    <span className="ml-2 px-2 py-0.5 text-xs bg-white text-green-600 rounded-full font-bold">
                      {selectedItems.size}
                    </span>
                  )}
                </div>
              </button>
            )}

            {/* Summary Count Badge */}
            <div className="flex items-center px-4 py-2 rounded-xl shadow-sm" style={{
              backgroundColor: 'var(--color-info)',
              color: 'var(--color-text-inverse)'
            }}>
              <FileText className="h-4 w-4 mr-2" />
              <span className="text-sm font-semibold">{pagination.total_count} {pagination.total_count === 1 ? 'Summary' : 'Summaries'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Generation Status Area - Modern Design */}
      {generationStatus.phase !== 'idle' && (
        <div className="group relative overflow-hidden rounded-2xl p-6 mb-6 shadow-xl border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
          borderColor: '#60a5fa'
        }}>
          <div className="absolute inset-0 opacity-50" style={{
            background: 'radial-gradient(circle at top right, #60a5fa20, transparent)'
          }}></div>
          
          <div className="relative flex">
            <div className="flex-shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl shadow-lg" style={{
                background: 'linear-gradient(135deg, #3b82f6, #2563eb)'
              }}>
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-white/30 border-t-white"></div>
              </div>
            </div>
            <div className="ml-4 flex-1">
              <div className="flex items-start justify-between mb-2">
                <p className="text-base font-bold text-blue-900">
                  {generationStatus.currentMessage || 'Summary generation in progress…'}
                </p>
                {generationStatus.progress !== null && (
                  <span className="text-sm font-bold px-3 py-1 rounded-full" style={{
                    background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                    color: 'white'
                  }}>
                    {progressToPercent(generationStatus.progress)}%
                  </span>
                )}
              </div>
              {generationStatus.details && (
                <p className="text-sm text-blue-800 mt-2">
                  {generationStatus.details}
                </p>
              )}
              {generationStatus.progress !== null && (
                <div className="mt-4 h-3 w-full overflow-hidden rounded-full shadow-inner" style={{
                  backgroundColor: '#bfdbfe'
                }}>
                  <div
                    className="h-full rounded-full transition-all duration-500 shadow-md"
                    style={{ 
                      width: `${progressToPercent(generationStatus.progress)}%`,
                      background: 'linear-gradient(90deg, #3b82f6, #2563eb, #1d4ed8)'
                    }}
                  />
                </div>
              )}
              {generationStatus.steps.length > 0 && (
                <ul className="mt-4 space-y-3">
                  {generationStatus.steps.map(step => {
                    const formattedTime = formatStatusTimestamp(step.timestamp)
                    return (
                      <li key={step.id} className="flex items-start p-3 rounded-xl backdrop-blur-sm" style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.5)'
                      }}>
                        <span className="mt-1.5 mr-3 h-2.5 w-2.5 rounded-full shadow-sm" style={{
                          backgroundColor: '#3b82f6'
                        }}></span>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-blue-900">{step.label}</p>
                          {step.detail && (
                            <p className="text-xs text-blue-700 mt-1">{step.detail}</p>
                          )}
                          {formattedTime && (
                            <p className="text-xs text-blue-600 mt-1 flex items-center">
                              <Clock className="h-3 w-3 mr-1" />
                              {formattedTime}
                            </p>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Success Message - Modern Design */}
      {generateSuccess && (
        <div className="group relative overflow-hidden rounded-2xl p-6 mb-6 shadow-xl border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
          borderColor: '#4ade80'
        }}>
          <div className="absolute inset-0 opacity-50" style={{
            background: 'radial-gradient(circle at top right, #4ade8020, transparent)'
          }}></div>
          <div className="relative flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl shadow-lg" style={{
                background: 'linear-gradient(135deg, #22c55e, #16a34a)'
              }}>
                <CheckCircle className="h-6 w-6 text-white" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-base font-bold text-green-900">
                {generateSuccess}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error Message - Modern Design */}
      {generateError && (
        <div className="group relative overflow-hidden rounded-2xl p-6 mb-6 shadow-xl border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
          borderColor: '#f87171'
        }}>
          <div className="absolute inset-0 opacity-50" style={{
            background: 'radial-gradient(circle at top right, #f8717120, transparent)'
          }}></div>
          <div className="relative flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl shadow-lg" style={{
                background: 'linear-gradient(135deg, #ef4444, #dc2626)'
              }}>
                <AlertCircle className="h-6 w-6 text-white" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-base font-bold text-red-900">
                {generateError}
              </p>
            </div>
          </div>
        </div>
      )}


      {/* Stats and Navigation - Modern Design */}
      {viewMode === 'single' && pagination.total_count > 1 && (
        <div className="group relative overflow-hidden rounded-2xl p-6 mb-6 shadow-lg border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-info) 3%, var(--color-primary) 3%)'
          }}></div>
          
          <div className="relative flex items-center justify-between">
            <button
              onClick={() => handlePageChange(pagination.current_page - 1)}
              disabled={!pagination.has_previous}
              className="group/btn relative overflow-hidden flex items-center px-5 py-3 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0" style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)'
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></div>
              <ChevronLeft className="h-5 w-5 mr-2 relative" />
              <span className="relative">Previous</span>
            </button>
            
            <div className="text-center px-6">
              <p className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                Summary {pagination.current_page} of {pagination.total_count}
              </p>
              <p className="text-xs mt-1 px-3 py-1 rounded-full inline-block" style={{
                color: 'var(--color-text-secondary)',
                backgroundColor: 'var(--color-surface)'
              }}>
                {currentSummaryContent?.filename}
              </p>
            </div>
            
            <button
              onClick={() => handlePageChange(pagination.current_page + 1)}
              disabled={!pagination.has_next}
              className="group/btn relative overflow-hidden flex items-center px-5 py-3 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0" style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)'
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></div>
              <span className="relative">Next</span>
              <ChevronRight className="h-5 w-5 ml-2 relative" />
            </button>
          </div>
        </div>
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
        /* Single Summary Display - Modern Design */
        <div className="space-y-6">
          {loading ? (
            <div className="group relative overflow-hidden rounded-2xl p-16 shadow-lg border transition-all duration-300" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <div className="flex flex-col items-center justify-center">
                <div className="relative">
                  <div className="absolute inset-0 rounded-full" style={{
                    background: 'radial-gradient(circle, var(--color-primary)30, transparent)'
                  }}></div>
                  <div className="animate-spin rounded-full h-16 w-16 border-4 border-t-transparent" style={{
                    borderColor: 'var(--color-primary)',
                    borderTopColor: 'transparent'
                  }}></div>
                </div>
                <p className="mt-4 text-lg font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
                  Loading summaries...
                </p>
              </div>
            </div>
          ) : currentSummaryContent ? (
            <div className="group relative overflow-hidden rounded-2xl p-8 shadow-xl border transition-all duration-300 hover:shadow-2xl" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{
                background: 'radial-gradient(circle at top right, var(--color-primary)08, transparent)'
              }}></div>
              
              {/* Summary Content */}
              {contentLoading ? (
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-transparent mb-4" style={{
                    borderColor: 'var(--color-primary)',
                    borderTopColor: 'transparent'
                  }}></div>
                  <p className="text-base font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
                    Loading summary content...
                  </p>
                </div>
              ) : (
                <>
                  <div className="relative prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-ul:mt-2 prose-li:my-1 marker:text-gray-500">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{ code: CodeBlock }}
                    >
                      {currentSummaryContent.content}
                    </ReactMarkdown>
                  </div>

                  {/* Delete button - modern style */}
                  <div className="relative flex justify-end mt-6 pt-6" style={{
                    borderTop: `1px solid var(--color-divider)`
                  }}>
                    <button
                      onClick={() => {
                        setSelectedSummary(currentSummaryContent.filename)
                        setDeleteDialogOpen(true)
                      }}
                      className="group/del relative overflow-hidden flex items-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                      title="Delete summary"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/40 to-white/0 translate-x-[-100%] group-hover/del:translate-x-[100%] transition-transform duration-700"></div>
                      <Trash2 className="h-4 w-4 mr-2 relative" />
                      <span className="relative">Delete Summary</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : pagination.total_count > 0 ? (
            <div className="group relative overflow-hidden rounded-2xl p-16 shadow-lg border transition-all duration-300" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <div className="flex flex-col items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-transparent mb-4" style={{
                  borderColor: 'var(--color-primary)',
                  borderTopColor: 'transparent'
                }}></div>
                <p className="text-base font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
                  Loading summary content...
                </p>
              </div>
            </div>
          ) : (
            <div className="group relative overflow-hidden rounded-2xl p-16 shadow-lg border transition-all duration-300" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <div className="absolute inset-0 opacity-50" style={{
                background: 'radial-gradient(circle at center, var(--color-info)10, transparent)'
              }}></div>
              <div className="relative text-center">
                <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl shadow-lg mb-6" style={{
                  background: 'linear-gradient(135deg, var(--color-info), var(--color-primary))'
                }}>
                  <FileText className="h-12 w-12 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                  No Summary Notes Yet
                </h3>
                <p className="text-base mb-6" style={{ color: 'var(--color-text-secondary)' }}>
                  AI-generated summaries will appear here as you make changes to your notes
                </p>
                <button
                  onClick={handleSummaryGeneration}
                  disabled={loading || generateLoading || generationStatus.phase !== 'idle'}
                  className="relative overflow-hidden px-6 py-3 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 hover:shadow-xl hover:scale-105 text-white"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                  <div className="relative flex items-center">
                    <Zap className="h-5 w-5 mr-2" />
                    <span>Generate Your First Summary</span>
                  </div>
                </button>
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
