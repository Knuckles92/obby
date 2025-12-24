import { useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, FileText, Search, Terminal, Edit3, FolderOpen, FileOutput, Brain, AlertTriangle, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

type AgentActionType = 'progress' | 'tool_call' | 'tool_result' | 'warning' | 'error' | 'assistant_thinking'

interface AgentAction {
  id: string
  type: AgentActionType
  label: string
  detail?: string
  timestamp: string
  sessionId?: string
}

type CancelPhase = 'idle' | 'cancelling' | 'force-killing' | 'cancelled' | 'failed'

interface ActivityTimelineProps {
  actions: AgentAction[]
  isExpanded: boolean
  onToggle: () => void
  maxHeight?: string
  cancelPhase?: CancelPhase
  cancelMessage?: string
}

const formatTimestamp = (iso: string) => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const getToolIcon = (label: string) => {
  const labelLower = label.toLowerCase()
  if (labelLower.includes('read')) return <FileText className="h-3.5 w-3.5" />
  if (labelLower.includes('grep') || labelLower.includes('search')) return <Search className="h-3.5 w-3.5" />
  if (labelLower.includes('bash') || labelLower.includes('command')) return <Terminal className="h-3.5 w-3.5" />
  if (labelLower.includes('edit')) return <Edit3 className="h-3.5 w-3.5" />
  if (labelLower.includes('glob') || labelLower.includes('folder')) return <FolderOpen className="h-3.5 w-3.5" />
  if (labelLower.includes('write')) return <FileOutput className="h-3.5 w-3.5" />
  return null
}

const actionTypeLabel = (type: AgentActionType) => {
  switch (type) {
    case 'tool_call':
      return 'tool'
    case 'tool_result':
      return 'result'
    case 'assistant_thinking':
      return 'thinking'
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
      return 'border-[var(--color-info)] bg-[color-mix(in_srgb,var(--color-info)_15%,transparent)] text-[var(--color-info)]'
    case 'tool_result':
      return 'border-[var(--color-success)] bg-[color-mix(in_srgb,var(--color-success)_15%,transparent)] text-[var(--color-success)]'
    case 'assistant_thinking':
      return 'border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_15%,transparent)] text-[var(--color-accent)]'
    case 'error':
      return 'border-[var(--color-error)] bg-[color-mix(in_srgb,var(--color-error)_15%,transparent)] text-[var(--color-error)]'
    case 'warning':
      return 'border-[var(--color-warning)] bg-[color-mix(in_srgb,var(--color-warning)_15%,transparent)] text-[var(--color-warning)]'
    default:
      return 'border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)]'
  }
}

const actionIcon = (type: AgentActionType) => {
  switch (type) {
    case 'tool_call':
      return null // Will use tool-specific icon
    case 'tool_result':
      return <CheckCircle className="h-3.5 w-3.5" />
    case 'assistant_thinking':
      return <Brain className="h-3.5 w-3.5" />
    case 'error':
      return <AlertCircle className="h-3.5 w-3.5" />
    case 'warning':
      return <AlertTriangle className="h-3.5 w-3.5" />
    default:
      return null
  }
}

export default function ActivityTimeline({
  actions,
  isExpanded,
  onToggle,
  maxHeight = '200px',
  cancelPhase = 'idle',
  cancelMessage = ''
}: ActivityTimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [expandedActionId, setExpandedActionId] = useState<string | null>(null)

  // Auto-scroll to bottom when new actions arrive
  useEffect(() => {
    if (scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [actions, isExpanded])

  // Filter to show meaningful actions (skip generic progress messages)
  const meaningfulActions = actions.filter(
    (a) => a.type !== 'progress' || a.label.toLowerCase().includes('file') || a.label.toLowerCase().includes('tool')
  )

  const latestAction = meaningfulActions[meaningfulActions.length - 1]

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--color-hover)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="shimmer-loading rounded-full w-2 h-2" />
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">
            Activity
          </span>
          {!isExpanded && latestAction && (
            <span className="text-xs text-[var(--color-text-tertiary)] truncate max-w-[200px]">
              — {latestAction.label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {cancelPhase !== 'idle' && cancelPhase !== 'cancelled' && (
            <span className={`text-xs font-medium flex items-center gap-1 ${
              cancelPhase === 'force-killing' ? 'text-orange-500' : 'text-yellow-500'
            }`}>
              {cancelPhase === 'cancelling' && <Loader2 className="h-3 w-3 animate-spin" />}
              {cancelPhase === 'force-killing' && <AlertTriangle className="h-3 w-3" />}
              {cancelMessage}
            </span>
          )}
          <span className="text-xs text-[var(--color-text-tertiary)]">
            {meaningfulActions.length} actions
          </span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-[var(--color-text-tertiary)]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[var(--color-text-tertiary)]" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div
          ref={scrollRef}
          className="border-t border-[var(--color-border)] overflow-y-auto"
          style={{ maxHeight }}
        >
          {meaningfulActions.length === 0 ? (
            <div className="px-3 py-4 text-xs text-[var(--color-text-tertiary)] text-center">
              Waiting for agent activity...
            </div>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              {meaningfulActions.map((action) => (
                <div
                  key={action.id}
                  className="px-3 py-2 hover:bg-[var(--color-hover)] transition-colors cursor-pointer"
                  onClick={() => setExpandedActionId(expandedActionId === action.id ? null : action.id)}
                >
                  <div className="flex items-start gap-2">
                    {/* Timestamp */}
                    <span className="text-[10px] font-mono text-[var(--color-text-tertiary)] flex-shrink-0 pt-0.5">
                      {formatTimestamp(action.timestamp)}
                    </span>

                    {/* Type badge */}
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0 ${actionStyle(action.type)}`}
                    >
                      {actionTypeLabel(action.type)}
                    </span>

                    {/* Icon + Label */}
                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                      {action.type === 'tool_call' ? getToolIcon(action.label) : actionIcon(action.type)}
                      <span className="text-xs text-[var(--color-text-primary)] truncate">
                        {action.label}
                      </span>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {expandedActionId === action.id && action.detail && (
                    <div className="mt-2 ml-16 text-[11px] text-[var(--color-text-secondary)] bg-[var(--color-background)] rounded px-2 py-1.5 font-mono whitespace-pre-wrap break-all">
                      {action.detail}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
