import React from 'react'
import { FileText } from 'lucide-react'

interface FileReferenceProps {
  path: string
  action?: 'read' | 'modified' | 'mentioned' | 'created'
  onClick: (filePath: string) => void
  className?: string
}

const getActionColor = (action?: string) => {
  switch (action) {
    case 'modified': return 'var(--color-warning, #f59e0b)'
    case 'created': return 'var(--color-success, #10b981)'
    case 'read': return 'var(--color-info, #3b82f6)'
    case 'mentioned': return 'var(--color-text-secondary, #6b7280)'
    default: return 'var(--color-primary, #3b82f6)'
  }
}

const getActionLabel = (action?: string) => {
  switch (action) {
    case 'modified': return 'modified'
    case 'created': return 'created'
    case 'read': return 'read'
    case 'mentioned': return 'mentioned'
    default: return ''
  }
}

export default function FileReference({
  path,
  action,
  onClick,
  className = ''
}: FileReferenceProps) {
  const color = getActionColor(action)
  const label = getActionLabel(action)
  const fileName = path.split('/').pop() || path

  return (
    <button
      onClick={(e) => {
        e.preventDefault()
        onClick(path)
      }}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md
        transition-all duration-150 hover:shadow-sm
        border border-transparent ${className}`}
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        color: color,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--color-surface-hover, var(--color-surface))'
        e.currentTarget.style.borderColor = color
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--color-surface)'
        e.currentTarget.style.borderColor = 'var(--color-border)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
      title={`Click to open: ${path}`}
    >
      <FileText size={14} />
      <span className="text-sm font-medium">
        {fileName}
      </span>
      {label && (
        <span
          className="text-xs opacity-70"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          ({label})
        </span>
      )}
    </button>
  )
}
