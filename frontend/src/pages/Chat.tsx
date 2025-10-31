import { useCallback, useEffect, useRef, useState } from 'react'
import { Send, MessageSquare, Settings, Wrench, Activity, FileText, X, Minimize2, Maximize2, Trash2, XCircle } from 'lucide-react'
import { apiRequest } from '../utils/api'
import FileBrowser from '../components/FileBrowser'
import NoteEditor from '../components/NoteEditor'
import ConfirmationDialog from '../components/ConfirmationDialog'
import LoadingIndicator from '../components/LoadingIndicator'
import { ContextModal } from '../components/ContextModal'
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

interface WatchedContextNode {
  path: string
  name: string
  type: 'file' | 'directory'
  size?: number
  lastModified?: number
  children?: WatchedContextNode[]
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
      return 'border-[var(--color-info)] bg-[color-mix(in_srgb,var(--color-info)_10%,transparent)] text-[var(--color-info)]'
    case 'tool_result':
      return 'border-[var(--color-success)] bg-[color-mix(in_srgb,var(--color-success)_10%,transparent)] text-[var(--color-success)]'
    case 'assistant_thinking':
      return 'border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_10%,transparent)] text-[var(--color-accent)]'
    case 'error':
      return 'border-[var(--color-error)] bg-[color-mix(in_srgb,var(--color-error)_10%,transparent)] text-[var(--color-error)]'
    case 'warning':
      return 'border-[var(--color-warning)] bg-[color-mix(in_srgb,var(--color-warning)_10%,transparent)] text-[var(--color-warning)]'
    default:
      return 'border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]'
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
  const [contextFiles, setContextFiles] = useState<string[]>([])
  const [showContextModal, setShowContextModal] = useState(false)
  const [watchedFiles, setWatchedFiles] = useState<WatchedContextNode[]>([])
  const [recentlyViewedFiles, setRecentlyViewedFiles] = useState<string[]>([])
  const [contextBeingUsed, setContextBeingUsed] = useState(false)
  const [showUnsavedWarning, setShowUnsavedWarning] = useState(false)
  const [pendingFileSelection, setPendingFileSelection] = useState<string | null>(null)
  const [modifiedContextFiles, setModifiedContextFiles] = useState<Set<string>>(new Set())
  const [contextFilesMetadata, setContextFilesMetadata] = useState<Map<string, { lastModified: number, size: number }>>(new Map())
  const [showClearChatConfirmation, setShowClearChatConfirmation] = useState(false)

  // Resizable panel widths
  const [fileBrowserWidth, setFileBrowserWidth] = useState(280)
  const [chatPanelWidth, setChatPanelWidth] = useState(400)
  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fileUpdateEventSourceRef = useRef<EventSource | null>(null)
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

  // Load watched files for context modal
  useEffect(() => {
    const loadWatchedFiles = async () => {
      try {
        const response = await apiRequest('/api/files/watched')
        const directories = Array.isArray(response.directories) ? response.directories : []

        const formatted: WatchedContextNode[] = directories.map((directory: any) => {
          const dirChildren: WatchedContextNode[] = Array.isArray(directory.files)
            ? directory.files.map((file: any) => ({
                path: file?.relativePath || file?.path || '',
                name: file?.name || file?.relativePath || file?.path || 'Unknown file',
                type: 'file' as const,
                size: typeof file?.size === 'number' ? file.size : undefined,
                lastModified: typeof file?.lastModified === 'number' ? file.lastModified : undefined
              })).filter((child: WatchedContextNode) => Boolean(child.path))
            : []

          return {
            path: typeof directory?.path === 'string' && directory.path.length > 0
              ? directory.path
              : directory?.name || 'notes',
            name: directory?.name || directory?.path || 'notes',
            type: 'directory' as const,
            children: dirChildren
          }
        }).filter((node: any) => node.children && node.children.length > 0)

        setWatchedFiles(formatted as WatchedContextNode[])
      } catch (err) {
        console.error('Failed to load watched files:', err)
      }
    }
    loadWatchedFiles()
  }, [])

  // Auto-add selected file to context when file selection changes
  useEffect(() => {
    if (selectedFile && !contextFiles.includes(selectedFile)) {
      setContextFiles(prev => [selectedFile, ...prev])
    }
  }, [selectedFile])

  useEffect(() => {
    setMessages([
      {
        role: 'system',
        content: `You are an AI assistant for Obby, a file monitoring and note management system.

Context: Obby tracks file changes in a local repository, stores content in SQLite (obby.db), and provides semantic search through AI-analyzed notes. The notes directory contains documentation and tracked files.

Tools available:
- Grep: Search through notes and documentation with ripgrep
- Read: Inspect the contents of files under watch
- Write: Apply requested edits to files when instructed
- Bash: Run shell commands inside the project workspace

Guidelines:
- Be concise and direct in responses
- Always begin by searching the notes directory with the Grep tool before considering any other data source.
- Do not query SQLite or other databases unless the notes search clearly cannot answer the question.
- When using tools, proceed without announcing your actions
- Synthesize results rather than listing raw data
- Focus on answering the user's question efficiently`
      }
    ])

    loadAvailableTools()
    fetchCurrentModel()
    connectToFileUpdatesSSE()

    return () => {
      disconnectProgressSSE()
      disconnectFileUpdatesSSE()
    }
  }, [])

  const loadAvailableTools = async () => {
    try {
      const toolsInfo = await apiRequest<{ tool_names: string[]; tools: ToolSchema[] }>('/api/chat/tools')
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
      const pingResponse = await apiRequest<{ model?: string; claude_model?: string }>('/api/chat/ping')
      const model = pingResponse.claude_model || pingResponse.model || ''
      setCurrentModel(model)
    } catch (e) {
      console.warn('Failed to get model from ping endpoint:', e)
      setCurrentModel('')
    }
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading, streamingMessage])

  // Get display model name
  const getDisplayModel = () => {
    if (!currentModel) return ''
    
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

  // Monitor for modifications to context files and show notifications
  useEffect(() => {
    // Check which modified files are in our current context
    const modifiedInContext = contextFiles.filter(file => modifiedContextFiles.has(file))

    if (modifiedInContext.length > 0) {
      // Show notification for each modified context file
      modifiedInContext.forEach(file => {
        const fileName = file.split('/').pop() || file
        recordAgentAction('warning', `Context file updated: ${fileName}`,
          'File was modified - will fetch fresh content on next message', undefined)
      })
    }
  }, [modifiedContextFiles, contextFiles, recordAgentAction])

  const disconnectProgressSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setProgressMessage(null)
    setProgressType(null)
  }, [])

  const disconnectFileUpdatesSSE = useCallback(() => {
    if (fileUpdateEventSourceRef.current) {
      fileUpdateEventSourceRef.current.close()
      fileUpdateEventSourceRef.current = null
    }
  }, [])

  const connectToFileUpdatesSSE = useCallback(() => {
    // Don't reconnect if already connected
    if (fileUpdateEventSourceRef.current) {
      return
    }

    try {
      const eventSource = new EventSource('/api/files/updates/stream')
      fileUpdateEventSourceRef.current = eventSource

      eventSource.onopen = () => {
        console.log('Connected to file updates stream')
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const eventType = data.type

          if (!eventType || eventType === 'keepalive' || eventType === 'connected') {
            return
          }

          // Handle file modification events - track ALL modifications
          // We'll filter by context membership during rendering
          if (eventType === 'modified' && data.filePath) {
            const modifiedPath = data.filePath
            console.log(`File modified: ${modifiedPath}`)

            // Mark file as modified (track all modifications)
            setModifiedContextFiles(prev => new Set(prev).add(modifiedPath))
          }
        } catch (error) {
          console.error('Error parsing file update SSE message:', error)
        }
      }

      eventSource.onerror = (error) => {
        console.error('File updates SSE connection error:', error)
        if (fileUpdateEventSourceRef.current?.readyState === EventSource.CLOSED) {
          disconnectFileUpdatesSSE()
        }
      }
    } catch (error) {
      console.error('Failed to establish file updates SSE connection:', error)
    }
  }, [disconnectFileUpdatesSSE])

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
          } else if (eventType === 'cancelled') {
            actionType = 'warning'
            // Handle cancellation
            setLoading(false)
            setIsStreaming(false)
            setStreamingMessage('')
            setProgressMessage(null)
            setProgressType(null)
            recordAgentAction('warning', 'Agent operation cancelled', 'Operation was stopped by user', sessionId)
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

  const cancelAgent = useCallback(async () => {
    if (!currentSessionId || !loading) return
    
    try {
      const response = await apiRequest(`/api/chat/cancel/${currentSessionId}`, {
        method: 'POST'
      })
      
      if (response.success) {
        recordAgentAction('warning', 'Agent cancellation requested', 'Waiting for operation to stop...', currentSessionId)
      } else {
        recordAgentAction('error', 'Failed to cancel agent', response.message || 'Unknown error', currentSessionId)
      }
    } catch (error: any) {
      console.error('Failed to cancel agent:', error)
      recordAgentAction('error', 'Failed to cancel agent', error?.message || 'Unknown error', currentSessionId)
    }
  }, [currentSessionId, loading, recordAgentAction])

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

    // Include context files if any are selected
    if (contextFiles.length > 0) {
      setContextBeingUsed(true)
      try {
        const { fetchFileContent } = await import('../utils/fileOperations')

        // Fetch content for all context files
        const contextFilesData = []
        const orderedContextFiles = [...contextFiles]

        // Ensure selected file is first if it's in context
        if (selectedFile && orderedContextFiles.includes(selectedFile)) {
          orderedContextFiles.splice(orderedContextFiles.indexOf(selectedFile), 1)
          orderedContextFiles.unshift(selectedFile)
        }

        // Store metadata for freshness tracking
        const newMetadata = new Map<string, { lastModified: number, size: number }>()
        const failedFiles: string[] = []
        const validFiles: string[] = []

        // Validate and fetch each context file
        for (const filePath of orderedContextFiles) {
          try {
            const fileData = await fetchFileContent(filePath)

            // Store metadata
            newMetadata.set(filePath, {
              lastModified: fileData.lastModified,
              size: fileData.size
            })

            contextFilesData.push({
              ...fileData,
              path: filePath,
              isPrimary: filePath === selectedFile
            })

            validFiles.push(filePath)
          } catch (err: any) {
            // File doesn't exist or is not accessible
            console.warn(`Failed to fetch context file ${filePath}:`, err)
            failedFiles.push(filePath)

            // Record as warning
            recordAgentAction('warning', `Context file not found: ${filePath.split('/').pop()}`,
              'File has been removed from context', undefined)
          }
        }

        // Remove failed files from context
        if (failedFiles.length > 0) {
          setContextFiles(prev => prev.filter(f => !failedFiles.includes(f)))

          // Show error notification
          const fileNames = failedFiles.map(f => f.split('/').pop()).join(', ')
          recordAgentAction('error', `Removed ${failedFiles.length} missing file(s) from context`,
            `Files not found: ${fileNames}`, undefined)
        }

        // Update metadata and clear modified indicators (we just fetched fresh content)
        setContextFilesMetadata(newMetadata)
        setModifiedContextFiles(new Set())

        // If all context files failed, don't include context
        if (validFiles.length === 0 && contextFiles.length > 0) {
          recordAgentAction('error', 'All context files are missing',
            'Message will be sent without file context', undefined)
          setContextBeingUsed(false)
          // Continue without context
        }

        // Build context message with all files
        const contextParts = contextFilesData.map((fileData, index) => {
          const prefix = fileData.isPrimary 
            ? `[Context: User is currently viewing the file "${fileData.name}" at path "${fileData.path}" (Primary context)]`
            : `[Context: Additional file "${fileData.name}" at path "${fileData.path}"]`
          
          return `${prefix}\n\n\`\`\`markdown\n${fileData.content}\n\`\`\``
        }).join('\n\n---\n\n')

        const contextMessage = `${contextParts}\n\n---\n\nUser's question about these notes:`
        userMessage = `${contextMessage}\n\n${content}`

        recordAgentAction('progress', `Including ${contextFiles.length} file${contextFiles.length !== 1 ? 's' : ''} in context`, 
          contextFiles.map(f => f.split('/').pop()).join(', '), undefined)
      } catch (err) {
        console.error('Failed to fetch context files:', err)
        recordAgentAction('warning', 'Could not include some context files', String(err), undefined)
      }
    }

    const next = [...messagesToSend, { role: 'user' as Role, content: userMessage }]
    // Store display version separately
    const displayMessages = [...messagesToSend, { role: 'user' as Role, content: displayMessage }]
    setMessages(displayMessages)
    setInput('')
    setLoading(true)

    disconnectProgressSSE()

    const sessionId = `chat-${Date.now()}-${Math.random().toString(36).substring(7)}`
    setCurrentSessionId(sessionId)

    // Show preview of the query being sent
    const queryPreview = content.length > 80 ? content.slice(0, 80) + '...' : content
    recordAgentAction('progress', `Sending: "${queryPreview}"`, 'Provider: Claude Agent SDK', sessionId)

    setProgressMessage(null)
    setProgressType(null)
    connectToProgressSSE(sessionId)

    try {
      const res = await apiRequest<ChatCompletionResponse>(
        '/api/chat/agent_query',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: next, // Send messages with context to AI
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
          
          const newMessages = (res.conversation || []).filter(msg => {
            const messageId = `${msg.role}:${msg.content.substring(0, 50)}`
            return !existingMessageIds.includes(messageId)
          })

          // Clean user messages to match displayMessage
          const currentDisplayMessage = displayMessage // Capture current value to avoid stale closure
          const cleanNewMessages = newMessages.map(msg =>
            msg.role === 'user' && msg.content !== currentDisplayMessage ?
              { ...msg, content: currentDisplayMessage } : msg
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
      
      // Handle cancellation response
      if (e?.cancelled || e?.status === 499 || errorMessage.includes('cancelled')) {
        setLoading(false)
        setIsStreaming(false)
        setStreamingMessage('')
        setProgressMessage(null)
        setProgressType(null)
        setContextBeingUsed(false)
        recordAgentAction('warning', 'Agent operation cancelled', 'Operation was stopped', sessionId)
        return
      }

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
    setRecentlyViewedFiles(prev => {
      const updated = [filePath, ...prev.filter((f) => f !== filePath)]
      return updated.slice(0, 8)
    })
  }, [])

  const handleFileBrowserToggle = useCallback(() => {
    setFileBrowserOpen(prev => !prev)
  }, [])

  const refreshContextMetadata = useCallback(async () => {
    if (contextFiles.length === 0) return

    try {
      const { fetchFileContent } = await import('../utils/fileOperations')
      const newMetadata = new Map<string, { lastModified: number, size: number }>()

      // Fetch fresh metadata for all context files
      for (const filePath of contextFiles) {
        try {
          const fileData = await fetchFileContent(filePath)
          newMetadata.set(filePath, {
            lastModified: fileData.lastModified,
            size: fileData.size
          })
        } catch (error) {
          console.warn(`Failed to refresh metadata for ${filePath}:`, error)
        }
      }

      // Update metadata and clear modified indicators
      setContextFilesMetadata(newMetadata)
      setModifiedContextFiles(new Set())

      recordAgentAction('progress', 'Context files refreshed',
        `Updated metadata for ${newMetadata.size} file(s)`, undefined)
    } catch (error) {
      console.error('Failed to refresh context metadata:', error)
      recordAgentAction('error', 'Failed to refresh context',
        String(error), undefined)
    }
  }, [contextFiles, recordAgentAction])

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

  const clearChat = useCallback(() => {
    // Reset to initial system message only
    setMessages([
      {
        role: 'system',
        content: `You are an AI assistant for Obby, a file monitoring and note management system.

Context: Obby tracks file changes in a local repository, stores content in SQLite (obby.db), and provides semantic search through AI-analyzed notes. The notes directory contains documentation and tracked files.

Tools available:
- Grep: Search through notes and documentation with ripgrep
- Read: Inspect the contents of files under watch
- Write: Apply requested edits to files when instructed
- Bash: Run shell commands inside the project workspace

Guidelines:
- Be concise and direct in responses
- Always begin by searching the notes directory with the Grep tool before considering any other data source.
- Do not query SQLite or other databases unless the notes search clearly cannot answer the question.
- When using tools, proceed without announcing your actions
- Synthesize results rather than listing raw data
- Focus on answering the user's question efficiently`
      }
    ])

    // Clear all chat-related state
    setInput('')
    setError(null)
    setLoading(false)
    setProgressMessage(null)
    setProgressType(null)
    setAgentActions([])
    setCurrentSessionId(null)
    setStreamingMessage('')
    setIsStreaming(false)
    setContextBeingUsed(false)

    // Disconnect SSE connections
    disconnectProgressSSE()

    setShowClearChatConfirmation(false)
  }, [disconnectProgressSSE])

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
                        (Claude {getDisplayModel()})
                      </span>
                    </>
                  )}
                </span>
              </div>

              <div className="flex items-center space-x-2">
                {/* Context files indicator */}
                {contextFiles.length > 0 ? (
                  <div
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs cursor-pointer transition-colors ${
                      contextFiles.some(f => modifiedContextFiles.has(f))
                        ? 'bg-[color-mix(in_srgb,var(--color-warning)_20%,transparent)] text-[var(--color-warning)] hover:bg-[color-mix(in_srgb,var(--color-warning)_30%,transparent)]'
                        : 'bg-[color-mix(in_srgb,var(--color-info)_20%,transparent)] text-[var(--color-info)] hover:bg-[color-mix(in_srgb,var(--color-info)_30%,transparent)]'
                    }`}
                    onClick={() => setShowContextModal(true)}
                    title={contextFiles.some(f => modifiedContextFiles.has(f))
                      ? "Context files modified - click to manage"
                      : "Click to manage context files"}
                  >
                    <FileText className="h-3 w-3" />
                    <span>
                      {contextFiles.length === 1 ? contextFiles[0].split('/').pop() : `${contextFiles.length} files`}
                    </span>
                    {contextFiles.some(f => modifiedContextFiles.has(f)) ? (
                      <div className="w-1.5 h-1.5 bg-[var(--color-warning)] rounded-full animate-pulse" title="Context files modified - fresh content will be fetched"></div>
                    ) : (
                      <div className="w-1.5 h-1.5 bg-[var(--color-info)] rounded-full animate-pulse" title="Context included in background"></div>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setContextFiles([])
                      }}
                      className="hover:bg-opacity-70 rounded p-0.5"
                      title="Clear all context"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowContextModal(true)}
                    className="px-2 py-1 bg-[color-mix(in_srgb,var(--color-info)_20%,transparent)] text-[var(--color-info)] rounded-lg text-xs hover:bg-[color-mix(in_srgb,var(--color-info)_30%,transparent)] transition-colors"
                    title="Add context files"
                  >
                    + Add Context
                  </button>
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
                {/* Context files indicator */}
                {contextFiles.length > 0 ? (
                  <div
                    className={`flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border transition-colors cursor-pointer ${
                      contextFiles.some(f => modifiedContextFiles.has(f))
                        ? 'border-amber-400/50 bg-amber-500/20 hover:bg-amber-500/30'
                        : 'border-white/30 bg-white/10 hover:bg-white/20'
                    }`}
                    onClick={() => setShowContextModal(true)}
                    title={contextFiles.some(f => modifiedContextFiles.has(f))
                      ? "Context files modified - click to manage"
                      : "Click to manage context files"}
                  >
                    <FileText className="h-4 w-4" />
                    <span className="text-sm font-medium">
                      {contextFiles.length === 1 ? contextFiles[0].split('/').pop() : `Context: ${contextFiles.length} files`}
                    </span>
                    {contextFiles.some(f => modifiedContextFiles.has(f)) ? (
                      <>
                        <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" title="Context files modified"></div>
                        <span className="text-xs opacity-75">(modified)</span>
                      </>
                    ) : (
                      <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" title="Context included in background"></div>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setContextFiles([])
                      }}
                      className="ml-1 hover:bg-white/20 rounded p-0.5 transition-colors"
                      title="Clear all context"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowContextModal(true)}
                    className="px-4 py-2 rounded-full backdrop-blur-sm border border-white/30 bg-white/10 hover:bg-white/20 text-white font-medium text-sm transition-colors"
                  >
                    + Add Context Files
                  </button>
                )}

                <div className="flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border border-white/30 bg-white/10">
                  <Wrench className="h-4 w-4" />
                  <span className="text-sm font-medium">
                    Claude
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
                contextFiles={contextFiles}
                onContextToggle={(filePath, isSelected) => {
                  setContextFiles(prev => {
                    if (isSelected) {
                      return [...prev, filePath]
                    } else {
                      return prev.filter(f => f !== filePath)
                    }
                  })
                }}
              />
            </div>
            {/* Left resize handle */}
            <div
              onMouseDown={handleMouseDownLeft}
              className="w-1 flex-shrink-0 bg-[var(--color-border)] hover:bg-[var(--color-primary)] cursor-col-resize transition-colors"
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
            contextFiles={contextFiles}
            onContextToggle={(filePath, isSelected) => {
              setContextFiles(prev => {
                if (isSelected) {
                  return [...prev, filePath]
                } else {
                  return prev.filter(f => f !== filePath)
                }
              })
            }}
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
          className="w-1 flex-shrink-0 bg-[var(--color-border)] hover:bg-[var(--color-primary)] cursor-col-resize transition-colors"
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
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    Chat now runs exclusively on the Claude Agent SDK.
                  </p>
                </div>

                {availableTools.length > 0 && (
                  <div className="pt-2 border-t border-gray-200">
                    <div className="text-sm font-medium mb-2">Available Tools</div>
                    <div className="text-xs text-gray-600 mb-2">
                      Claude Agent SDK can use these tools for enhanced functionality
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
                {contextFiles.length > 0 && (
                  <p className="text-xs mt-2 text-blue-600 dark:text-blue-400">
                    📄 {contextFiles.length === 1 ? 'Note context' : 'Multiple notes'} will be included in the background
                  </p>
                )}
              </div>
            )}
            <div className="space-y-3">
              {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').map((m, idx) => (
                <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.role === 'user' ? (
                    <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap bg-[var(--color-primary)] text-[var(--color-text-inverse)] relative">
                      {m.content}
                      {contextBeingUsed && idx === messages.filter((msg) => msg.role !== 'system' && msg.role !== 'tool').length - 1 && (
                        <div className="absolute -top-2 -right-2 w-4 h-4 bg-[var(--color-accent)] rounded-full animate-pulse" title="Context included in background">
                          <FileText className="h-2.5 w-2.5 text-[var(--color-text-inverse)] mx-auto mt-0.5" />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm bg-[var(--color-surface)] text-[var(--color-text-primary)] border border-[var(--color-border)]">
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
                  <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm bg-[var(--color-surface)] text-[var(--color-text-primary)] border border-[var(--color-border)]">
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
                className="w-full border border-[var(--color-border)] rounded-md px-3 py-2 bg-[var(--color-surface)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)] text-sm"
                placeholder="Type your message…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                disabled={loading}
              />
              <div className="flex gap-2">
                {loading ? (
                  <button
                    onClick={cancelAgent}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                    title="Stop agent operation"
                  >
                    <XCircle className="h-4 w-4" />
                    Stop Agent
                  </button>
                ) : (
                  <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-[var(--color-primary)] text-[var(--color-text-inverse)] hover:bg-[color-mix(in_srgb,var(--color-primary)_80%,black)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                  >
                    <Send className="h-4 w-4" />
                    Send
                  </button>
                )}
                <button
                  onClick={() => setShowClearChatConfirmation(true)}
                  disabled={loading || messages.filter((m) => m.role !== 'system').length === 0}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                  title="Clear chat history"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
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

      {/* Clear chat confirmation dialog */}
      <ConfirmationDialog
        isOpen={showClearChatConfirmation}
        onClose={() => setShowClearChatConfirmation(false)}
        onConfirm={clearChat}
        title="Clear Chat History"
        message="Are you sure you want to clear the entire chat history? This action cannot be undone."
        confirmText="Clear Chat"
        cancelText="Cancel"
        danger={true}
      />

      {/* Context management modal */}
      <ContextModal
        isOpen={showContextModal}
        onClose={() => setShowContextModal(false)}
        currentContextFiles={contextFiles}
        onContextChange={setContextFiles}
        watchedFiles={watchedFiles}
        currentViewedFile={selectedFile || undefined}
        modifiedFiles={modifiedContextFiles}
        filesMetadata={contextFilesMetadata}
        recentlyViewedFiles={recentlyViewedFiles}
        onRefreshContext={refreshContextMetadata}
      />
    </div>
  )
}
