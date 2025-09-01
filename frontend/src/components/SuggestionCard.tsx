import React from 'react'
import { 
  Clock, 
  FileCode, 
  Hash, 
  Sparkles,
  Calendar,
  FolderOpen
} from 'lucide-react'

interface SuggestionCardProps {
  suggestion: string
  category?: 'time' | 'file' | 'topic' | 'quick'
  onClick: (suggestion: string) => void
  className?: string
}

const getCategoryIcon = (category: string) => {
  switch (category) {
    case 'time': return Clock
    case 'file': return FileCode
    case 'topic': return Hash
    case 'quick': return Sparkles
    default: return Calendar
  }
}

const getCategoryColor = (category: string) => {
  switch (category) {
    case 'time': return 'blue'
    case 'file': return 'green'
    case 'topic': return 'purple'
    case 'quick': return 'orange'
    default: return 'gray'
  }
}

export default function SuggestionCard({ 
  suggestion, 
  category = 'quick', 
  onClick, 
  className = '' 
}: SuggestionCardProps) {
  const Icon = getCategoryIcon(category)
  const color = getCategoryColor(category)
  
  return (
    <button
      onClick={() => onClick(suggestion)}
      className={`group p-4 rounded-xl border-2 border-transparent hover:shadow-md transition-all duration-200 text-left w-full ${className}`}
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '2px solid var(--color-border)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = `var(--color-${color}, var(--color-primary))`
        e.currentTarget.style.backgroundColor = `var(--color-surface-hover, var(--color-surface))`
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--color-border)'
        e.currentTarget.style.backgroundColor = 'var(--color-surface)'
      }}
    >
      <div className="flex items-start space-x-3">
        <div 
          className="p-2 rounded-lg transition-colors"
          style={{
            backgroundColor: 'var(--color-background)',
            color: `var(--color-${color}, var(--color-text-secondary))`
          }}
        >
          <Icon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <p 
            className="text-sm font-medium leading-relaxed group-hover:text-opacity-80 transition-colors"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {suggestion}
          </p>
          <div 
            className="text-xs mt-1 capitalize"
            style={{ color: `var(--color-${color}, var(--color-text-secondary))` }}
          >
            {category} suggestion
          </div>
        </div>
        <div 
          className="opacity-0 group-hover:opacity-100 transition-opacity text-xs"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          →
        </div>
      </div>
    </button>
  )
}