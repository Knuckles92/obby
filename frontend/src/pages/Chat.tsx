import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Send, MessageSquare, Settings, Wrench, Activity, FileText, X, Minimize2, Maximize2, Trash2, XCircle, Loader2, AlertTriangle } from 'lucide-react'
import { apiRequest } from '../utils/api'
import FileBrowser from '../components/FileBrowser'
import NoteEditor from '../components/NoteEditor'
import ConfirmationDialog from '../components/ConfirmationDialog'
import LoadingIndicator from '../components/LoadingIndicator'
import ActivityTimeline from '../components/ActivityTimeline'
import { ContextModal } from '../components/ContextModal'
import FileReference from '../components/FileReference'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

type Role = 'system' | 'user' | 'assistant' | 'tool'

interface FileReference {
  path: string
  action?: 'read' | 'modified' | 'mentioned' | 'created'
}

interface AgentAction {
  id: string
  type: AgentActionType
  label: string
  detail?: string
  timestamp: string
  sessionId?: string
}

interface ChatMessage {
  role: Role
  content: string
  tool_calls?: any[]
  tool_call_id?: string
  name?: string
  fileReferences?: FileReference[]
  actions?: AgentAction[]  // Actions that occurred during this turn (for assistant messages)
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

type CancelPhase = 'idle' | 'cancelling' | 'force-killing' | 'cancelled' | 'failed'

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
  const location = useLocation()
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
  const [streamingFileReferences, setStreamingFileReferences] = useState<FileReference[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  // Activity timeline and cancel phase state
  const [timelineExpanded, setTimelineExpanded] = useState(true)
  const [expandedHistoryTimelines, setExpandedHistoryTimelines] = useState<Set<number>>(new Set())
  const [cancelPhase, setCancelPhase] = useState<CancelPhase>('idle')
  const [cancelMessage, setCancelMessage] = useState('')
  const cancelTimeoutRef = useRef<NodeJS.Timeout | null>(null)

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
  const currentTurnActionsRef = useRef<AgentAction[]>([])  // Track actions for attaching to messages

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

  // Handle file selection from navigation state (e.g., from Summary Notes links)
  // Note: handleFileSelect is defined later in the component, but useCallback ensures stable reference
  useEffect(() => {
    if ((location.state as any)?.selectedFile) {
      // Select file by setting state directly to avoid dependency issues
      setSelectedFile((location.state as any).selectedFile)
      setRecentlyViewedFiles(prev => {
        const updated = [(location.state as any).selectedFile, ...prev.filter((f) => f !== (location.state as any).selectedFile)]
        return updated.slice(0, 8)
      })
      // Clear the state so it doesn't persist on navigation
      window.history.replaceState({}, document.title)
    }
  }, [location.state?.selectedFile])

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
    // Initialize with empty messages array - system prompt is handled by backend
    setMessages([])

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

  // When loading finishes, ensure the last assistant message has actions attached
  const prevLoadingRef = useRef(loading)
  useEffect(() => {
    // Detect when loading transitions from true to false
    if (prevLoadingRef.current && !loading) {
      // Delay slightly to allow any pending SSE events to be processed
      const timeoutId = setTimeout(() => {
        // Loading just finished - attach actions to last assistant message if missing
        const actions = [...currentTurnActionsRef.current]
        if (actions.length > 0) {
          setMessages(prev => {
            // Find last assistant message
            const lastIdx = prev.length - 1
            if (lastIdx >= 0 && prev[lastIdx].role === 'assistant' && !prev[lastIdx].actions) {
              // Attach actions to last assistant message
              const updated = [...prev]
              updated[lastIdx] = { ...updated[lastIdx], actions }
              return updated
            }
            return prev
          })
        }
      }, 100)
      return () => clearTimeout(timeoutId)
    }
    prevLoadingRef.current = loading
  }, [loading])

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
    // Update ref synchronously BEFORE state update (state callbacks are async)
    if (!currentTurnActionsRef.current.some((existing) => existing.id === action.id)) {
      currentTurnActionsRef.current = [...currentTurnActionsRef.current, action].slice(-120)
    }
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
            setStreamingFileReferences([])
            setIsStreaming(true)
            return
          }

          // Handle file references (may come before or during message)
          if (eventType === 'file_references') {
            const fileRefs = data.fileReferences || []
            if (fileRefs.length > 0) {
              setStreamingFileReferences(fileRefs)
              recordAgentAction('progress', `Referenced ${fileRefs.length} file(s)`, null, sessionId)
            }
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

          // Handle assistant message turn completing
          if (eventType === 'assistant_message_complete') {
            const content = data.content || streamingMessage
            if (content) {
              // Capture current actions for this turn
              const turnActions = [...currentTurnActionsRef.current]
              // Use file references from event data or accumulated ones
              const fileRefs = data.fileReferences || (streamingFileReferences.length > 0 ? streamingFileReferences : undefined)
              // Add completed message to conversation with any accumulated file references and actions
              setMessages((prev) => [...prev, {
                role: 'assistant',
                content,
                fileReferences: fileRefs,
                actions: turnActions.length > 0 ? turnActions : undefined
              }])
              setStreamingMessage('')
              setStreamingFileReferences([])
            }
            setIsStreaming(false)
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
          } else if (eventType === 'cancelling') {
            actionType = 'warning'
            // Handle cancellation in progress
            const phase = extras.phase
            if (phase === 'graceful') {
              setCancelPhase('cancelling')
              setCancelMessage('Stopping agent...')
            } else if (phase === 'force') {
              setCancelPhase('force-killing')
              setCancelMessage("Agent didn't respond, forcing stop...")
            }
            recordAgentAction('warning', data.message || 'Cancellation in progress', `Phase: ${phase}`, sessionId)
            return // Don't record duplicate action below
          } else if (eventType === 'cancelled') {
            actionType = 'warning'
            // Handle cancellation complete
            const phase = extras.phase || 'unknown'
            const wasForced = phase.includes('force')
            setCancelPhase('cancelled')
            setCancelMessage(wasForced ? 'Agent force stopped' : 'Agent stopped')
            setLoading(false)
            setIsStreaming(false)
            setStreamingMessage('')
            setProgressMessage(null)
            setProgressType(null)
            // Clear cancel timeout if set
            if (cancelTimeoutRef.current) {
              clearTimeout(cancelTimeoutRef.current)
              cancelTimeoutRef.current = null
            }
            recordAgentAction('warning', 'Agent operation cancelled', `Phase: ${phase}`, sessionId)
            // Reset cancel phase after delay
            setTimeout(() => {
              setCancelPhase('idle')
              setCancelMessage('')
            }, 2000)
            return // Don't record duplicate action below
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
            // Reset cancel phase on normal completion
            if (cancelTimeoutRef.current) {
              clearTimeout(cancelTimeoutRef.current)
              cancelTimeoutRef.current = null
            }
            setCancelPhase('idle')
            setCancelMessage('')
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
    // Prevent multiple cancel requests
    if (cancelPhase !== 'idle') return

    setCancelPhase('cancelling')
    setCancelMessage('Stopping agent...')

    // Safety timeout - force clear loading state after 15 seconds if SSE events never arrive
    cancelTimeoutRef.current = setTimeout(() => {
      if (loading) {
        setLoading(false)
        setIsStreaming(false)
        setStreamingMessage('')
        setProgressMessage(null)
        setProgressType(null)
        setCancelPhase('idle')
        setCancelMessage('')
        recordAgentAction('warning', 'Stop timeout - cleared state',
          'Backend may still be processing. If issues persist, please refresh.', currentSessionId)
      }
    }, 15000)

    try {
      const response = await apiRequest(`/api/chat/cancel/${currentSessionId}`, {
        method: 'POST'
      })

      if (response.success) {
        recordAgentAction('warning', 'Agent cancellation requested', 'Waiting for operation to stop...', currentSessionId)
      } else {
        // Clear timeout on failure
        if (cancelTimeoutRef.current) {
          clearTimeout(cancelTimeoutRef.current)
          cancelTimeoutRef.current = null
        }
        setCancelPhase('failed')
        setCancelMessage('Failed to stop')
        recordAgentAction('error', 'Failed to cancel agent', response.message || 'Unknown error', currentSessionId)
        // Reset failed state after delay
        setTimeout(() => {
          setCancelPhase('idle')
          setCancelMessage('')
        }, 3000)
      }
    } catch (error: any) {
      // Clear timeout on error
      if (cancelTimeoutRef.current) {
        clearTimeout(cancelTimeoutRef.current)
        cancelTimeoutRef.current = null
      }
      console.error('Failed to cancel agent:', error)
      setCancelPhase('failed')
      setCancelMessage('Failed to stop')
      recordAgentAction('error', 'Failed to cancel agent', error?.message || 'Unknown error', currentSessionId)
      // Reset failed state after delay
      setTimeout(() => {
        setCancelPhase('idle')
        setCancelMessage('')
      }, 3000)
    }
  }, [currentSessionId, loading, cancelPhase, recordAgentAction])

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || loading) return
    setError(null)

    // Reset streaming state and clear actions for new turn
    setStreamingMessage('')
    setStreamingFileReferences([])
    setIsStreaming(false)
    setAgentActions([])  // Clear actions for new turn
    currentTurnActionsRef.current = []  // Clear ref too

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

      // Capture current actions for this turn before adding messages
      const turnActions = [...currentTurnActionsRef.current]

      // Handle conversation responses (multiple messages)
      // Note: SSE may have already added the assistant message - we need robust deduplication
      if (Array.isArray(res.conversation) && res.conversation.length > 0) {
        setMessages((prevMessages) => {
          // Create fingerprints using more content for better deduplication
          const createFingerprint = (m: ChatMessage) => `${m.role}:${m.content.substring(0, 200)}`
          const existingFingerprints = new Set(prevMessages.map(createFingerprint))

          // Filter to only truly new messages
          const newMessages = (res.conversation || []).filter(msg => {
            const fingerprint = createFingerprint(msg as ChatMessage)
            return !existingFingerprints.has(fingerprint)
          })

          // If no new messages, don't modify state
          if (newMessages.length === 0) {
            return prevMessages
          }

          // Clean user messages to match displayMessage, but preserve fileReferences for assistant messages
          // Also attach actions to the last assistant message (only if it doesn't already have actions)
          const currentDisplayMessage = displayMessage // Capture current value to avoid stale closure
          const assistantMsgCount = newMessages.filter(m => m.role === 'assistant').length
          let assistantIdx = 0
          const cleanNewMessages = newMessages.map(msg => {
            if (msg.role === 'user' && msg.content !== currentDisplayMessage) {
              return { ...msg, content: currentDisplayMessage }
            }
            // Attach actions to the last assistant message of this turn (only if not already present)
            if (msg.role === 'assistant') {
              assistantIdx++
              if (assistantIdx === assistantMsgCount && turnActions.length > 0 && !msg.actions) {
                return { ...msg, actions: turnActions }
              }
            }
            // Preserve all fields including fileReferences
            return msg
          })

          return [...prevMessages, ...cleanNewMessages]
        })
      }
      // Handle single reply responses (only if not already added by SSE)
      else if (reply) {
        setMessages((prev) => {
          // Check if this reply was already added by SSE
          const alreadyExists = prev.some(m =>
            m.role === 'assistant' && m.content.substring(0, 200) === reply.substring(0, 200)
          )
          if (alreadyExists) {
            return prev
          }
          return [...prev, {
            role: 'assistant',
            content: reply,
            actions: turnActions.length > 0 ? turnActions : undefined
          }]
        })
      }

      // Clear streaming state after final message is received
      setStreamingMessage('')
      setStreamingFileReferences([])
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
        setStreamingFileReferences([])
        setProgressMessage(null)
        setProgressType(null)
        setContextBeingUsed(false)
        recordAgentAction('warning', 'Agent operation cancelled', 'Operation was stopped', sessionId)
        return
      }

      // Clear streaming state on error
      setStreamingMessage('')
      setStreamingFileReferences([])
      setIsStreaming(false)

      // Reset context being used indicator
      setContextBeingUsed(false)
      setError(errorMessage)
      recordAgentAction('error', 'Chat request failed', errorMessage, sessionId)
    } finally {
      setLoading(false)
      // Delay disconnecting SSE to allow pending events to be processed
      setTimeout(() => {
        disconnectProgressSSE()
      }, 500)
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

  /**
   * showFile - Primary method for opening files from links and references
   * Normalizes file paths and displays them in the file viewer
   * @param path - File path (can be absolute or relative)
   */
  const showFile = useCallback((path: string) => {
    if (!path) return

    // Normalize the file path
    let normalizedPath = path

    // Convert backslashes to forward slashes (Windows paths)
    normalizedPath = normalizedPath.replace(/\\/g, '/')

    // Remove common absolute path prefixes to get project-relative path
    // Handle Windows absolute paths (e.g., D:/Python Projects/obby/frontend/src/...)
    normalizedPath = normalizedPath.replace(/^[A-Z]:[\/].*?obby[\/]/i, '')

    // Handle Unix absolute paths (e.g., /mnt/d/Python Projects/obby/frontend/src/...)
    normalizedPath = normalizedPath.replace(/^\/mnt\/[a-z]\/.*?obby[\/]/i, '')
    normalizedPath = normalizedPath.replace(/^\/.*?obby[\/]/i, '')

    // Remove leading slash if present (ensure it's relative)
    normalizedPath = normalizedPath.replace(/^\/+/, '')

    // Call the file selection handler
    handleFileSelect(normalizedPath)
  }, [handleFileSelect])

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

Context: Obby tracks file changes in a local repository, stores content in SQLite (.db/obby.db), and provides semantic search through AI-analyzed notes. The notes directory contains documentation and tracked files.

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
- Focus on answering the user's question efficiently

File References:
When mentioning files in your response, format them as inline code with the full relative path:
- Correct format: \`frontend/src/Chat.tsx\` or \`backend.py\` or \`routes/chat.py\`
- Incorrect format: frontend/src/Chat.tsx (plain text without backticks)
- Always use project-relative paths (e.g., \`frontend/src/Chat.tsx\` not \`/mnt/d/Python Projects/obby/frontend/src/Chat.tsx\`)
- Include the path when useful for clarity (e.g., \`routes/chat.py\` instead of just \`chat.py\` if there are multiple chat.py files)
- Never include absolute path prefixes like '/mnt/d/', 'D:/', or '/obby/'

Response Format:
When you reference, read, modify, or create files during your response, you MUST return a structured JSON response with the following format:
{
  "message": "Your response text in markdown format with inline code file references",
  "fileReferences": [
    {
      "path": "relative/path/to/file.md",
      "action": "read" | "modified" | "created" | "mentioned"
    }
  ]
}

File Reference Actions:
- "read": Files you read or searched through to answer the question
- "modified": Files you edited or updated
- "created": New files you created
- "mentioned": Files you reference in your response without directly accessing

If you do not reference any files, return a simple text response instead of JSON.`
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
    setStreamingFileReferences([])
    setIsStreaming(false)
    setContextBeingUsed(false)
    setExpandedHistoryTimelines(new Set())
    currentTurnActionsRef.current = []

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

  /**
   * Determines if a string looks like a file path that should be clickable.
   * Used to make file references in AI responses interactive.
   */
  const isFilePathLike = (text: string): boolean => {
    if (!text || text.length < 2) return false
    
    // Exclude obvious non-paths
    // - Pure numbers or simple numeric expressions
    if (/^\d+(\.\d+)?$/.test(text)) return false
    // - Common code literals
    if (/^(true|false|null|undefined|NaN|Infinity|None|True|False)$/i.test(text)) return false
    // - Shell commands (without looking like paths)
    if (/^(npm|yarn|pnpm|pip|git|cd|ls|rm|mv|cp|mkdir|cat|echo|grep|curl|wget|node|python|ruby)\s/i.test(text)) return false
    // - Function calls like `functionName()` or `func(args)`
    if (/^\w+\([^)]*\)$/.test(text)) return false
    // - Variable assignments or comparisons
    if (/[=<>!]/.test(text)) return false
    // - Array/object literals
    if (/^[\[{]/.test(text) || /[\]}]$/.test(text)) return false
    // - Strings with spaces (usually not file paths in this context)
    if (/\s/.test(text)) return false
    
    // Comprehensive file extension list
    const fileExtensions = /\.(tsx?|jsx?|mjs|cjs|py|pyw|pyi|md|mdx|markdown|json|jsonc|ya?ml|txt|text|css|scss|sass|less|styl|html?|htm|xml|xsl|xslt|sh|bash|zsh|fish|ps1|bat|cmd|rs|go|mod|sum|java|kt|kts|scala|sbt|c|cpp|cc|cxx|h|hpp|hxx|hh|cs|csx|fs|fsx|fsi|vb|vbs|rb|rake|gemspec|php|phtml|pl|pm|t|lua|r|rmd|jl|swift|m|mm|sql|sqlite|db|sqlite3|toml|ini|cfg|conf|config|env|local|example|sample|lock|log|csv|tsv|xml|svg|wasm|wat|proto|graphql|gql|tf|tfvars|hcl|dockerfile|makefile|cmake|ninja|gradle|pom|cabal|cargo|mix|rebar|gitignore|gitattributes|gitmodules|dockerignore|editorconfig|prettierrc|prettierignore|eslintrc|eslintignore|babelrc|nvmrc|npmrc|yarnrc|browserslistrc|stylelintrc|obbywatch|obbyignore)$/i

    // Check 1: Has a recognized file extension with valid path characters
    if (fileExtensions.test(text)) {
      // Valid path characters (alphanumeric, dots, hyphens, underscores, slashes)
      return /^[\w.\-/\\@]+$/.test(text)
    }
    
    // Check 2: Dot-files without extension (like .gitignore, .env, .obbywatch)
    if (/^\.[\w][\w.-]*$/.test(text) && !text.includes('/') && !text.includes('\\')) {
      return true
    }
    
    // Check 3: Path with directory separators (like frontend/src/utils)
    if ((text.includes('/') || text.includes('\\')) && /^[\w.\-/\\@]+$/.test(text)) {
      const segments = text.split(/[/\\]/).filter(Boolean)
      // At least one segment that looks like a directory/file name
      if (segments.length >= 1 && segments.every(s => s.length > 0 && !/^\.{2,}$/.test(s))) {
        // Ensure at least one segment has a letter (not just dots/numbers)
        return segments.some(s => /[a-zA-Z]/.test(s))
      }
    }
    
    return false
  }

  /**
   * Parses text and returns an array of React nodes with file paths made clickable.
   * Detects file paths in quotes ("path/to/file.tsx" or 'path/to/file.tsx')
   * and standalone paths that look like file references.
   */
  const renderTextWithClickableFilePaths = (text: string): React.ReactNode[] => {
    const result: React.ReactNode[] = []
    
    // Pattern to match:
    // 1. Quoted paths: "path/to/file.ext" or 'path/to/file.ext'
    // 2. Standalone paths with directory structure and extension
    const filePathPattern = /["']([^"'\s]+)["']|(?<![a-zA-Z0-9_])([a-zA-Z0-9_@][a-zA-Z0-9_\-./@\\]*[a-zA-Z0-9_])(?![a-zA-Z0-9_])/g
    
    let lastIndex = 0
    let match: RegExpExecArray | null
    let keyIndex = 0
    
    while ((match = filePathPattern.exec(text)) !== null) {
      // Get the captured path (either from quoted group or standalone group)
      const capturedPath = match[1] || match[2]
      
      // Skip if the captured text doesn't look like a file path
      if (!capturedPath || !isFilePathLike(capturedPath)) {
        continue
      }
      
      // Add text before this match
      if (match.index > lastIndex) {
        const beforeText = text.slice(lastIndex, match.index)
        result.push(beforeText)
      }
      
      // Determine if it was quoted (match[1] is the quoted capture group)
      const wasQuoted = match[1] !== undefined
      
      // Add the clickable file path element
      result.push(
        <span
          key={`file-${keyIndex++}`}
          className="cursor-pointer hover:bg-[var(--color-primary)] hover:text-[var(--color-text-inverse)] transition-colors px-1 py-0.5 rounded bg-[color-mix(in_srgb,var(--color-primary)_20%,transparent)] text-[var(--color-primary)] font-mono text-sm"
          onClick={() => showFile(capturedPath)}
          title={`Click to open: ${capturedPath}`}
        >
          {wasQuoted ? `"${capturedPath}"` : capturedPath}
        </span>
      )
      
      lastIndex = match.index + match[0].length
    }
    
    // Add any remaining text after the last match
    if (lastIndex < text.length) {
      result.push(text.slice(lastIndex))
    }
    
    // If no matches were found, return the original text
    if (result.length === 0) {
      return [text]
    }
    
    return result
  }

  // Markdown components for chat messages
  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '')

      // Handle code blocks (not inline)
      if (!inline && match) {
        return (
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            {...props}
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
        )
      }

      // Handle inline code - check if it looks like a file path
      if (inline) {
        const codeText = String(children)

        if (isFilePathLike(codeText)) {
          return (
            <code
              className={`${className || ''} cursor-pointer hover:bg-[var(--color-primary)] hover:text-[var(--color-text-inverse)] transition-colors px-2 py-0.5 rounded bg-[color-mix(in_srgb,var(--color-primary)_20%,transparent)] text-[var(--color-primary)] font-mono text-sm`}
              onClick={() => showFile(codeText)}
              title={`Click to open: ${codeText}`}
              {...props}
            >
              {children}
            </code>
          )
        }
      }

      // Regular inline code (not a file path)
      return (
        <code className={className} {...props}>
          {children}
        </code>
      )
    },
    a({ node, children, href, ...props }: any) {
      // Check if the link looks like a file path (no protocol, and passes file path detection)
      const looksLikeFilePath = href && !href.match(/^[a-z]+:\/\//) && isFilePathLike(href)

      if (looksLikeFilePath) {
        return (
          <button
            onClick={(e) => {
              e.preventDefault()
              showFile(href)
            }}
            className="text-[var(--color-primary)] hover:underline cursor-pointer bg-transparent border-none p-0 font-inherit"
            title={`Click to open: ${href}`}
          >
            {children}
          </button>
        )
      }

      // Regular external links
      return (
        <a href={href} {...props} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      )
    },
    p({ children, ...props }: any) {
      // Process paragraph children to make file paths clickable
      const processChildren = (childElements: React.ReactNode): React.ReactNode => {
        return React.Children.map(childElements, (child, index) => {
          // Only process string children (text nodes)
          if (typeof child === 'string') {
            const processed = renderTextWithClickableFilePaths(child)
            // If processing returned multiple elements or different content, wrap in fragment
            if (processed.length === 1 && processed[0] === child) {
              return child // No changes needed
            }
            return <React.Fragment key={`text-${index}`}>{processed}</React.Fragment>
          }
          // Return other elements (like code, links, etc.) unchanged
          return child
        })
      }

      return <p {...props}>{processChildren(children)}</p>
    }
  }

  return (
    <div className="h-[94dvh] flex flex-col m-0 p-0">
      {/* Header */}
      <div className={`flex-shrink-0 transition-all duration-300 ${
        headerMinimized 
          ? 'border-b border-[var(--color-border)] bg-[var(--color-background)]' 
          : ''
      }`}>
        {headerMinimized ? (
          /* Compact Header */
          <div className="px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-1.5 bg-[color-mix(in_srgb,var(--color-primary)_20%,transparent)] rounded-lg">
                  <MessageSquare className="h-4 w-4 text-[var(--color-primary)]" />
                </div>
                <span className="font-medium text-[var(--color-text-primary)]">
                  Chat
                  {currentModel && (
                    <>
                      {' '}
                      <span className="text-xs text-[var(--color-text-secondary)]">
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
                  className="p-1.5 rounded-lg hover:bg-[var(--color-hover)] text-[var(--color-text-secondary)]"
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
          className="flex-shrink-0 border-l border-[var(--color-border)] bg-[var(--color-background)] flex flex-col"
        >
          {showSettings && (
            <div className="flex-shrink-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] p-4">
              <h3 className="font-semibold mb-3 text-[var(--color-text-primary)]">Chat Settings</h3>
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-medium mb-2 text-[var(--color-text-primary)]">AI Provider</div>
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    Chat now runs exclusively on the Claude Agent SDK.
                  </p>
                </div>

                {availableTools.length > 0 && (
                  <div className="pt-2 border-t border-[var(--color-border)]">
                    <div className="text-sm font-medium mb-2 text-[var(--color-text-primary)]">Available Tools</div>
                    <div className="text-xs text-[var(--color-text-secondary)] mb-2">
                      Claude Agent SDK can use these tools for enhanced functionality
                    </div>
                    <ul className="space-y-1">
                      {availableTools.map((tool) => (
                        <li key={tool.name} className="rounded border border-[var(--color-border)] bg-[var(--color-background)] px-2 py-1">
                          <div className="text-xs font-semibold text-[var(--color-text-primary)]">{tool.name}</div>
                          {tool.description && (
                            <div className="text-xs text-[var(--color-text-secondary)]">{tool.description}</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={scrollRef} className="flex-1 min-h-0 overflow-auto p-4 bg-[var(--color-surface)]">
            {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').length === 0 && (
              <div className="text-[var(--color-text-secondary)] text-sm text-center py-8">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Start a conversation</p>
                {contextFiles.length > 0 && (
                  <p className="text-xs mt-2 text-[var(--color-info)]">
                    📄 {contextFiles.length === 1 ? 'Note context' : 'Multiple notes'} will be included in the background
                  </p>
                )}
              </div>
            )}
            <div className="space-y-3">
              {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').map((m, idx) => (
                <React.Fragment key={idx}>
                  {/* For assistant messages, show activity timeline BEFORE the response */}
                  {m.role === 'assistant' && m.actions && m.actions.length > 0 && (
                    <ActivityTimeline
                      actions={m.actions}
                      isExpanded={expandedHistoryTimelines.has(idx)}
                      onToggle={() => {
                        setExpandedHistoryTimelines(prev => {
                          const next = new Set(prev)
                          if (next.has(idx)) {
                            next.delete(idx)
                          } else {
                            next.add(idx)
                          }
                          return next
                        })
                      }}
                      maxHeight="150px"
                    />
                  )}
                  <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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
                        <div className="prose prose-sm max-w-none" style={{ color: 'var(--color-text-primary)' }}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {m.content}
                          </ReactMarkdown>
                        </div>
                        {m.fileReferences && m.fileReferences.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-[var(--color-border)] flex flex-wrap gap-2">
                            {m.fileReferences.map((ref, refIdx) => (
                              <FileReference
                                key={`${ref.path}-${refIdx}`}
                                path={ref.path}
                                action={ref.action}
                                onClick={showFile}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </React.Fragment>
              ))}
              {/* Show current streaming turn if we have content */}
              {isStreaming && streamingMessage && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] px-3 py-2 rounded-lg text-sm bg-[var(--color-surface)] text-[var(--color-text-primary)] border border-[var(--color-border)]">
                    <div className="prose prose-sm max-w-none" style={{ color: 'var(--color-text-primary)' }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                        {streamingMessage}
                      </ReactMarkdown>
                    </div>
                    {streamingFileReferences && streamingFileReferences.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[var(--color-border)] flex flex-wrap gap-2">
                        {streamingFileReferences.map((ref, refIdx) => (
                          <FileReference
                            key={`streaming-${ref.path}-${refIdx}`}
                            path={ref.path}
                            action={ref.action}
                            onClick={showFile}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
              {/* Show activity timeline and loading animation when streaming or waiting */}
              {(isStreaming || loading) && (
                <div className="space-y-2">
                  <ActivityTimeline
                    actions={agentActions}
                    isExpanded={timelineExpanded}
                    onToggle={() => setTimelineExpanded(!timelineExpanded)}
                    maxHeight="200px"
                    cancelPhase={cancelPhase}
                    cancelMessage={cancelMessage}
                  />
                  <LoadingIndicator />
                </div>
              )}
              {error && (
                <div className="text-[var(--color-error)] text-sm">{error}</div>
              )}
            </div>
          </div>

          <div className="flex-shrink-0 p-4 border-t border-[var(--color-border)] bg-[var(--color-background)]">
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
                    disabled={cancelPhase !== 'idle' && cancelPhase !== 'failed'}
                    className={`flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md transition-colors text-sm font-medium ${
                      cancelPhase === 'force-killing'
                        ? 'bg-orange-600 text-white cursor-wait'
                        : cancelPhase === 'cancelling'
                        ? 'bg-yellow-600 text-white cursor-wait'
                        : cancelPhase === 'failed'
                        ? 'bg-red-800 text-white hover:bg-red-900'
                        : 'bg-red-600 text-white hover:bg-red-700'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    title={cancelMessage || "Stop agent operation"}
                  >
                    {cancelPhase === 'cancelling' && <Loader2 className="h-4 w-4 animate-spin" />}
                    {cancelPhase === 'force-killing' && <AlertTriangle className="h-4 w-4" />}
                    {(cancelPhase === 'idle' || cancelPhase === 'failed' || cancelPhase === 'cancelled') && <XCircle className="h-4 w-4" />}
                    {cancelPhase === 'idle' ? 'Stop Agent' : cancelMessage || 'Stop Agent'}
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
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-[var(--color-surface)] text-[var(--color-text-primary)] hover:bg-[var(--color-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium border border-[var(--color-border)]"
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
