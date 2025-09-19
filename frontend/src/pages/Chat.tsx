import { useEffect, useRef, useState } from 'react'
import { Send, MessageSquare, Settings, Wrench } from 'lucide-react'
import { apiRequest } from '../utils/api'

type Role = 'system' | 'user' | 'assistant' | 'tool'
interface ChatMessage { 
  role: Role; 
  content: string;
  tool_calls?: any[];
  tool_call_id?: string;
  name?: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [useTools, setUseTools] = useState(true)
  const [availableTools, setAvailableTools] = useState<string[]>([])
  const [showSettings, setShowSettings] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Ensure we have an initial system instruction only once
    setMessages([{ role: 'system', content: 'You are a helpful assistant with access to tools for searching notes and documentation.' }])
    
    // Load available tools
    loadAvailableTools()
  }, [])

  const loadAvailableTools = async () => {
    try {
      const toolsInfo = await apiRequest<{ tool_names: string[] }>('/api/chat/tools')
      setAvailableTools(toolsInfo.tool_names || [])
    } catch (e) {
      console.warn('Failed to load available tools:', e)
    }
  }

  useEffect(() => {
    // Auto-scroll to latest message
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || loading) return
    setError(null)

    const next = [...messages, { role: 'user', content }]
    setMessages(next)
    setInput('')
    setLoading(true)

    try {
      const res = await apiRequest<{ 
        reply: string; 
        tools_used?: boolean; 
        conversation?: ChatMessage[];
      }>(
        '/api/chat/complete',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: next, use_tools: useTools }),
        }
      )
      const reply = (res.reply || '').trim()
      
      if (res.tools_used && res.conversation) {
        // If tools were used, update with the full conversation
        setMessages(res.conversation)
      } else {
        // Standard response
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      }
    } catch (e: any) {
      setError(e?.message || 'Chat failed')
    } finally {
      setLoading(false)
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold">Chat</h1>
          {useTools && availableTools.length > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded-md text-xs">
              <Wrench className="h-3 w-3" />
              Tools Enabled
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

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold mb-3">Chat Settings</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={useTools}
                onChange={(e) => setUseTools(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Enable tool calling</span>
            </label>
            {availableTools.length > 0 && (
              <div className="text-sm text-gray-600">
                <div className="font-medium">Available Tools:</div>
                <ul className="mt-1 space-y-1">
                  {availableTools.map((tool) => (
                    <li key={tool} className="text-xs bg-gray-100 px-2 py-1 rounded">
                      {tool}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto rounded-lg border border-gray-200 p-4 bg-white/70">
        {messages.filter(m => m.role !== 'system').length === 0 && (
          <div className="text-gray-500 text-sm">Start a conversation by sending a message.</div>
        )}
        <div className="space-y-4">
          {messages.filter(m => m.role !== 'system').map((m, idx) => {
            if (m.role === 'tool') {
              // Tool response message
              return (
                <div key={idx} className="flex justify-center">
                  <div className="max-w-[90%] px-3 py-2 rounded-md text-xs bg-yellow-50 border border-yellow-200 text-yellow-800">
                    <div className="font-medium mb-1">🔧 Tool: {m.name}</div>
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  </div>
                </div>
              )
            }
            
            if (m.role === 'assistant' && m.tool_calls && m.tool_calls.length > 0) {
              // Assistant message with tool calls
              return (
                <div key={idx} className="flex justify-start">
                  <div className="max-w-[75%] space-y-2">
                    {m.content && (
                      <div className="px-3 py-2 rounded-md text-sm bg-gray-100 text-gray-900 whitespace-pre-wrap">
                        {m.content}
                      </div>
                    )}
                    {m.tool_calls.map((tc: any, tcIdx: number) => (
                      <div key={tcIdx} className="px-3 py-2 rounded-md text-xs bg-blue-50 border border-blue-200 text-blue-800">
                        <div className="font-medium mb-1">🛠️ Calling: {tc.function.name}</div>
                        <div className="text-xs text-blue-600">
                          {JSON.stringify(JSON.parse(tc.function.arguments), null, 2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            }
            
            // Regular user/assistant message
            return (
              <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[75%] px-3 py-2 rounded-md text-sm whitespace-pre-wrap ${
                  m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
                }`}>
                  {m.content}
                </div>
              </div>
            )
          })}
          {loading && (
            <div className="text-gray-500 text-sm">Thinking…</div>
          )}
          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
        </div>
      </div>

      {/* Input */}
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
  )
}

