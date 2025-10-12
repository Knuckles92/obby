import { FileText, Clock, Trash2, Eye, Check } from 'lucide-react'
import { SummaryNote } from '../types'

interface SummaryCardProps {
  summary: SummaryNote
  onView: (filename: string) => void
  onDelete: (filename: string) => void
  isSelected?: boolean
  isSelectMode?: boolean
  isItemSelected?: boolean
  onSelect?: (filename: string) => void
}

export default function SummaryCard({ 
  summary, 
  onView, 
  onDelete, 
  isSelected = false, 
  isSelectMode = false, 
  isItemSelected = false, 
  onSelect 
}: SummaryCardProps) {
  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const truncateTitle = (title: string, maxLength: number = 50) => {
    if (title.length <= maxLength) return title
    return title.substring(0, maxLength) + '...'
  }

  const handleCardClick = () => {
    if (isSelectMode && onSelect) {
      onSelect(summary.filename)
    } else {
      onView(summary.filename)
    }
  }

  return (
    <div 
      className={`group/card relative overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-2xl rounded-2xl border-2 ${
        isSelected ? 'shadow-2xl scale-105' : 'shadow-lg'
      } ${
        isItemSelected ? 'shadow-2xl' : ''
      }`}
      style={{
        background: isItemSelected 
          ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)' 
          : 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: isSelected 
          ? 'var(--color-primary)' 
          : isItemSelected 
            ? '#4ade80' 
            : 'var(--color-border)',
        transform: 'translateY(0)',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
      onClick={handleCardClick}
      onMouseEnter={(e) => {
        if (!isSelected) {
          e.currentTarget.style.transform = 'translateY(-4px)'
          e.currentTarget.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
        }
      }}
    >
      {/* Hover gradient overlay */}
      <div className="absolute inset-0 opacity-0 group-hover/card:opacity-100 transition-opacity duration-300 pointer-events-none" style={{
        background: 'radial-gradient(circle at top right, var(--color-primary)08, transparent)'
      }}></div>
      
      <div className="relative p-6">
        {/* Selection checkbox overlay */}
        {isSelectMode && (
          <div className="absolute top-4 left-4 z-10">
            <div 
              className={`w-7 h-7 rounded-xl border-2 flex items-center justify-center transition-all duration-300 shadow-md ${
                isItemSelected 
                  ? 'bg-green-600 border-green-600 text-white scale-110' 
                  : 'bg-white/90 border-gray-300 hover:border-green-400 hover:scale-110'
              }`}
              style={{
                backgroundColor: isItemSelected ? '#16a34a' : 'rgba(255, 255, 255, 0.9)',
                borderColor: isItemSelected ? '#16a34a' : 'var(--color-border)',
                color: isItemSelected ? 'white' : 'transparent'
              }}
            >
              {isItemSelected && <Check className="h-4 w-4" />}
            </div>
          </div>
        )}

        {/* Header with title and delete button */}
        <div className={`flex items-start justify-between mb-4 ${isSelectMode ? 'pl-10' : ''}`}>
          <div className="flex-1 mr-2">
            <h3 
              className="font-bold text-gray-900 leading-tight text-lg"
              style={{ 
                color: 'var(--color-text-primary)'
              }}
              title={summary.title}
            >
              {truncateTitle(summary.title)}
            </h3>
          </div>
          {!isSelectMode && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(summary.filename)
              }}
              className="opacity-0 group-hover/card:opacity-100 sm:opacity-100 transition-all duration-300 p-2.5 hover:bg-red-50 rounded-xl touch-manipulation flex items-center justify-center border-2 border-transparent hover:border-red-200 hover:scale-110"
              style={{
                color: 'var(--color-error)',
                minWidth: '44px',
                minHeight: '44px'
              }}
              title="Delete summary"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Preview content */}
        <div 
          className={`text-gray-600 text-sm mb-4 line-clamp-3 leading-relaxed ${isSelectMode ? 'pl-10' : ''}`}
          style={{ 
            color: 'var(--color-text-secondary)'
          }}
        >
          {summary.preview || 'No preview available'}
        </div>

        {/* Metadata row with modern badges */}
        <div className={`flex flex-wrap items-center gap-2 mb-4 ${isSelectMode ? 'pl-10' : ''}`}>
          <div className="flex items-center px-3 py-1.5 rounded-lg shadow-sm" style={{
            backgroundColor: 'var(--color-info)',
            color: 'var(--color-text-inverse)'
          }} title="Creation date">
            <Clock className="h-3.5 w-3.5 mr-1.5" />
            <span className="text-xs font-semibold">{formatDate(summary.timestamp)}</span>
          </div>
          <div className="flex items-center px-3 py-1.5 rounded-lg shadow-sm" style={{
            backgroundColor: 'var(--color-success)',
            color: 'var(--color-text-inverse)'
          }} title="Word count">
            <FileText className="h-3.5 w-3.5 mr-1.5" />
            <span className="text-xs font-semibold">{summary.word_count} words</span>
          </div>
          <div 
            className="flex items-center px-3 py-1.5 rounded-lg shadow-sm text-xs font-semibold"
            style={{ 
              backgroundColor: 'var(--color-warning)',
              color: 'var(--color-text-inverse)'
            }}
            title="File size"
          >
            {formatFileSize(summary.file_size)}
          </div>
        </div>

        {/* Click hint with modern styling */}
        <div className="flex justify-center pt-3 border-t" style={{
          borderColor: 'var(--color-divider)'
        }}>
          <div 
            className="text-xs flex items-center px-3 py-1.5 rounded-lg transition-all duration-300 group-hover/card:scale-105"
            style={{ 
              color: 'var(--color-text-secondary)',
              backgroundColor: 'var(--color-surface)',
              fontWeight: '600'
            }}
          >
            {isSelectMode ? (
              <>
                <Check className="h-3.5 w-3.5 mr-1.5" />
                Click to {isItemSelected ? 'deselect' : 'select'}
              </>
            ) : (
              <>
                <Eye className="h-3.5 w-3.5 mr-1.5" />
                Click to view full summary
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}