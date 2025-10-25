import React from 'react'
import { 
  FileText, 
  CheckSquare, 
  List, 
  BarChart3,
  Check
} from 'lucide-react'

interface OutputFormat {
  id: string
  name: string
  description: string
  icon: React.ComponentType<{ size?: number, className?: string }>
  preview: string
  color: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'
}

interface OutputStylePickerProps {
  value: string
  onChange: (format: string) => void
  className?: string
  compact?: boolean
}

const OUTPUT_FORMATS: OutputFormat[] = [
  {
    id: 'summary',
    name: 'Summary',
    description: 'Comprehensive overview with insights and analysis',
    icon: FileText,
    preview: '• Executive Summary\n• Key Highlights\n• File Activity\n• Next Steps',
    color: 'info'
  },
  {
    id: 'actionItems',
    name: 'Action Items',
    description: 'Focused on next steps and actionable tasks',
    icon: CheckSquare,
    preview: '• Immediate Actions\n• Code Quality Tasks\n• Future Enhancements\n• Technical Debt',
    color: 'success'
  },
  {
    id: 'bulletPoints',
    name: 'Bullet Points',
    description: 'Concise bullet-point overview of changes',
    icon: List,
    preview: '• What Was Accomplished\n• Files Modified\n• Key Changes\n• Quick Stats',
    color: 'primary'
  },
  {
    id: 'technicalDetails',
    name: 'Technical Details',
    description: 'In-depth technical analysis with metrics',
    icon: BarChart3,
    preview: '• Technical Overview\n• Performance Impact\n• Code Patterns\n• Recommendations',
    color: 'warning'
  }
]

export default function OutputStylePicker({ value, onChange, className = '', compact = false }: OutputStylePickerProps) {
  if (compact) {
    return (
      <div className={`space-y-2 ${className}`}>
        <label
          className="block text-sm font-medium"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Output Style
        </label>
        <div className="grid grid-cols-2 gap-2">
          {OUTPUT_FORMATS.map((format) => {
            const Icon = format.icon
            const isSelected = value === format.id
            return (
              <button
                key={format.id}
                onClick={() => onChange(format.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-all ${isSelected ? 'font-semibold' : ''}`}
                style={{
                  backgroundColor: 'var(--color-surface)',
                  borderColor: isSelected ? `var(--color-${format.color}, var(--color-primary))` : 'var(--color-border)',
                  color: isSelected ? `var(--color-${format.color}, var(--color-primary))` : 'var(--color-text-secondary)'
                }}
              >
                <span
                  className="inline-flex items-center justify-center w-6 h-6 rounded"
                  style={{
                    backgroundColor: isSelected ? `var(--color-${format.color}, var(--color-primary))` : 'var(--color-background)',
                    color: isSelected ? 'var(--color-text-inverse)' : `var(--color-${format.color}, var(--color-text-secondary))`
                  }}
                >
                  <Icon size={14} />
                </span>
                <span>{format.name}</span>
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <label 
        className="block text-sm font-medium mb-3"
        style={{ color: 'var(--color-text-primary)' }}
      >
        Output Style
        <p className="text-sm font-normal mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Choose how you want the results formatted
        </p>
      </label>
      
      <div className="grid grid-cols-1 gap-3">
        {OUTPUT_FORMATS.map((format) => {
          const Icon = format.icon
          const isSelected = value === format.id
          
          return (
            <button
              key={format.id}
              onClick={() => onChange(format.id)}
              className={`relative p-4 rounded-xl border-2 text-left transition-all duration-200 hover:shadow-md group ${
                isSelected ? 'shadow-lg' : 'hover:border-opacity-50'
              }`}
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: isSelected 
                  ? `var(--color-${format.color}, var(--color-primary))` 
                  : 'var(--color-border)',
                transform: isSelected ? 'scale(1.02)' : 'scale(1)',
              }}
            >
              {isSelected && (
                <div 
                  className="absolute top-3 right-3 w-6 h-6 rounded-full flex items-center justify-center"
                  style={{ 
                    backgroundColor: `var(--color-${format.color}, var(--color-primary))`,
                    color: 'var(--color-text-inverse)'
                  }}
                >
                  <Check size={14} />
                </div>
              )}
              <div className="flex items-start space-x-3 mb-3">
                <div 
                  className="p-2 rounded-lg"
                  style={{
                    backgroundColor: isSelected 
                      ? `var(--color-${format.color}, var(--color-primary))` 
                      : 'var(--color-background)',
                    color: isSelected 
                      ? 'var(--color-text-inverse)' 
                      : `var(--color-${format.color}, var(--color-text-secondary))`
                  }}
                >
                  <Icon size={20} />
                </div>
                <div className="flex-1">
                  <h3 
                    className="font-semibold text-sm"
                    style={{ 
                      color: isSelected 
                        ? `var(--color-${format.color}, var(--color-primary))` 
                        : 'var(--color-text-primary)'
                    }}
                  >
                    {format.name}
                  </h3>
                  <p 
                    className="text-xs mt-1 leading-relaxed"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {format.description}
                  </p>
                </div>
              </div>
              <div 
                className="text-xs font-mono p-3 rounded-lg border"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text-secondary)'
                }}
              >
                {format.preview.split('\n').map((line, index) => (
                  <div key={index} className="py-0.5">
                    {line}
                  </div>
                ))}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
