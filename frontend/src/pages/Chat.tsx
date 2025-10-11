import { useCallback, useEffect, useRef, useState } from 'react'
import { Send, MessageSquare, Settings, Wrench, Activity } from 'lucide-react'
import { apiRequest } from '../utils/api'

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
  const [availableTools, setAvailableTools] = useState<ToolInfo[]>([])
  const [showSettings, setShowSettings] = useState(false)
  const [progressMessage, setProgressMessage] = useState<string | null>(null)
  const [, setProgressType] = useState<string | null>(null)
  const [agentActions, setAgentActions] = useState<AgentAction[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

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
- When using tools, proceed without announcing your actions
- Synthesize results rather than listing raw data
- Focus on answering the user's question efficiently`
      }
    ])

    loadAvailableTools()

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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

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

    const next = [...messages, { role: 'user', content }]
    setMessages(next)
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
            messages: next,
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

      if (res.tools_used && Array.isArray(res.conversation) && res.conversation.length > 0) {
        setMessages(res.conversation)
      } else if (Array.isArray(res.conversation) && res.conversation.length > 0) {
        setMessages(res.conversation)
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      }
    } catch (e: any) {
      const errorMessage = e?.message || 'Chat failed'
      setError(errorMessage)
      recordAgentAction('error', 'Chat request failed', errorMessage, sessionId)
    } finally {
      setLoading(false)
      disconnectProgressSSE()
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold">Chat</h1>
          <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-xs font-medium">
            <Wrench className="h-3 w-3" />
            {provider === 'openai' ? 'OpenAI' : 'Claude'}
          </div>
          {enableFallback && (
            <div className="px-2 py-1 bg-gray-100 text-gray-600 rounded-md text-xs">
              Fallback: On
            </div>
          )}
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-2 rounded-md hover:bg-gray-100"
          title="Chat Settings"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
        <div className="flex-1 flex flex-col gap-4 min-h-0">
          {showSettings && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Chat Settings</h3>
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

          <div ref={scrollRef} className="flex-1 min-h-0 overflow-auto rounded-lg border border-gray-200 p-4 bg-white/70">
            {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').length === 0 && (
              <div className="text-gray-500 text-sm">Start a conversation by sending a message.</div>
            )}
            <div className="space-y-4">
              {messages.filter((m) => m.role !== 'system' && m.role !== 'tool').map((m, idx) => (
                <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] px-3 py-2 rounded-md text-sm whitespace-pre-wrap ${
                    m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
                  }`}>
                    {m.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="text-gray-500 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                    </div>
                    <span>Assistant is thinking…</span>
                  </div>
                </div>
              )}
              {error && (
                <div className="text-red-600 text-sm">{error}</div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Type your message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              Send
            </button>
          </div>
        </div>

        <div className="lg:w-80 w-full flex flex-col min-h-[200px]">
          <div className="flex-1 flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white/70">
            <div className="px-3 py-2 border-b border-gray-200 flex items-center justify-between bg-gray-50">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <Activity className="h-4 w-4 text-gray-500" />
                Agent Activity
              </div>
              {loading && (
                <div className="flex items-center gap-1 text-xs text-blue-600">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  Live
                </div>
              )}
            </div>
            {progressMessage && loading && (
              <div className="px-3 py-2 text-xs border-b border-blue-100 bg-blue-50 text-blue-700">
                {progressMessage}
              </div>
            )}
            <div className="flex-1 overflow-auto p-3 space-y-3 text-sm">
              {agentActions.length === 0 ? (
                <div className="text-xs text-gray-500">
                  Agent actions, tool calls, and progress updates will appear here while a chat request is running.
                </div>
              ) : (
                agentActions.map((action, index) => {
                  const previous = agentActions[index - 1]
                  const showSession = action.sessionId && action.sessionId !== previous?.sessionId
                  return (
                    <div key={action.id} className="space-y-1">
                      {showSession && (
                        <div className="text-[10px] uppercase tracking-wide text-gray-400">
                          Session {shortSessionLabel(action.sessionId)}
                        </div>
                      )}
                      <div className={`rounded-md border px-3 py-2 ${actionStyle(action.type)}`}>
                        <div className="flex items-center justify-between text-xs opacity-75">
                          <span>{formatTimestamp(action.timestamp)}</span>
                          <span className="capitalize">{actionTypeLabel(action.type)}</span>
                        </div>
                        <div className="mt-1 text-sm font-medium">{action.label}</div>
                        {action.detail && (
                          <pre className="mt-2 text-xs whitespace-pre-wrap break-words">
                            {action.detail}
                          </pre>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
