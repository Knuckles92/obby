import { useState, useEffect } from 'react'

import { 
  Play, 
  Save, 
  History, 
  BookOpen, 
  Download,
  TrendingUp,
  FileText,
  Activity,
  CheckCircle,
  Loader,
  ChevronDown,
  X
} from 'lucide-react'
import TimeRangePicker from '../components/TimeRangePicker'
import { apiFetch } from '../utils/api'

interface TimeRange {
  start: Date
  end: Date
}

interface QueryTemplate {
  id: string
  name: string
  query: string
  description: string
  timeRange: string
  outputFormat: string
}

interface QueryResult {
  queryId: number
  result: {
    timeRange: {
      start: string
      end: string
      duration: string
      durationHours: number
    }
    summary: {
      totalChanges: number
      filesAffected: number
      linesAdded: number
      linesRemoved: number
      netLinesChanged: number
      changeTypes: Record<string, number>
    }
    outputFormat: string
    generatedAt: string
    aiInsights?: {
      summary?: string
      highlights?: string[]
      actionItems?: Array<{
        title: string
        priority: string
        effort: string
        description: string
      }>
    }
    fileMetrics?: Array<{
      file_path: string
      change_count: number
      total_lines_added: number
      total_lines_removed: number
    }>
    topFiles?: Array<{
      file_path: string
      change_count: number
    }>
    keyTopics?: string[]
    keyKeywords?: string[]
    timeline?: Array<{
      timestamp: string
      changeCount: number
      linesAdded: number
      linesRemoved: number
      filesAffected: number
    }>
  }
  executionTime?: number
}

interface QueryHistory {
  id: number
  query_text: string
  time_range_start: string
  time_range_end: string
  status: string
  created_timestamp: string
  query_name?: string
}

export default function TimeQuery() {
  const [query, setQuery] = useState('')
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
    end: new Date()
  })
  const [outputFormat, setOutputFormat] = useState<'summary' | 'actionItems'>('summary')
  const [focusAreas, setFocusAreas] = useState<string[]>([])
  const [newFocusArea, setNewFocusArea] = useState('')
  
  // Query execution state
  const [isExecuting, setIsExecuting] = useState(false)
  const [currentResult, setCurrentResult] = useState<QueryResult | null>(null)
  const [executionProgress, setExecutionProgress] = useState({ message: '', progress: 0 })
  
  // Templates and history
  const [templates, setTemplates] = useState<QueryTemplate[]>([])
  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>([])
  const [suggestions, setSuggestions] = useState<string[]>([])
  
  // UI state
  const [showTemplates, setShowTemplates] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [saveQueryName, setSaveQueryName] = useState('')

  useEffect(() => {
    fetchTemplates()
    fetchSuggestions()
    fetchQueryHistory()
  }, [])

  const fetchTemplates = async () => {
    try {
      const response = await apiFetch('/api/time-query/templates')
      setTemplates((response as any).templates || [])
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    }
  }

  const fetchSuggestions = async () => {
    try {
      const response = await apiFetch('/api/time-query/suggestions')
      setSuggestions((response as any).suggestions || [])
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
    }
  }

  const fetchQueryHistory = async () => {
    try {
      const response = await apiFetch('/api/time-query/history?limit=10')
      setQueryHistory((response as any).queries || [])
    } catch (error) {
      console.error('Failed to fetch query history:', error)
    }
  }

  const handleTemplateSelect = (template: QueryTemplate) => {
    setQuery(template.query)
    setOutputFormat(template.outputFormat as any)
    setShowTemplates(false)
    
    // Set time range based on template
    const now = new Date()
    switch (template.timeRange) {
      case 'today':
        setTimeRange({
          start: new Date(now.getFullYear(), now.getMonth(), now.getDate()),
          end: now
        })
        break
      case 'thisWeek':
        const dayOfWeek = now.getDay()
        const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1
        setTimeRange({
          start: new Date(now.getFullYear(), now.getMonth(), now.getDate() - mondayOffset),
          end: now
        })
        break
      case 'last7Days':
        setTimeRange({
          start: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
          end: now
        })
        break
      case 'last30Days':
        setTimeRange({
          start: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000),
          end: now
        })
        break
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
  }

  const addFocusArea = () => {
    if (newFocusArea.trim() && !focusAreas.includes(newFocusArea.trim())) {
      setFocusAreas([...focusAreas, newFocusArea.trim()])
      setNewFocusArea('')
    }
  }

  const removeFocusArea = (area: string) => {
    setFocusAreas(focusAreas.filter(a => a !== area))
  }

  const executeQuery = async () => {
    if (!query.trim()) return

    setIsExecuting(true)
    setCurrentResult(null)
    setExecutionProgress({ message: 'Starting analysis...', progress: 0 })

    try {
      const requestData = {
        query: query.trim(),
        startTime: timeRange.start.toISOString(),
        endTime: timeRange.end.toISOString(),
        focusAreas,
        outputFormat,
        stream: true
      }

      // Use EventSource for streaming response
      const _eventSource = new EventSource(`/api/time-query/execute`)
      
      // For this demo, we'll use a regular fetch call instead
      const response = await apiFetch('/api/time-query/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...requestData, stream: false })
      })

      setCurrentResult(response as unknown as QueryResult)
      await fetchQueryHistory() // Refresh history

    } catch (error) {
      console.error('Query execution failed:', error)
      setExecutionProgress({ message: 'Query failed', progress: 0 })
    } finally {
      setIsExecuting(false)
    }
  }

  const handleSaveQuery = async () => {
    if (!currentResult?.queryId || !saveQueryName.trim()) return

    try {
      await apiFetch('/api/time-query/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          queryId: currentResult.queryId,
          name: saveQueryName.trim()
        })
      })
      
      setShowSaveDialog(false)
      setSaveQueryName('')
      await fetchQueryHistory()
    } catch (error) {
      console.error('Failed to save query:', error)
    }
  }

  const formatDuration = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} minutes`
    } else if (hours < 24) {
      return `${Math.round(hours)} hours`
    } else {
      return `${Math.round(hours / 24)} days`
    }
  }

  const renderResults = () => {
    if (!currentResult) return null

    const { result } = currentResult

    return (
      <div className="space-y-6">
        {/* Results Header */}
        <div 
          className="p-4 rounded-lg border flex items-center justify-between"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center space-x-3">
            <CheckCircle 
              size={20} 
              style={{ color: 'var(--color-success, #10b981)' }} 
            />
            <div>
              <h3 
                className="font-semibold"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Query Complete
              </h3>
              <p 
                className="text-sm"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {formatDuration(result.timeRange.durationHours)} • {result.summary.totalChanges} changes • {result.summary.filesAffected} files
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowSaveDialog(true)}
              className="p-2 rounded-lg transition-colors"
              style={{
                backgroundColor: 'var(--color-background)',
                color: 'var(--color-text-secondary)'
              }}
            >
              <Save size={16} />
            </button>
            <button
              className="p-2 rounded-lg transition-colors"
              style={{
                backgroundColor: 'var(--color-background)',
                color: 'var(--color-text-secondary)'
              }}
            >
              <Download size={16} />
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Changes', value: result.summary.totalChanges, icon: Activity },
            { label: 'Files', value: result.summary.filesAffected, icon: FileText },
            { label: 'Lines Added', value: result.summary.linesAdded, icon: TrendingUp },
            { label: 'Lines Removed', value: result.summary.linesRemoved, icon: TrendingUp }
          ].map(({ label, value, icon: Icon }) => (
            <div
              key={label}
              className="p-4 rounded-lg border"
              style={{
                backgroundColor: 'var(--color-surface)'
              }}
            >
              <div className="flex items-center space-x-2 mb-2">
                <Icon 
                  size={16} 
                  style={{ color: 'var(--color-primary)' }} 
                />
                <span 
                  className="text-sm"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {label}
                </span>
              </div>
              <div 
                className="text-2xl font-bold"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {value?.toLocaleString() || 0}
              </div>
            </div>
          ))}
        </div>

        {/* AI Insights */}
        {result.aiInsights && (
          <div 
            className="p-4 rounded-lg border"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <h4 
              className="font-semibold mb-3 flex items-center space-x-2"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <Activity size={16} />
              <span>AI Insights</span>
            </h4>
            
            {result.aiInsights.summary && (
              <div className="p-6">
                <p style={{ color: 'var(--color-text-primary)' }}>
                  {result.aiInsights.summary}
                </p>
              </div>
            )}
            
            {result.aiInsights.highlights && (
              <div className="flex items-center justify-between mb-1">
                <h5 
                  className="font-medium text-sm"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Key Highlights:
                </h5>
                <ul className="space-y-1">
                  {result.aiInsights.highlights.map((highlight, index) => (
                    <li 
                      key={index}
                      className="text-sm flex items-start space-x-2"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      <span style={{ color: 'var(--color-primary)' }}>•</span>
                      <span>{highlight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.aiInsights.actionItems && (
              <div className="mt-4 space-y-2">
                <h5 
                  className="font-medium text-sm"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Suggested Actions:
                </h5>
                {result.aiInsights.actionItems.map((item, index) => (
                  <div 
                    key={index}
                    className="p-3 rounded border-l-4 space-y-1"
                    style={{
                      backgroundColor: 'var(--color-background)',
                      borderLeftColor: item.priority === 'High' ? 'var(--color-error, #ef4444)' : 
                                      item.priority === 'Medium' ? 'var(--color-warning, #f59e0b)' : 
                                      'var(--color-success, #10b981)'
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <span 
                        className="font-medium"
                        style={{ color: 'var(--color-text-primary)' }}
                      >
                        {item.title}
                      </span>
                      <div className="flex items-center space-x-2 text-xs">
                        <span 
                          className="px-2 py-1 rounded"
                          style={{
                            backgroundColor: item.priority === 'High' ? 'var(--color-error, #ef4444)' : 
                                            item.priority === 'Medium' ? 'var(--color-warning, #f59e0b)' : 
                                            'var(--color-success, #10b981)',
                            color: 'white'
                          }}
                        >
                          {item.priority}
                        </span>
                        <History size={16} style={{ color: 'var(--color-text-secondary)' }} />
                        <span style={{ color: 'var(--color-text-secondary)' }}>
                          {item.effort}
                        </span>
                      </div>
                    </div>
                    <p 
                      className="text-sm"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      {item.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Top Files (if available) */}
        {(result.fileMetrics || result.topFiles) && (
          <div 
            className="p-4 rounded-lg border"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <h4 
              className="font-semibold mb-3"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Most Active Files
            </h4>
            <div className="space-y-2">
              {(result.fileMetrics || result.topFiles || []).slice(0, 5).map((file, index) => (
                <div 
                  key={index}
                  className="flex items-center justify-between p-2 rounded"
                  style={{ backgroundColor: 'var(--color-background)' }}
                >
                  <span 
                    className="text-sm font-mono truncate flex-1"
                    style={{ color: 'var(--color-text-primary)' }}
                  >
                    {file.file_path}
                  </span>
                  <span 
                    className="text-sm ml-2"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {file.change_count} changes
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Topics and Keywords */}
        {(result.keyTopics || result.keyKeywords) && (
          <div 
            className="p-4 rounded-lg border"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <h4 
              className="font-semibold mb-3"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Key Topics & Keywords
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {result.keyTopics && (
                <div>
                  <h5 
                    className="text-sm font-medium mb-2"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    Topics
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {result.keyTopics.map((topic, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 rounded-full text-xs"
                        style={{
                          backgroundColor: 'var(--color-primary)',
                          color: 'var(--color-text-inverse)'
                        }}
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {result.keyKeywords && (
                <div>
                  <h5 
                    className="text-sm font-medium mb-2"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    Keywords
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {result.keyKeywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 rounded-full text-xs"
                        style={{
                          backgroundColor: 'var(--color-accent)',
                          color: 'var(--color-text-inverse)'
                        }}
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Modern Header */}
      <div className="flex items-center justify-between">
        <div>
            <Activity size={32} className="text-white" />
            <h1 
              className="text-2xl font-bold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Time-Based Queries
            </h1>
            <p 
              className="text-sm"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Analyze your development activity over time with natural language queries
            </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)'
            }}
          >
            <BookOpen size={18} />
            <span className="font-medium">Templates</span>
          </button>
          
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)'
            }}
          >
            <History size={18} />
            <span className="font-medium">History</span>
          </button>
        </div>
      </div>

      {/* Collapsible Templates Panel */}
      {showTemplates && (
        <div 
          className="p-4 rounded-lg border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <h3 
            className="font-semibold mb-3"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Query Templates
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {templates.map((template) => (
              <button
                key={template.id}
                onClick={() => handleTemplateSelect(template)}
                className="group p-4 rounded-xl border-2 border-transparent hover:border-blue-200 hover:shadow-md transition-all duration-200 text-left"
                style={{
                  backgroundColor: 'var(--color-surface)',
                }}
              >
                <div 
                  className="font-medium mb-1"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {template.name}
                </div>
                <div 
                  className="text-sm mb-2"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {template.description}
                </div>
                <div 
                  className="text-xs font-mono"
                  style={{ color: 'var(--color-primary)' }}
                >
                  "{template.query}"
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Collapsible History Panel */}
      {showHistory && (
        <div 
          className="p-4 rounded-lg border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <h3 
            className="font-semibold mb-3"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Recent Queries
          </h3>
          <div className="space-y-2">
            {queryHistory.map((historyItem) => (
              <button
                key={historyItem.id}
                onClick={() => setQuery(historyItem.query_text)}
                className="w-full p-4 rounded-xl border-2 border-transparent hover:border-blue-200 hover:shadow-md transition-all duration-200 text-left group"
                style={{
                  backgroundColor: 'var(--color-surface)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <span 
                    className="font-medium truncate"
                    style={{ color: 'var(--color-text-primary)' }}
                  >
                    {historyItem.query_name || historyItem.query_text}
                  </span>
                  <span 
                    className="text-xs font-mono px-2 py-1 rounded-md inline-block"
                    style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}
                  >
                    {new Date(historyItem.created_timestamp).toLocaleDateString()}
                  </span>
                </div>
                <div 
                  className="text-sm"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {new Date(historyItem.time_range_start).toLocaleDateString()} - {new Date(historyItem.time_range_end).toLocaleDateString()}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-8">
        {/* Query Input Section */}
        <div className="space-y-6">
          {/* Main Query Input */}
          <div 
            className="p-6 rounded-lg border"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <label 
              className="block text-sm font-medium mb-3"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>Describe what you'd like to analyze from your development activity</p>
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., 'Summarize the last 5 days' or 'What did I accomplish this week?'"
              rows={3}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all resize-none"
              style={{
                backgroundColor: 'var(--color-background)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-primary)'
              }}
            />
            {/* Suggestions */}
            {suggestions.length > 0 && (
              <div className="mt-4">
                <span 
                  className="text-xs font-medium"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  Suggestions:
                </span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {suggestions.slice(0, 4).map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="px-3 py-2 text-sm rounded-lg border-2 border-transparent hover:border-blue-300 hover:bg-blue-50 transition-all duration-200"
                      style={{
                        backgroundColor: 'var(--color-background)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-secondary)'
                      }}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Configuration Row */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Time Range Picker - Takes 2 columns */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-lg border p-6"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)'
              }}
            >
              <TimeRangePicker
                value={timeRange}
                onChange={setTimeRange}
              />
            </div>
          </div>

          {/* Output Format and Focus Areas - Takes 2 columns */}
          <div className="lg:col-span-2 space-y-6">
            {/* Output Format */}
            <div 
              className="p-4 rounded-lg border"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)'
              }}
            >
              <label 
                className="block text-sm font-medium mb-3"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Output Format
              </label>
              <div className="space-y-2">
                {[
                  { id: 'summary', label: 'Summary', description: 'Concise overview with key insights' },
                  { id: 'actionItems', label: 'Action Items', description: 'AI-generated next steps' }
                ].map(({ id, label, description }) => (
                  <label key={id} className={`flex items-start space-x-3 p-3 rounded-lg border-2 cursor-pointer transition-all duration-200 ${outputFormat === id ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <input
                      type="radio"
                      name="outputFormat"
                      value={id}
                      checked={outputFormat === id}
                      onChange={(e) => setOutputFormat(e.target.value as any)}
                      className="mt-1"
                    />
                    <div>
                      <div 
                        className="font-medium text-sm"
                        style={{ color: 'var(--color-text-primary)' }}
                      >
                        {label}
                      </div>
                      <div 
                        className="text-xs"
                        style={{ color: 'var(--color-text-secondary)' }}
                      >
                        {description}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Focus Areas */}
            <div 
              className="p-4 rounded-lg border"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)'
              }}
            >
              <label 
                className="block text-sm font-medium mb-3"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Focus Areas
                <p className="text-sm font-normal mt-1" style={{ color: 'var(--color-text-secondary)' }}>Filter by file types, directories, or keywords</p>
              </label>
              <div className="flex space-x-2 mb-3">
                <input
                  type="text"
                  value={newFocusArea}
                  onChange={(e) => setNewFocusArea(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addFocusArea()}
                  placeholder="e.g., 'frontend', '.py', 'components'"
                  className="flex-1 px-3 py-2 rounded-lg border-2 border-gray-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all"
                  style={{
                    backgroundColor: 'var(--color-background)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-primary)'
                  }}
                />
                <button
                  onClick={addFocusArea}
                  className="px-4 py-2 rounded-lg font-medium transition-all duration-200 hover:scale-105"
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: 'var(--color-text-inverse)'
                  }}
                >
                  Add
                </button>
              </div>
              {focusAreas.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {focusAreas.map((area, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-2 rounded-full text-sm font-medium border-2 border-blue-200 bg-blue-50"
                      style={{
                        backgroundColor: 'var(--color-background)',
                        color: 'var(--color-text-primary)',
                        borderColor: 'var(--color-primary)'
                      }}
                    >
                      {area}
                      <button
                        onClick={() => removeFocusArea(area)}
                        className="ml-2 hover:bg-white/20 rounded-full p-1 transition-colors"
                        style={{ color: 'var(--color-text-secondary)' }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Execute Button and Progress - Takes 1 column */}
          <div className="lg:col-span-1 space-y-4">
            <button
              onClick={executeQuery}
              disabled={!query.trim() || isExecuting}
              className={`w-full flex items-center justify-center space-x-3 px-6 py-4 rounded-xl font-semibold text-lg transition-all duration-200 shadow-lg hover:shadow-xl ${!query.trim() || isExecuting ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02]'}`}
              style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)'
              }}
            >
              {isExecuting ? (
                <>
                  <Loader size={20} className="animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Play size={20} />
                  <span>Execute Query</span>
                </>
              )}
            </button>

            {/* Execution Progress */}
            {isExecuting && (
              <div 
                className="p-3 rounded border"
                style={{
                  backgroundColor: 'var(--color-background)'
                }}
              >
                <div className="flex items-center space-x-2 mb-2">
                  <Loader size={20} className="animate-spin" style={{ color: 'var(--color-primary)' }} />
                  <span 
                    className="text-sm"
                    style={{ color: 'var(--color-text-primary)' }}
                  >
                    {executionProgress.message}
                  </span>
                </div>
                <div 
                  className="w-full bg-gray-200 rounded-full h-2"
                  style={{ backgroundColor: 'var(--color-border)' }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      backgroundColor: 'var(--color-primary)',
                      width: `${executionProgress.progress}%`
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Results Panel */}
        <div>
          {currentResult ? renderResults() : (
            <div 
              className="h-96 flex flex-col items-center justify-center rounded-lg border-2 border-dashed"
              style={{
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-secondary)'
              }}
            >
              <div className="max-w-md mx-auto">
                <div className="flex items-center justify-center space-x-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  <span>Try asking about your recent development activity</span>
                </div>
                <p className="text-lg font-medium mb-2">Ready for your query</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Query Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div 
            className="bg-white rounded-lg p-6 max-w-md w-full mx-4"
            style={{
              backgroundColor: 'var(--color-surface)',
              color: 'var(--color-text-primary)'
            }}
          >
            <h3 className="text-lg font-semibold mb-4">Save Query</h3>
            <input
              type="text"
              value={saveQueryName}
              onChange={(e) => setSaveQueryName(e.target.value)}
              placeholder="Enter a name for this query"
              className="w-full px-3 py-2 rounded border mb-4"
              style={{
                backgroundColor: 'var(--color-background)'
              }}
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 rounded"
                style={{
                  backgroundColor: 'var(--color-background)',
                  color: 'var(--color-text-secondary)'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveQuery}
                disabled={!saveQueryName.trim()}
                className="px-4 py-2 rounded disabled:opacity-50"
                style={{
                  backgroundColor: 'var(--color-primary)',
                  color: 'var(--color-text-inverse)'
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}