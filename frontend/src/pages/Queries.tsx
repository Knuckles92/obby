import { useState, useEffect } from 'react'

import { 
  Play, 
  Save, 
  History, 
  BookOpen, 
  Download,
  CheckCircle,
  Loader,
  Activity
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import TimeRangePicker from '../components/TimeRangePicker'
import OutputStylePicker from '../components/OutputStylePicker'
import { apiRequest } from '../utils/api'

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
    markdownContent?: string
    ai?: { model: string; provider?: string }
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

// TypeScript interface for ReactMarkdown code component props
interface CodeComponentProps {
  node?: any
  inline?: boolean
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

export default function Queries() {
  const [query, setQuery] = useState('')
  const [timeRange, setTimeRange] = useState<TimeRange>({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
    end: new Date()
  })
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
  const [outputFormat, setOutputFormat] = useState<string>('summary')
  const [optionsTab, setOptionsTab] = useState<'output' | 'time'>('output')
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false)

  useEffect(() => {
    fetchTemplates()
    fetchSuggestions()
    fetchQueryHistory()
  }, [])

  const fetchTemplates = async () => {
    try {
      const response = await apiRequest<any>('/api/time-query/templates')
      setTemplates(response.templates || [])
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    }
  }

  const fetchSuggestions = async () => {
    try {
      const response = await apiRequest<any>('/api/time-query/suggestions')
      setSuggestions(response.suggestions || [])
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
    }
  }

  const fetchQueryHistory = async () => {
    try {
      const response = await apiRequest<any>('/api/time-query/history?limit=10')
      setQueryHistory(response.queries || [])
    } catch (error) {
      console.error('Failed to fetch query history:', error)
    }
  }

  const handleTemplateSelect = (template: QueryTemplate) => {
    setQuery(template.query)
    setShowTemplates(false)
    if (template.outputFormat) {
      setOutputFormat(template.outputFormat)
    }
    
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
        outputFormat, // Use selected output style
        stream: true
      }

      // Execute synchronously for now
      const response = await apiRequest<QueryResult>('/api/time-query/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...requestData, stream: false })
      })

      setCurrentResult(response)
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
      await apiRequest('/api/time-query/save', {
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

    // Custom components for markdown rendering
    const components = {
      code({ node, inline, className, children, ...props }: CodeComponentProps) {
        const match = /language-(\w+)/.exec(className || '')
        return !inline && match ? (
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            {...props}
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
        ) : (
          <code 
            className={className} 
            style={{ 
              backgroundColor: 'var(--color-surface)', 
              padding: '2px 4px', 
              borderRadius: '3px',
              fontSize: '0.875em'
            }} 
            {...props}
          >
            {children}
          </code>
        )
      }
    }

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
                {formatDuration(result.timeRange.durationHours)} • {result.summary.totalChanges} changes • {result.summary.filesAffected} files{result.ai?.model ? ` • Model: ${result.ai.model}` : ''}
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

        {/* Markdown Content */}
        <div 
          className="p-6 rounded-lg border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div 
            className="prose prose-sm max-w-none"
            style={{ 
              color: 'var(--color-text-primary)'
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={components}
            >
              {result.markdownContent || 'No content available.'}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Activity size={28} style={{ color: 'var(--color-primary)' }} />
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>Queries</h1>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Analyze your development activity with natural language</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTemplates(true)}
            className="flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors"
            style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
          >
            <BookOpen size={18} />
            <span className="font-medium">Templates</span>
          </button>
          <button
            onClick={() => setShowHistory(true)}
            className="flex items-center space-x-2 px-3 py-2 rounded-lg border transition-colors"
            style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
          >
            <History size={18} />
            <span className="font-medium">History</span>
          </button>
          <button
            onClick={executeQuery}
            disabled={!query.trim() || isExecuting}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold transition-all ${!query.trim() || isExecuting ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02]'}`}
            style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}
          >
            {isExecuting ? <Loader size={18} className="animate-spin" /> : <Play size={18} />}
            <span>{isExecuting ? 'Analyzing…' : 'Run'}</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 mt-6">
        {/* Composer */}
        <div className="xl:col-span-4 space-y-4 xl:sticky xl:top-0 self-start">
          {/* Query Input */}
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
            <label className="block text-sm font-medium mb-3" style={{ color: 'var(--color-text-primary)' }}>
              What do you want to analyze?
              <p className="text-sm font-normal mt-1" style={{ color: 'var(--color-text-secondary)' }}>e.g., "Summarize the last 5 days" or "What did I accomplish this week?"</p>
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              className="w-full px-4 py-3 rounded-lg border-2 focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all resize-none"
              style={{ backgroundColor: 'var(--color-background)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
            {suggestions.length > 0 && (
              <div className="mt-3">
                <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>Suggestions</span>
                <div className="mt-2 overflow-x-auto whitespace-nowrap hide-scrollbar">
                  {suggestions.slice(0, 8).map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestionClick(s)}
                      className="inline-block mr-2 mb-2 px-3 py-1.5 text-xs rounded-lg border transition-all duration-200 hover:border-blue-300 hover:bg-blue-50"
                      style={{ backgroundColor: 'var(--color-background)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Options (Output / Time) */}
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
            <div className="flex items-center gap-2 mb-3">
              {[
                { id: 'output', label: 'Output' },
                { id: 'time', label: 'Time Range' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setOptionsTab(tab.id as 'output' | 'time')}
                  className="px-3 py-1.5 rounded-md text-sm border transition-colors"
                  style={{
                    backgroundColor: optionsTab === tab.id ? 'var(--color-primary)' : 'var(--color-surface)',
                    color: optionsTab === tab.id ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
                    borderColor: optionsTab === tab.id ? 'var(--color-primary)' : 'var(--color-border)'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            {optionsTab === 'output' ? (
              <OutputStylePicker value={outputFormat} onChange={setOutputFormat} compact />
            ) : (
              <TimeRangePicker value={timeRange} onChange={setTimeRange} />
            )}
          </div>

          {/* Advanced Filters (Collapsible) */}
          <div className="rounded-lg border" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between px-4 py-3"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <span className="text-sm font-medium">Advanced Filters</span>
              <span className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`} style={{ color: 'var(--color-text-secondary)' }}>›</span>
            </button>
            {showAdvanced && (
              <div className="px-4 pb-4">
                <label className="block text-xs font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                  Focus Areas
                </label>
                <div className="flex space-x-2 mb-3">
                  <input
                    type="text"
                    value={newFocusArea}
                    onChange={(e) => setNewFocusArea(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addFocusArea()}
                    placeholder="e.g., 'frontend', '.py', 'components'"
                    className="flex-1 px-3 py-2 rounded-lg border-2 focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all"
                    style={{ backgroundColor: 'var(--color-background)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
                  />
                  <button
                    onClick={addFocusArea}
                    className="px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-105"
                    style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}
                  >
                    Add
                  </button>
                </div>
                {focusAreas.length > 0 && (
                  <div className="flex flex-wrap gap-1 max-h-24 overflow-auto pr-1">
                    {focusAreas.map((area, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2.5 py-1.5 rounded-full text-xs font-medium border"
                        style={{ backgroundColor: 'var(--color-background)', color: 'var(--color-text-primary)', borderColor: 'var(--color-border)' }}
                      >
                        {area}
                        <button onClick={() => removeFocusArea(area)} className="ml-2 hover:bg-white/20 rounded-full p-0.5 transition-colors" style={{ color: 'var(--color-text-secondary)' }}>×</button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="xl:col-span-8 space-y-4">
          {isExecuting && (
            <div className="p-3 rounded border" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
              <div className="flex items-center space-x-2 mb-2">
                <Loader size={20} className="animate-spin" style={{ color: 'var(--color-primary)' }} />
                <span className="text-sm" style={{ color: 'var(--color-text-primary)' }}>{executionProgress.message || 'Analyzing…'}</span>
              </div>
              <div className="w-full rounded-full h-2" style={{ backgroundColor: 'var(--color-border)' }}>
                <div className="h-full rounded-full transition-all duration-500 ease-out" style={{ backgroundColor: 'var(--color-primary)', width: `${executionProgress.progress}%` }} />
              </div>
            </div>
          )}

          <div>
            {currentResult ? (
              renderResults()
            ) : (
              <div className="h-96 flex flex-col items-center justify-center rounded-lg border-2 border-dashed" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
                <div className="max-w-md mx-auto text-center">
                  <p className="text-lg font-medium mb-2">Compose a query to get started</p>
                  <p className="text-sm">Use the suggestions or templates to quickly generate insightful summaries.</p>
                </div>
              </div>
            )}
          </div>
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
              style={{ backgroundColor: 'var(--color-background)' }}
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 rounded"
                style={{ backgroundColor: 'var(--color-background)', color: 'var(--color-text-secondary)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveQuery}
                disabled={!saveQueryName.trim()}
                className="px-4 py-2 rounded disabled:opacity-50"
                style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Templates Modal */}
      {showTemplates && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="rounded-lg p-6 max-w-3xl w-full mx-4" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text-primary)' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Query Templates</h3>
              <button onClick={() => setShowTemplates(false)} className="px-3 py-1 rounded" style={{ backgroundColor: 'var(--color-background)', color: 'var(--color-text-secondary)' }}>Close</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => { handleTemplateSelect(template); setShowTemplates(false) }}
                  className="group p-4 rounded-xl border-2 border-transparent hover:border-blue-200 hover:shadow-md transition-all duration-200 text-left"
                  style={{ backgroundColor: 'var(--color-surface)' }}
                >
                  <div className="font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>{template.name}</div>
                  <div className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>{template.description}</div>
                  <div className="text-xs font-mono" style={{ color: 'var(--color-primary)' }}>
                    "{template.query}"
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="rounded-lg p-6 max-w-2xl w-full mx-4" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text-primary)' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Recent Queries</h3>
              <button onClick={() => setShowHistory(false)} className="px-3 py-1 rounded" style={{ backgroundColor: 'var(--color-background)', color: 'var(--color-text-secondary)' }}>Close</button>
            </div>
            <div className="space-y-2 max-h-[60vh] overflow-auto pr-1">
              {queryHistory.map((historyItem) => (
                <button
                  key={historyItem.id}
                  onClick={() => { setQuery(historyItem.query_text); setShowHistory(false) }}
                  className="w-full p-4 rounded-xl border-2 border-transparent hover:border-blue-200 hover:shadow-md transition-all duration-200 text-left group"
                  style={{ backgroundColor: 'var(--color-surface)' }}
                >
                  <div className="flex items-start space-x-3">
                    <span className="font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                      {historyItem.query_name || historyItem.query_text}
                    </span>
                    <span className="text-xs font-mono px-2 py-1 rounded-md inline-block" style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}>
                      {new Date(historyItem.created_timestamp).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    {new Date(historyItem.time_range_start).toLocaleDateString()} - {new Date(historyItem.time_range_end).toLocaleDateString()}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
