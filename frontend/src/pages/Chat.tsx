import { useCallback, useEffect, useRef, useState } from 'react'
import { Send, MessageSquare, Settings, Wrench, Activity, FileText, X, Minimize2, Maximize2 } from 'lucide-react'
import { apiRequest } from '../utils/api'
import FileBrowser from '../components/FileBrowser'
import NoteEditor from '../components/NoteEditor'
import ConfirmationDialog from '../components/ConfirmationDialog'
import LoadingIndicator from '../components/LoadingIndicator'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

type Role = 'system' | 'user' | 'assistant' | 'tool'

interface ChatMessage {
  role: Role
  content: string
  tool_calls?: any[]
  tool_call_id?: string
  name?: string
}

interface ToolSchema {
  type: string
  function?: {
    name: string
    description?: string
  }
}

interface ToolInfo {
  name: string
  description?: string
}

type AgentActionType = 'progress' | 'tool_call' | 'tool_result' | 'warning' | 'error' | 'assistant_thinking'

interface AgentAction {
  id: string
  type: AgentActionType
  label: string
  detail?: string
  timestamp: string
  sessionId?: string
}

interface AgentActionResponse {
  id: string
  type: AgentActionType
  label: string
  detail?: string | null
  timestamp: string
  session_id?: string
  tool_call_id?: string
  success?: boolean
  error?: string
}

interface ChatCompletionResponse {
  reply: string
  tools_used?: boolean
  conversation?: ChatMessage[]
  provider_used?: string
  fallback_occurred?: boolean
  fallback_reason?: string
  session_id?: string
  agent_actions?: AgentActionResponse[]
  raw_conversation?: ChatMessage[]
}

const createLocalActionId = () => `action-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const formatTimestamp = (iso: string) => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const actionTypeLabel = (type: AgentActionType) => {
  switch (type) {
    case 'tool_call':
      return 'tool call'
    case 'tool_result':
      return 'tool result'
    case 'assistant_thinking':
      return 'reasoning'
    case 'error':
      return 'error'
    case 'warning':
      return 'warning'
    default:
      return 'progress'
  }
}

const actionStyle = (type: AgentActionType) => {
  switch (type) {
    case 'tool_call':
      return 'border-blue-200 bg-blue-50 text-blue-800'
    case 'tool_result':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800'
    case 'assistant_thinking':
      return 'border-purple-200 bg-purple-50 text-purple-800'
    case 'error':
      return 'border-red-200 bg-red-50 text-red-800'
    case 'warning':
      return 'border-amber-200 bg-amber-50 text-amber-800'
    default:
      return 'border-gray-200 bg-gray-50 text-gray-700'
  }
}

const shortSessionLabel = (sessionId?: string) => {
  if (!sessionId) return ''
  const parts = sessionId.split('-')
  if (parts.length <= 2) return sessionId
  return parts.slice(-2).join('-')
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [provider, setProvider] = useState<'openai' | 'claude'>('claude')
  const [enableFallback, setEnableFallback] = useState(false)
  const [currentModel, setCurrentModel] = useState<string>('')
  const [availableTools, setAvailableTools] = useState<ToolInfo[]>([])
  const [showSettings, setShowSettings] = useState(false)
  const [progressMessage, setProgressMessage] = useState<string | null>(null)
  const [, setProgressType] = useState<string | null>(null)
  const [agentActions, setAgentActions] = useState<AgentAction[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [headerMinimized, setHeaderMinimized] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState<string>('')
  const [isStreaming, setIsStreaming] = useState(false)

  // File browser and note editor state
  const [fileBrowserOpen, setFileBrowserOpen] = useState(true)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [includeNoteContext, setIncludeNoteContext] = useState(true)
  const [contextBeingUsed, setContextBeingUsed] = useState(false)
  const [showUnsavedWarning, setShowUnsavedWarning] = useState(false)
  const [pendingFileSelection, setPendingFileSelection] = useState<string | null>(null)

  // Resizable panel widths
  const [fileBrowserWidth, setFileBrowserWidth] = useState(280)
  const [chatPanelWidth, setChatPanelWidth] = useState(400)
  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Load panel widths from localStorage
  useEffect(() => {
    const savedFileBrowserWidth = localStorage.getItem('chatFileBrowserWidth')
    const savedChatPanelWidth = localStorage.getItem('chatPanelWidth')
    
    if (savedFileBrowserWidth) {
      setFileBrowserWidth(parseInt(savedFileBrowserWidth, 10))
    }
    if (savedChatPanelWidth) {
      setChatPanelWidth(parseInt(savedChatPanelWidth, 10))
    }
  }, [])

  // Save panel widths to localStorage
  useEffect(() => {
    localStorage.setItem('chatFileBrowserWidth', fileBrowserWidth.toString())
    localStorage.setItem('chatPanelWidth', chatPanelWidth.toString())
  }, [fileBrowserWidth, chatPanelWidth])

  useEffect(() => {
    setMessages([
      {
        role: 'system',
        content: `You are an AI assistant for Obby, a file monitoring and note management system.

Context: Obby tracks file changes in a local repository, stores content in SQLite (obby.db), and provides semantic search through AI-analyzed notes. The notes directory contains documentation and tracked files.

Tools available:
- notes_search: Search through notes and documentation with grep/ripgrep

Guidelines:
- Be concise and direct in responses
- Always begin by searching the notes directory with notes_search before considering any other tool or datasource.
- Do not query SQLite or other databases unless the notes search clearly cannot answer the question.
- When using tools, proceed without announcing your actions
- Synthesize results rather than listing raw data
- Focus on answering the user's question efficiently`
      }
    ])

    loadAvailableTools()
    fetchCurrentModel()

    return () => {
      disconnectProgressSSE()
    }
  }, [])

  const loadAvailableTools = async () => {
    try {
      const toolsInfo = await apiRequest<{ tool_names: string[]; tools?: ToolSchema[] }>('/api/chat/tools')
      const toolSchemas = toolsInfo.tools || []
      const parsedTools: ToolInfo[] = toolSchemas.map((schema) => {
        const toolName = schema.function?.name || 'Unknown tool'
        return {
          name: toolName,
          description: schema.function?.description?.trim() || undefined,
        }
      })

      const knownNames = new Set(parsedTools.map((tool) => tool.name))
      toolsInfo.tool_names
        .filter((name) => !knownNames.has(name))
        .forEach((name) => parsedTools.push({ name }))

      setAvailableTools(parsedTools)
    } catch (e) {
      console.warn('Failed to load available tools:', e)
    }
  }

  const fetchCurrentModel = async () => {
    try {
      const pingResponse = await apiRequest<{ model: string; claude_model: string }>('/api/chat/ping')
      const model = provider === 'openai' ? pingResponse.model : pingResponse.claude_model
      setCurrentModel(model || '')
    } catch (e) {
      console.warn('Failed to get model from ping endpoint:', e)
    }
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading, streamingMessage])

  // Refetch model when provider changes
  useEffect(() => {
    fetchCurrentModel()
  }, [provider])

  // Get display model name
  const getDisplayModel = () => {
    if (!currentModel) return ''
    
    if (provider === 'claude') {
      // Map Claude model codes to display names
      switch (currentModel.toLowerCase()) {
        case 'sonnet':
          return 'Sonnet'
        case 'opus':
          return 'Opus' 
        case 'haiku':
          return 'Haiku'
        default:
          return currentModel
      }
    }
    
    // For OpenAI, return as-is
    return currentModel
  }

  const appendAgentAction = useCallback((action: AgentAction) => {
    setAgentActions((prev) => {
      if (prev.some((existing) => existing.id === action.id)) {
        return prev
      }
      const next = [...prev, action]
      return next.slice(-120)
    })
  }, [])

  const recordAgentAction = useCallback(
    (
      type: AgentActionType,
      label: string,
      detail?: string | null,
      sessionOverride?: string | null,
      idOverride?: string,
      timestampOverride?: string
    ) => {
      const timestamp = timestampOverride ?? new Date().toISOString()
      const id = idOverride ?? createLocalActionId()
      appendAgentAction({
        id,
        type,
        label,
        detail: detail ?? undefined,
        timestamp,
        sessionId: sessionOverride ?? currentSessionId ?? undefined,
      })
    },
    [appendAgentAction, currentSessionId]
  )

  const disconnectProgressSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setProgressMessage(null)
    setProgressType(null)
  }, [])

  const connectToProgressSSE = useCallback((sessionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    try {
      const eventSource = new EventSource(`/api/chat/progress/${sessionId}`)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        console.log('Connected to chat progress updates')
        recordAgentAction('progress', 'Connected to agent telemetry', null, sessionId)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const eventType = data.type

          if (!eventType || eventType === 'keepalive') {
            return
          }

          if (eventType === 'connected') {
            recordAgentAction('progress', data.message || 'Connected to agent telemetry', null, sessionId, undefined, data.timestamp)
            return
          }

          // Handle new assistant message turn starting
          if (eventType === 'assistant_message_start') {
            // Reset streaming state for new turn
            setStreamingMessage('')
            setIsStreaming(true)
            return
          }

          // Handle assistant message turn completing
          if (eventType === 'assistant_message_complete') {
            const content = data.content || streamingMessage
            if (content) {
              // Add completed message to conversation
              setMessages((prev) => [...prev, { role: 'assistant', content }])
              setStreamingMessage('')
            }
            setIsStreaming(false)
            return
          }

          // Handle streaming text chunks
          if (eventType === 'assistant_text_chunk') {
            const chunk = data.chunk || ''
            const isComplete = data.is_complete || false

            if (isComplete) {
              // Streaming is complete (final signal)
              setIsStreaming(false)
            } else if (chunk) {
              // Append chunk to current turn's streaming message
              setIsStreaming(true)
              setStreamingMessage((prev) => prev + chunk)
            }
            return
          }

          setProgressMessage(data.message || null)
          setProgressType(eventType)

          const extras = { ...data }
          delete extras.type
          delete extras.message
          delete extras.session_id
          delete extras.timestamp

          let actionType: AgentActionType = 'progress'
          if (eventType === 'tool_use') {
            actionType = 'tool_call'
          } else if (eventType === 'tool_result') {
            actionType = 'tool_result'
          } else if (eventType === 'assistant_thinking') {
            actionType = 'assistant_thinking'
          } else if (eventType === 'error') {
            actionType = 'error'
          } else if (eventType === 'warning') {
            actionType = 'warning'
          } else if (eventType === 'validating' || eventType === 'configuring' || eventType === 'connecting' || eventType === 'sending') {
            actionType = 'progress'
          }

          let detail: string | null = null
          if (actionType === 'tool_call') {
            const toolLabel = extras.tool_name || extras.tool || extras.name
            if (toolLabel) {
              detail = `Tool: ${String(toolLabel)}`
            }
            // Add provider info if available
            if (extras.provider) {
              detail = (detail ? detail + '\n' : '') + `Provider: ${extras.provider}`
            }
          } else if (actionType === 'tool_result') {
            const resultDetails: string[] = []
            if (typeof extras.success === 'boolean') {
              resultDetails.push(`Success: ${extras.success ? 'Yes' : 'No'}`)
            }
            if (extras.tool_name) {
              resultDetails.push(`Tool: ${extras.tool_name}`)
            }
            if (resultDetails.length > 0) {
              detail = resultDetails.join('\n')
            }
          } else if ((actionType === 'error' || actionType === 'warning') && Object.keys(extras).length > 0) {
            // Only show extras if they have meaningful content
            const meaningfulKeys = Object.keys(extras).filter(k => extras[k] && k !== 'type')
            if (meaningfulKeys.length > 0) {
              detail = JSON.stringify(extras, null, 2)
            }
          }

          const label = data.message || eventType
          recordAgentAction(actionType, label, detail, sessionId)

          if (eventType === 'completed') {
            setTimeout(() => {
              setProgressMessage(null)
              setProgressType(null)
            }, 2000)
          } else if (eventType === 'error') {
            setTimeout(() => {
              setProgressMessage(null)
              setProgressType(null)
            }, 5000)
          }
        } catch (eventError) {
          console.error('Error parsing chat progress SSE message:', eventError)
          recordAgentAction('warning', 'Failed to parse agent update', String(eventError), sessionId)
        }
      }

      eventSource.onerror = (error) => {
        console.error('Chat progress SSE connection error:', error)
        recordAgentAction('warning', 'Agent telemetry connection interrupted', null, sessionId)
        if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
          disconnectProgressSSE()
        }
      }
    } catch (error) {
      console.error('Failed to establish chat progress SSE connection:', error)
      recordAgentAction('error', 'Unable to establish agent telemetry', String(error), sessionId)
    }
  }, [recordAgentAction, disconnectProgressSSE])

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || loading) return
    setError(null)

    // Reset streaming state
    setStreamingMessage('')
    setIsStreaming(false)

    // Prepare messages with optional note context
    let messagesToSend = [...messages]
    let userMessage = content
    let displayMessage = content

    // Include note context if enabled and file is selected
    if (selectedFile && includeNoteContext) {
      setContextBeingUsed(true)
      try {
        const { fetchFileContent } = await import('../utils/fileOperations')
        const fileData = await fetchFileContent(selectedFile)

        // Add note content as context before user message (for AI only)
        const contextMessage = `[Context: User is currently viewing the file "${fileData.name}" at path "${selectedFile}"]\n\n\`\`\`markdown\n${fileData.content}\n\`\`\`\n\n---\n\nUser's question about this note:`
        userMessage = `${contextMessage}\n\n${content}`

        recordAgentAction('progress', 'Including note context', `File: ${fileData.name}`, undefined)
      } catch (err) {
        console.error('Failed to fetch note content for context:', err)
        recordAgentAction('warning', 'Could not include note context', String(err), undefined)
      }
    }

    const next = [...messagesToSend, { role: 'user', content: userMessage }]
    // Store display version separately
    const displayMessages = [...messagesToSend, { role: 'user', content: displayMessage }]
    setMessages(displayMessages)
    setInput('')
    setLoading(true)

    disconnectProgressSSE()

    const sessionId = `chat-${Date.now()}-${Math.random().toString(36).substring(7)}`
    setCurrentSessionId(sessionId)

    // Show preview of the query being sent
    const queryPreview = content.length > 80 ? content.slice(0, 80) + '...' : content
    recordAgentAction('progress', `Sending: "${queryPreview}"`, `Provider: ${provider}`, sessionId)

    setProgressMessage(null)
    setProgressType(null)
    connectToProgressSSE(sessionId)

    try {
      const res = await apiRequest<ChatCompletionResponse>(
        '/api/chat/complete',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: next, // Send messages with context to AI
            provider: provider,
            enable_fallback: enableFallback,
            session_id: sessionId
          }),
        }
      )
      const reply = (res.reply || '').trim()

      if (res.fallback_occurred && res.fallback_reason) {
        console.warn(`Fallback occurred: ${res.fallback_reason}. Used ${res.provider_used} instead.`)
        recordAgentAction('warning', `Fallback to ${res.provider_used}`, res.fallback_reason, res.session_id ?? sessionId)
      }

      if (Array.isArray(res.agent_actions)) {
        res.agent_actions.forEach((action) => {
          if (!action || !action.id) return
          recordAgentAction(
            action.type || 'progress',
            action.label || action.type || 'Agent action',
            action.detail,
            action.session_id ?? res.session_id ?? sessionId,
            action.id,
            action.timestamp
          )
        })
      }

      // Handle conversation responses (multiple messages)
      if (Array.isArray(res.conversation) && res.conversation.length > 0) {
        setMessages((prevMessages) => {
          const existingMessageIds = prevMessages.map((m, idx) => `${m.role}:${m.content.substring(0, 50)}`)
          
          const newMessages = res.conversation.filter(msg => {
            const messageId = `${msg.role}:${msg.content.substring(0, 50)}`
            return !existingMessageIds.includes(messageId)
          })

          // Clean user messages to match displayMessage
          const cleanNewMessages = newMessages.map(msg =>
            msg.role === 'user' && msg.content !== displayMessage ?
              { ...msg, content: displayMessage } : msg
          )
          
          return [...prevMessages, ...cleanNewMessages]
        })
      } 
      // Handle single reply responses
      else if (reply) {
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      }

      // Clear streaming state after final message is received
      setStreamingMessage('')
      setIsStreaming(false)

      // Reset context being used indicator
      setContextBeingUsed(false)
    } catch (e: any) {
      const errorMessage = e?.message || 'Chat failed'

      // Clear streaming state on error
      setStreamingMessage('')
      setIsStreaming(false)

      // Reset context being used indicator
      setContextBeingUsed(false)
      setError(errorMessage)
      recordAgentAction('error', 'Chat request failed', errorMessage, sessionId)
    } finally {
      setLoading(false)
      disconnectProgressSSE()
    }
  }

  const handleFileSelect = useCallback((filePath: string) => {
    setSelectedFile(filePath)
    setPendingFileSelection(null)
  }, [])

  const handleFileBrowserToggle = useCallback(() => {
    setFileBrowserOpen(prev => !prev)
  }, [])

  // Resize handlers for left panel (FileBrowser)
  const handleMouseDownLeft = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingLeft(true)
  }, [])

  const handleMouseDownRight = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingRight(true)
  }, [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingLeft && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect()
        const newWidth = e.clientX - containerRect.left
        setFileBrowserWidth(newWidth)
      } else if (isResizingRight && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect()
        const newWidth = containerRect.right - e.clientX
        setChatPanelWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizingLeft(false)
      setIsResizingRight(false)
    }

    if (isResizingLeft || isResizingRight) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingLeft, isResizingRight])

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl+B - Toggle file browser
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault()
        handleFileBrowserToggle()
      }
      // Cmd/Ctrl+P - Focus fuzzy search (handled by FileBrowser component)
      // Cmd/Ctrl+S - Save file (handled by NoteEditor component)
      // Cmd/Ctrl+E - Toggle edit/preview (handled by NoteEditor component)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleFileBrowserToggle])

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Markdown components for chat messages
  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
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
        <code className={className} {...props}>
          {children}
        </code>
      )
    }
  }

  return (
    <div className="h-[94dvh] flex flex-col m-0 p-0">
      {/* Header */}
      <div className={`flex-shrink-0 transition-all duration-300 ${
        headerMinimized 
          ? 'border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900' 
          : ''
      }`}>
        {headerMinimized ? (
          /* Compact Header */
          <div className="px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-1.5 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <MessageSquare className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  Chat
                  {currentModel && (
                    <>
                      {' '}
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ({provider === 'openai' ? 'OpenAI' : 'Claude'} {getDisplayModel()})
                      </span>
                    </>
                  )}
                </span>
              </div>

              <div className="flex items-center space-x-2">
                {/* Compact note context indicator */}
                {selectedFile && includeNoteContext && (
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-lg text-xs">
                    <FileText className="h-3 w-3" />
                    <span>{selectedFile.split('/').pop()}</span>
                    <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" title="Context included in background"></div>
                    <button
                      onClick={() => setIncludeNoteContext(false)}
                      className="hover:bg-blue-200 dark:hover:bg-blue-800 rounded p-0.5"
                      title="Remove from context"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </div>
                )}
                
                <button
                  onClick={() => setHeaderMinimized(false)}
                  className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
                  title="Expand header"
                >
                  <Maximize2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Modern Header */
          <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
            background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
          }}>
            <div className="absolute inset-0 bg-black/10"></div>
            <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
            <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

            <div className="relative z-10 flex items-center justify-between">
              <div className="space-y-2">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                    <MessageSquare className="h-6 w-6" />
                  </div>
                  <h1 className="text-3xl font-bold tracking-tight">Chat with AI</h1>
                </div>
                <p className="text-blue-100 text-lg">Interactive AI conversation with note context and file operations</p>
              </div>

              <div className="flex items-center space-x-4">
                {/* Note context indicator */}
                {selectedFile && includeNoteContext && (
                  <div className="flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border border-white/30 bg-white/10">
                    <FileText className="h-4 w-4" />
                    <span className="text-sm font-medium">Context: {selectedFile.split('/').pop()}</span>
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" title="Context included in background"></div>
                    <button
                      onClick={() => setIncludeNoteContext(false)}
                      className="ml-1 hover:bg-white/20 rounded p-0.5 transition-colors"
                      title="Remove from context"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                )}
                {selectedFile && !includeNoteContext && (
                  <button
                    onClick={() => setIncludeNoteContext(true)}
                    className="px-4 py-2 rounded-full backdrop-blur-sm border border-white/30 bg-white/10 hover:bg-white/20 text-white font-medium text-sm transition-colors"
                  >
                    Include note in background context
                  </button>
                )}

                <div className="flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border border-white/30 bg-white/10">
                  <Wrench className="h-4 w-4" />
                  <span className="text-sm font-medium">
                    {provider === 'openai' ? 'OpenAI' : 'Claude'}
                    {currentModel && (
                      <>
                        {' '}
                        <span className="text-xs opacity-75">({getDisplayModel()})</span>
                      </>
                    )}
                  </span>
                </div>
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-2 rounded-xl backdrop-blur-sm border border-white/30 bg-white/10 hover:bg-white/20 text-white transition-colors"
                  title="Chat Settings"
                >
                  <Settings className="h-5 w-5" />
                </button>
                <button
                  onClick={() => setHeaderMinimized(true)}
                  className="p-2 rounded-xl backdrop-blur-sm border border-white/30 bg-white/10 hover:bg-white/20 text-white transition-colors"
                  title="Minimize header"
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Three-column layout */}
      <div ref={containerRef} className="flex-1 flex min-h-0">
        {/* File Browser (collapsible) */}
        {fileBrowserOpen && (
          <>
            <div style={{ width: `${fileBrowserWidth}px` }} className="flex-shrink-0">
              <FileBrowser
                isOpen={fileBrowserOpen}
                onToggle={handleFileBrowserToggle}
                onFileSelect={handleFileSelect}
                selectedFile={selectedFile}
              />
            </div>
            {/* Left resize handle */}
            <div
              onMouseDown={handleMouseDownLeft}
              className="w-1 flex-shrink-0 bg-gray-200 dark:bg-gray-700 hover:bg-blue-400 dark:hover:bg-blue-500 cursor-col-resize transition-colors"
              style={{ userSelect: 'none' }}
            />
          </>
        )}

        {!fileBrowserOpen && (
          <FileBrowser
            isOpen={fileBrowserOpen}
            onToggle={handleFileBrowserToggle}
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
          />
        )}

        {/* Note Editor (center, flexible width) */}
        <div className="flex-1 min-w-0">
          <NoteEditor
            filePath={selectedFile}
            onSave={(path) => {
              console.log('File saved:', path)
            }}
          />
        </div>

        {/* Right resize handle */}
        <div
          onMouseDown={handleMouseDownRight}
          className="w-1 flex-shrink-0 bg-gray-200 dark:bg-gray-700 hover:bg-blue-400 dark:hover:bg-blue-500 cursor-col-resize transition-colors"
          style={{ userSelect: 'none' }}
        />

        {/* Chat Panel (right, resizable width) */}
        <div 
          style={{ width: `${chatPanelWidth}px` }} 
          className="flex-shrink-0 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col"
        >
          {showSettings && (
            <div className="flex-shrink-0 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
              <h3 className="font-semibold mb-3 text-gray-900 dark:text-gray-100">Chat Settings</h3>
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-medium mb-2">AI Provider</div>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="provider"
                        value="openai"
                        checked={provider === 'openai'}
                        onChange={(e) => setProvider(e.target.value as 'openai' | 'claude')}
                        className="text-blue-600"
                      />
                      <span className="text-sm">OpenAI</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="provider"
                        value="claude"
                        checked={provider === 'claude'}
                        onChange={(e) => setProvider(e.target.value as 'openai' | 'claude')}
                        className="text-blue-600"
                      />
                      <span className="text-sm">Claude</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableFallback}
                      onChange={(e) => setEnableFallback(e.target.checked)}
                      className="rounded text-blue-600"
                    />
                    <span className="text-sm">Enable fallback to other provider on failure</span>
                  </label>
                  <p className="text-xs text-gray-500 mt-1 ml-6">
                    If the selected provider fails, automatically try the other one
                  </p>
                </div>

                {availableTools.length > 0 && (
                  <div className="pt-2 border-t border-gray-200">
                    <div className="text-sm font-medium mb-2">Available Tools</div>
                    <div className="text-xs text-gray-600 mb-2">
                      Both providers have access to these tools for enhanced functionality
                    </div>
                    <ul className="space-y-1">
                      {availableTools.map((tool) => (
                        <li key={tool.name} className="rounded border border-gray-200 bg-white px-2 py-1">
                          <div className="text-xs font-semibold text-gray-800">{tool.name}</div>
                          {tool.description && (
                            <div className="text-xs text-gray-600">{tool.description}</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={scrollRef} className="flex-1 min-h-0 overflow-auto p-4 bg-gray-50 dark:bg-gray-950">
            {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').length === 0 && (
              <div className="text-gray-500 dark:text-gray-400 text-sm text-center py-8">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Start a conversation</p>
                {selectedFile && includeNoteContext && (
                  <p className="text-xs mt-2 text-blue-600 dark:text-blue-400">
                    📄 Note context will be included in the background
                  </p>
                )}
              </div>
            )}
            <div className="space-y-3">
              {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').map((m, idx) => (
                <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.role === 'user' ? (
                    <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap bg-blue-600 text-white relative">
                      {m.content}
                      {contextBeingUsed && idx === messages.filter((msg) => msg.role !== 'system' && msg.role !== 'tool').length - 1 && (
                        <div className="absolute -top-2 -right-2 w-4 h-4 bg-blue-500 rounded-full animate-pulse" title="Context included in background">
                          <FileText className="h-2.5 w-2.5 text-white mx-auto mt-0.5" />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700">
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {/* Show current streaming turn if we have content */}
              {isStreaming && streamingMessage && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700">
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                        {streamingMessage}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              )}
              {/* Show loading animation when streaming (new turn) or waiting for response */}
              {(isStreaming || loading) && <LoadingIndicator />}
              {error && (
                <div className="text-red-600 text-sm">{error}</div>
              )}
            </div>
          </div>

          <div className="flex-shrink-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
            <div className="flex flex-col gap-2">
              <input
                className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                placeholder="Type your message…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
              >
                <Send className="h-4 w-4" />
                {loading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Unsaved changes warning dialog */}
      <ConfirmationDialog
        isOpen={showUnsavedWarning}
        onClose={() => {
          setShowUnsavedWarning(false)
          setPendingFileSelection(null)
        }}
        onConfirm={() => {
          if (pendingFileSelection) {
            setSelectedFile(pendingFileSelection)
          }
          setShowUnsavedWarning(false)
          setPendingFileSelection(null)
        }}
        title="Unsaved Changes"
        message="You have unsaved changes in the current file. Do you want to discard them and switch files?"
        confirmText="Discard Changes"
        cancelText="Cancel"
        danger={true}
      />
    </div>
  )
}
