import { useState, useEffect, useRef } from 'react'
import { FileText, Clock, BarChart3, Trash2, ChevronDown, ChevronRight, Tag, Search, Calendar, TrendingUp, List, Grid, Settings, Save, RefreshCw, Zap, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { LivingNote as LivingNoteType, LivingNoteSection, LivingNoteSettings } from '../types'
import ConfirmationDialog from '../components/ConfirmationDialog'
import { apiFetch, searchSemanticIndex } from '../utils/api'

// TypeScript interface for ReactMarkdown code component props
interface CodeComponentProps {
  node?: any
  inline?: boolean
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

interface ParsedSession {
  id: string
  title: string
  timestamp: string
  content: string
  metadata?: {
    topics?: string[]
    keywords?: string[]
    impact?: string
    changes?: number
    duration?: string
  }
}

interface ViewMode {
  type: 'traditional' | 'structured' | 'timeline'
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const VIEW_MODES: ViewMode[] = [
  { type: 'traditional', label: 'Traditional', icon: FileText },
  { type: 'structured', label: 'Structured', icon: Grid },
  { type: 'timeline', label: 'Timeline', icon: List }
]

const IMPACT_COLORS = {
  brief: 'bg-gray-100 text-gray-700 border-gray-200',
  moderate: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  significant: 'bg-red-100 text-red-700 border-red-200'
}

export default function LivingNote() {
  const [note, setNote] = useState<LivingNoteType>({
    content: '',
    lastUpdated: '',
    wordCount: 0
  })
  const [loading, setLoading] = useState(true)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [viewMode, setViewMode] = useState<'traditional' | 'structured' | 'timeline'>('traditional')
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState<LivingNoteSettings>({
    updateFrequency: 'realtime',
    summaryLength: 'moderate',
    writingStyle: 'technical',
    includeMetrics: true,
    autoUpdate: true,
    maxSections: 10,
    focusAreas: []
  })
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [newFocusArea, setNewFocusArea] = useState('')
  const [hasError, setHasError] = useState(false)
  const [manualUpdateLoading, setManualUpdateLoading] = useState(false)
  const [showManualUpdateOptions, setShowManualUpdateOptions] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const manualUpdateRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    try {
      fetchLivingNote()
      fetchSettings()
      connectToSSE()
    } catch (error) {
      console.error('Error initializing LivingNote component:', error)
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

  // Handle click outside for manual update dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (manualUpdateRef.current && !manualUpdateRef.current.contains(event.target as Node)) {
        setShowManualUpdateOptions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const connectToSSE = () => {
    if (eventSourceRef.current) {
      return // Already connected
    }

    try {
      const eventSource = new EventSource('/api/living-note/events')
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        console.log('Connected to living note updates')
        setIsConnected(true)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'living_note_updated') {
            setNote({
              content: data.content,
              lastUpdated: data.lastUpdated,
              wordCount: data.wordCount,
              metadata: data.metadata,
              sections: data.sections
            })
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
        
        // Don't attempt aggressive reconnection to avoid infinite loops
        if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
          disconnectSSE()
          // Only reconnect if not already attempting
          setTimeout(() => {
            if (!eventSourceRef.current) {
              connectToSSE()
            }
          }, 10000) // Increased delay to 10 seconds
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

  const fetchLivingNote = async () => {
    try {
      setLoading(true)
      const response = await apiFetch('/api/living-note')
      const data = await response.json()
      setNote(data)
    } catch (error) {
      console.error('Error fetching living note:', error)
      setHasError(true)
    } finally {
      setLoading(false)
    }
  }

  const fetchSettings = async () => {
    try {
      const response = await apiFetch('/api/living-note/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (error) {
      console.error('Error fetching settings:', error)
      // Keep default settings if fetch fails - don't set error state for this
    }
  }

  const saveSettings = async () => {
    try {
      setSettingsLoading(true)
      const response = await apiFetch('/api/living-note/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })
      
      if (response.ok) {
        console.log('Settings saved successfully')
      } else {
        console.error('Failed to save settings')
      }
    } catch (error) {
      console.error('Error saving settings:', error)
    } finally {
      setSettingsLoading(false)
    }
  }

  const addFocusArea = () => {
    if (newFocusArea.trim() && !settings.focusAreas.includes(newFocusArea.trim())) {
      setSettings({
        ...settings,
        focusAreas: [...settings.focusAreas, newFocusArea.trim()]
      })
      setNewFocusArea('')
    }
  }

  const removeFocusArea = (area: string) => {
    setSettings({
      ...settings,
      focusAreas: settings.focusAreas.filter(a => a !== area)
    })
  }

  const triggerManualUpdate = async () => {
    try {
      const response = await apiFetch('/api/living-note/update', {
        method: 'POST'
      })
      
      if (response.ok) {
        console.log('Manual update triggered')
      } else {
        console.error('Failed to trigger manual update')
      }
    } catch (error) {
      console.error('Error triggering manual update:', error)
    }
  }

  const triggerComprehensiveUpdate = async (updateType: 'quick' | 'full' | 'smart') => {
    setManualUpdateLoading(true)
    try {
      const response = await apiFetch('/api/living-note/manual-update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ type: updateType })
      })
      
      if (response.ok) {
        const result = await response.json()
        console.log(`Comprehensive ${updateType} update completed:`, result.message)
        setShowManualUpdateOptions(false)
      } else {
        const error = await response.json()
        console.error('Failed to trigger comprehensive update:', error.error)
      }
    } catch (error) {
      console.error('Error triggering comprehensive update:', error)
    } finally {
      setManualUpdateLoading(false)
    }
  }

  const handleClearNote = async () => {
    try {
      setClearLoading(true)
      const response = await apiFetch('/api/living-note/clear', {
        method: 'POST'
      })
      
      if (response.ok) {
        const result = await response.json()
        console.log(result.message)
        // Refresh the note content
        await fetchLivingNote()
        setClearDialogOpen(false)
      } else {
        const error = await response.json()
        console.error('Error clearing living note:', error.error)
        alert('Failed to clear living note: ' + error.error)
      }
    } catch (error) {
      console.error('Error clearing living note:', error)
      alert('Failed to clear living note. Please try again.')
    } finally {
      setClearLoading(false)
    }
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  // Parse structured markdown into sessions
  const parseStructuredContent = (content: string): ParsedSession[] => {
    if (!content) return []
    
    // Check if content has session structure
    const sessionPattern = /^## Session \d+: (.+?)\n\*\*Timestamp:\*\* (.+?)\n([\s\S]*?)(?=^## Session \d+:|$)/gm
    const sessions: ParsedSession[] = []
    let match
    
    while ((match = sessionPattern.exec(content)) !== null) {
      const [, title, timestamp, sessionContent] = match
      
      // Extract metadata from session content
      const metadata: ParsedSession['metadata'] = {}
      
      // Extract topics
      const topicsMatch = sessionContent.match(/\*\*Topics:\*\* (.+)/)
      if (topicsMatch) {
        metadata.topics = topicsMatch[1].split(', ').map(t => t.trim())
      }
      
      // Extract keywords
      const keywordsMatch = sessionContent.match(/\*\*Keywords:\*\* (.+)/)
      if (keywordsMatch) {
        metadata.keywords = keywordsMatch[1].split(', ').map(k => k.trim())
      }
      
      // Extract impact
      const impactMatch = sessionContent.match(/\*\*Impact:\*\* (\w+)/)
      if (impactMatch) {
        metadata.impact = impactMatch[1].toLowerCase()
      }
      
      // Extract changes count
      const changesMatch = sessionContent.match(/(\d+) changes?/)
      if (changesMatch) {
        metadata.changes = parseInt(changesMatch[1])
      }
      
      sessions.push({
        id: `session-${sessions.length + 1}`,
        title: title.trim(),
        timestamp: timestamp.trim(),
        content: sessionContent.trim(),
        metadata
      })
    }
    
    return sessions
  }

  // Check if content is structured format
  const isStructuredFormat = (content: string): boolean => {
    return content.includes('## Session') && content.includes('**Timestamp:**')
  }

  // Toggle session expansion
  const toggleSession = (sessionId: string) => {
    setExpandedSessions(prev => {
      const newSet = new Set(prev)
      if (newSet.has(sessionId)) {
        newSet.delete(sessionId)
      } else {
        newSet.add(sessionId)
      }
      return newSet
    })
  }

  // Handle topic/keyword click for search integration
  const handleTagClick = (type: 'topic' | 'keyword', value: string) => {
    setSearchQuery(`${type}:${value}`)
    setShowSearch(true)
  }

  // Get sessions from content
  const sessions = parseStructuredContent(note.content)
  const isStructured = isStructuredFormat(note.content)
  
  // Calculate additional stats for structured content
  const totalSessions = sessions.length
  const totalTopics = new Set(sessions.flatMap(s => s.metadata?.topics || [])).size
  const totalKeywords = new Set(sessions.flatMap(s => s.metadata?.keywords || [])).size

  if (hasError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <FileText className="h-6 w-6 text-gray-600 mr-3" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Living Note</h1>
              <p className="text-gray-600">Error loading component</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="text-center py-12">
            <p className="text-red-600">Something went wrong loading the Living Note page.</p>
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
            <h1 className="text-2xl font-bold text-gray-900">Living Note</h1>
            <p className="text-gray-600">AI-generated summary of your note changes</p>
          </div>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={fetchLivingNote}
            disabled={loading}
            className="btn-secondary flex items-center"
          >
            {loading && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
            )}
            Refresh
          </button>
          
          <div className="flex items-center space-x-4">
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
            
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                showSettings 
                  ? 'bg-primary-100 text-primary-700 border border-primary-200' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200'
              }`}
            >
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </button>
            
            {settings.updateFrequency === 'manual' && (
              <button
                onClick={triggerManualUpdate}
                className="flex items-center px-4 py-2 text-sm font-medium text-blue-700 bg-blue-100 rounded-md hover:bg-blue-200 transition-colors"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Update Now
              </button>
            )}

            {/* Comprehensive Manual Update Button - Always Available */}
            <div className="relative" ref={manualUpdateRef}>
              <button
                onClick={() => setShowManualUpdateOptions(!showManualUpdateOptions)}
                disabled={manualUpdateLoading}
                className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  manualUpdateLoading 
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                    : 'bg-purple-100 text-purple-700 hover:bg-purple-200 border border-purple-200'
                }`}
              >
                {manualUpdateLoading ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4 mr-2" />
                )}
                Manually Update Note
                {!manualUpdateLoading && (
                  showManualUpdateOptions ? 
                    <ChevronUp className="h-4 w-4 ml-2" /> : 
                    <ChevronDown className="h-4 w-4 ml-2" />
                )}
              </button>

              {/* Dropdown Options */}
              {showManualUpdateOptions && !manualUpdateLoading && (
                <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                  <div className="p-2">
                    <button
                      onClick={() => triggerComprehensiveUpdate('quick')}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-purple-50 rounded-md transition-colors"
                    >
                      <div className="font-medium">Quick Update</div>
                      <div className="text-xs text-gray-500">Last 1-2 hours of changes</div>
                    </button>
                    <button
                      onClick={() => triggerComprehensiveUpdate('full')}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-purple-50 rounded-md transition-colors"
                    >
                      <div className="font-medium">Full Regeneration</div>
                      <div className="text-xs text-gray-500">Complete analysis of today's session</div>
                    </button>
                    <button
                      onClick={() => triggerComprehensiveUpdate('smart')}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-purple-50 rounded-md transition-colors"
                    >
                      <div className="font-medium">Smart Refresh</div>
                      <div className="text-xs text-gray-500">AI-driven content gap analysis</div>
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            <button
              onClick={() => setClearDialogOpen(true)}
              className="flex items-center px-4 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200 transition-colors"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Clear Note
            </button>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-medium text-gray-900">Living Note Settings</h3>
            <button
              onClick={() => setShowSettings(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Update Frequency */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Update Frequency
              </label>
              <select
                value={settings.updateFrequency}
                onChange={(e) => setSettings({
                  ...settings,
                  updateFrequency: e.target.value as LivingNoteSettings['updateFrequency']
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="realtime">Real-time (as changes occur)</option>
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="manual">Manual only</option>
              </select>
            </div>

            {/* Summary Length */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Summary Length
              </label>
              <select
                value={settings.summaryLength}
                onChange={(e) => setSettings({
                  ...settings,
                  summaryLength: e.target.value as LivingNoteSettings['summaryLength']
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="brief">Brief (concise summaries)</option>
                <option value="moderate">Moderate (balanced detail)</option>
                <option value="detailed">Detailed (comprehensive)</option>
              </select>
            </div>

            {/* Writing Style */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Writing Style
              </label>
              <select
                value={settings.writingStyle}
                onChange={(e) => setSettings({
                  ...settings,
                  writingStyle: e.target.value as LivingNoteSettings['writingStyle']
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="technical">Technical (precise, formal)</option>
                <option value="casual">Casual (conversational)</option>
                <option value="formal">Formal (professional)</option>
                <option value="bullet-points">Bullet Points (structured)</option>
              </select>
            </div>

            {/* Max Sections */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Maximum Sections
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={settings.maxSections}
                onChange={(e) => setSettings({
                  ...settings,
                  maxSections: parseInt(e.target.value) || 10
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          {/* Toggles */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="includeMetrics"
                checked={settings.includeMetrics}
                onChange={(e) => setSettings({
                  ...settings,
                  includeMetrics: e.target.checked
                })}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label htmlFor="includeMetrics" className="ml-2 block text-sm text-gray-700">
                Include metrics and statistics
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="autoUpdate"
                checked={settings.autoUpdate}
                onChange={(e) => setSettings({
                  ...settings,
                  autoUpdate: e.target.checked
                })}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label htmlFor="autoUpdate" className="ml-2 block text-sm text-gray-700">
                Enable automatic updates
              </label>
            </div>
          </div>

          {/* Focus Areas */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Focus Areas
              <span className="text-gray-500 text-xs ml-1">(topics to emphasize in summaries)</span>
            </label>
            
            <div className="flex flex-wrap gap-2 mb-3">
              {settings.focusAreas.map((area, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
                >
                  {area}
                  <button
                    onClick={() => removeFocusArea(area)}
                    className="ml-2 text-primary-600 hover:text-primary-800"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            
            <div className="flex space-x-2">
              <input
                type="text"
                value={newFocusArea}
                onChange={(e) => setNewFocusArea(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addFocusArea()}
                placeholder="Add focus area (e.g., 'API design', 'performance')"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <button
                onClick={addFocusArea}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                Add
              </button>
            </div>
          </div>

          {/* Save Button */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={saveSettings}
              disabled={settingsLoading}
              className="flex items-center px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {settingsLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Settings
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* View Mode Selector for Structured Content */}
      {isStructured && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">View Mode</h3>
            <button
              onClick={() => setShowSearch(!showSearch)}
              className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                showSearch 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Search className="h-4 w-4 mr-2" />
              Search
            </button>
          </div>
          
          <div className="flex space-x-2">
            {VIEW_MODES.map(mode => {
              const Icon = mode.icon
              return (
                <button
                  key={mode.type}
                  onClick={() => setViewMode(mode.type)}
                  className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    viewMode === mode.type
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
                  }`}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {mode.label}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Search Panel */}
      {showSearch && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Search Living Note</h3>
            <button
              onClick={() => setShowSearch(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search sessions, topics, keywords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>
      )}

      {/* Stats */}
      <div className={`grid grid-cols-1 ${isStructured ? 'md:grid-cols-5' : 'md:grid-cols-3'} gap-6`}>
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-md">
              <BarChart3 className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Word Count</p>
              <p className="text-lg font-semibold text-gray-900">{note.wordCount}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-md">
              <Clock className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Last Updated</p>
              <p className="text-sm font-semibold text-gray-900">
                {note.lastUpdated ? formatDate(note.lastUpdated) : 'Never'}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-md">
              <FileText className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Status</p>
              <p className="text-sm font-semibold text-gray-900">
                {note.content ? 'Active' : 'Empty'}
              </p>
            </div>
          </div>
        </div>

        {isStructured && (
          <>
            <div className="card">
              <div className="flex items-center">
                <div className="p-2 bg-indigo-100 rounded-md">
                  <Calendar className="h-6 w-6 text-indigo-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Sessions</p>
                  <p className="text-lg font-semibold text-gray-900">{totalSessions}</p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center">
                <div className="p-2 bg-orange-100 rounded-md">
                  <Tag className="h-6 w-6 text-orange-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Topics</p>
                  <p className="text-lg font-semibold text-gray-900">{totalTopics}</p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Note Content */}
      <div className="space-y-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : note.content ? (
          isStructured && viewMode !== 'traditional' ? (
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">AI Summary - {viewMode === 'structured' ? 'Structured View' : 'Timeline View'}</h3>
              
              {sessions.length > 0 ? (
                <div className={viewMode === 'timeline' ? 'space-y-6' : 'space-y-4'}>
                  {sessions
                    .filter(session => {
                      if (!searchQuery) return true
                      const query = searchQuery.toLowerCase()
                      
                      // Handle special search syntax
                      if (query.startsWith('topic:')) {
                        const topic = query.substring(6)
                        return session.metadata?.topics?.some(t => t.toLowerCase().includes(topic))
                      }
                      if (query.startsWith('keyword:')) {
                        const keyword = query.substring(8)
                        return session.metadata?.keywords?.some(k => k.toLowerCase().includes(keyword))
                      }
                      
                      // General search in title and content
                      return session.title.toLowerCase().includes(query) ||
                             session.content.toLowerCase().includes(query) ||
                             session.metadata?.topics?.some(t => t.toLowerCase().includes(query)) ||
                             session.metadata?.keywords?.some(k => k.toLowerCase().includes(query))
                    })
                    .map((session) => (
                      <div key={session.id} className={`card ${viewMode === 'timeline' ? 'border-l-4 border-primary-500 ml-4' : ''}`}>
                        {/* Session Header */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <button
                              onClick={() => toggleSession(session.id)}
                              className="text-gray-500 hover:text-gray-700 transition-colors"
                            >
                              {expandedSessions.has(session.id) ? (
                                <ChevronDown className="h-5 w-5" />
                              ) : (
                                <ChevronRight className="h-5 w-5" />
                              )}
                            </button>
                            <div>
                              <h4 className="text-lg font-medium text-gray-900">{session.title}</h4>
                              <div className="flex items-center space-x-4 text-sm text-gray-500">
                                <span className="flex items-center">
                                  <Clock className="h-4 w-4 mr-1" />
                                  {formatDate(session.timestamp)}
                                </span>
                                {session.metadata?.changes && (
                                  <span className="flex items-center">
                                    <TrendingUp className="h-4 w-4 mr-1" />
                                    {session.metadata.changes} changes
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            {/* Impact Indicator */}
                            {session.metadata?.impact && (
                              <span className={`px-2 py-1 text-xs font-medium rounded-full border ${
                                IMPACT_COLORS[session.metadata.impact as keyof typeof IMPACT_COLORS] || IMPACT_COLORS.brief
                              }`}>
                                {session.metadata.impact}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Session Metadata Tags */}
                        {(session.metadata?.topics?.length || session.metadata?.keywords?.length) && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {session.metadata.topics?.map(topic => (
                              <button
                                key={topic}
                                onClick={() => handleTagClick('topic', topic)}
                                className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                              >
                                <Tag className="h-3 w-3 mr-1" />
                                {topic}
                              </button>
                            ))}
                            {session.metadata.keywords?.map(keyword => (
                              <button
                                key={keyword}
                                onClick={() => handleTagClick('keyword', keyword)}
                                className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
                              >
                                {keyword}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Session Content */}
                        {expandedSessions.has(session.id) && (
                          <div className="mt-4 prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100">
                            <div className="bg-gray-50 border border-gray-200 p-4 rounded-lg">
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
                                {session.content}
                              </ReactMarkdown>
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  }
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No sessions found</p>
                  <p className="text-sm text-gray-500 mt-2">
                    {searchQuery ? 'Try adjusting your search query' : 'Sessions will appear as they are created'}
                  </p>
                </div>
              )}
            </div>
          ) : (
            /* Traditional View */
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">AI Summary</h3>
              <div className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100">
                <div className="bg-white border border-gray-200 p-6 rounded-lg">
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
                    {note.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )
        ) : (
          <div className="card">
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No living note content yet</p>
              <p className="text-sm text-gray-500 mt-2">
                The AI will generate summaries as you make changes to your notes
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Clear Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={clearDialogOpen}
        onClose={() => setClearDialogOpen(false)}
        onConfirm={handleClearNote}
        title="Clear Living Note"
        message="Are you sure you want to clear the living note? This will permanently delete all AI-generated content."
        confirmText="Clear Note"
        cancelText="Cancel"
        danger={true}
        loading={clearLoading}
        extraWarning="This action cannot be undone."
      />
    </div>
  )
}