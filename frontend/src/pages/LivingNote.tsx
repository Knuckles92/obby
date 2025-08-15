import { useState, useEffect, useRef } from 'react'
import { FileText, Clock, BarChart3, Trash2, RefreshCw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { LivingNote as LivingNoteType } from '../types'
import ConfirmationDialog from '../components/ConfirmationDialog'
import { apiFetch } from '../utils/api'

// TypeScript interface for ReactMarkdown code component props
interface CodeComponentProps {
  node?: any
  inline?: boolean
  className?: string
  children?: React.ReactNode
  [key: string]: any
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
  const [hasError, setHasError] = useState(false)
  const [updateLoading, setUpdateLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fallbackTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    try {
      fetchLivingNote()
      connectToSSE()
    } catch (error) {
      console.error('Error initializing LivingNote component:', error)
      setLoading(false)
    }
    
    return () => {
      try {
        disconnectSSE()
        // Clean up any pending fallback timeout
        if (fallbackTimeoutRef.current) {
          clearTimeout(fallbackTimeoutRef.current)
          fallbackTimeoutRef.current = null
        }
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
              sections: data.sections
            })
            
            // Clear any pending fallback timeout since we received the update
            if (fallbackTimeoutRef.current) {
              clearTimeout(fallbackTimeoutRef.current)
              fallbackTimeoutRef.current = null
            }
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


  const triggerUpdate = async () => {
    setUpdateLoading(true)
    try {
      const response = await apiFetch('/api/living-note/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ force: false })
      })
      
      if (response.ok) {
        console.log('Update completed successfully')
        // SSE will automatically refresh the content via notify_living_note_change()
        
        // Set up fallback mechanism in case SSE fails to deliver the update
        if (!isConnected) {
          // If SSE is not connected, immediately fetch the updated content
          console.log('SSE disconnected, fetching content immediately')
          await fetchLivingNote()
        } else {
          // If SSE is connected, wait for automatic update but have a fallback timeout
          fallbackTimeoutRef.current = setTimeout(async () => {
            console.log('SSE fallback timeout triggered, fetching content manually')
            await fetchLivingNote()
            fallbackTimeoutRef.current = null
          }, 1500) // 1.5 second timeout for better responsiveness
        }
      } else {
        const error = await response.json()
        console.error('Failed to trigger update:', error.error)
      }
    } catch (error) {
      console.error('Error triggering update:', error)
      // On error, always try to fetch the latest content
      await fetchLivingNote()
    } finally {
      setUpdateLoading(false)
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
              onClick={triggerUpdate}
              disabled={updateLoading}
              className="flex items-center px-4 py-2 text-sm font-medium text-blue-700 bg-blue-100 rounded-md hover:bg-blue-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {updateLoading ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Update Now
            </button>
            
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


      

      {/* Stats */}
      <div className={`grid grid-cols-1 md:grid-cols-3 gap-6`}>
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
      </div>

      {/* Note Content */}
      <div className="space-y-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : note.content ? (
          /* Traditional View Only */
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">AI Summary</h3>
            <div className="prose prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-ul:mt-2 prose-li:my-1 marker:text-gray-500">
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