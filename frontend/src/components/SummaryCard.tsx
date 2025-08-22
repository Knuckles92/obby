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
      className={`card cursor-pointer transition-all duration-200 hover:shadow-lg relative ${
        isSelected ? 'ring-2 ring-blue-500 border-blue-200' : ''
      } ${
        isItemSelected ? 'ring-2 ring-green-500 border-green-200 bg-green-50' : ''
      }`}
      style={{
        borderColor: isSelected ? 'var(--color-primary)' : isItemSelected ? 'var(--color-success)' : 'var(--color-border)',
        backgroundColor: isItemSelected ? 'var(--color-success-50, #f0fdf4)' : undefined,
        transform: 'translateY(0)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease'
      }}
      onClick={handleCardClick}
      onMouseEnter={(e) => {
        if (!isSelected) {
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.boxShadow = 'var(--shadow-lg)'
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = 'var(--shadow-md)'
        }
      }}
    >
      {/* Selection checkbox overlay */}
      {isSelectMode && (
        <div className="absolute top-2 left-2 z-10">
          <div 
            className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all duration-200 ${
              isItemSelected 
                ? 'bg-green-600 border-green-600 text-white' 
                : 'bg-white border-gray-300 hover:border-green-400'
            }`}
            style={{
              backgroundColor: isItemSelected ? 'var(--color-success)' : 'white',
              borderColor: isItemSelected ? 'var(--color-success)' : 'var(--color-border)',
              color: isItemSelected ? 'white' : 'transparent'
            }}
          >
            {isItemSelected && <Check className="h-4 w-4" />}
          </div>
        </div>
      )}

      {/* Header with title and delete button */}
      <div className={`flex items-start justify-between mb-3 ${isSelectMode ? 'pl-8' : ''}`}>
        <div className="flex-1 mr-2">
          <h3 
            className="font-medium text-gray-900 leading-tight"
            style={{ 
              fontSize: 'var(--font-size-base)',
              fontWeight: 'var(--font-weight-medium)',
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
            className="opacity-0 group-hover:opacity-100 sm:opacity-100 transition-opacity duration-200 p-2 hover:bg-red-100 rounded-md touch-manipulation flex items-center justify-center"
            style={{
              color: 'var(--color-error)',
              transition: 'opacity 0.2s ease, background-color 0.2s ease',
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
        className={`text-gray-600 text-sm mb-4 line-clamp-3 ${isSelectMode ? 'pl-8' : ''}`}
        style={{ 
          color: 'var(--color-text-secondary)',
          fontSize: 'var(--font-size-sm)',
          lineHeight: 'var(--line-height-relaxed)'
        }}
      >
        {summary.preview || 'No preview available'}
      </div>

      {/* Metadata row */}
      <div className={`flex items-center justify-between text-xs text-gray-500 mb-3 ${isSelectMode ? 'pl-8' : ''}`}>
        <div className="flex items-center space-x-4">
          <div className="flex items-center" title="Creation date">
            <Clock className="h-3 w-3 mr-1" />
            <span>{formatDate(summary.timestamp)}</span>
          </div>
          <div className="flex items-center" title="Word count">
            <FileText className="h-3 w-3 mr-1" />
            <span>{summary.word_count} words</span>
          </div>
        </div>
        <div 
          className="text-xs"
          style={{ color: 'var(--color-text-secondary)' }}
          title="File size"
        >
          {formatFileSize(summary.file_size)}
        </div>
      </div>

      {/* Click hint */}
      <div className="flex justify-center pt-2">
        <div 
          className="text-xs text-gray-400 flex items-center"
          style={{ 
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-xs)',
            opacity: 0.7
          }}
        >
          {isSelectMode ? (
            <>
              <Check className="h-3 w-3 mr-1" />
              Click to select
            </>
          ) : (
            <>
              <Eye className="h-3 w-3 mr-1" />
              Click to view
            </>
          )}
        </div>
      </div>
    </div>
  )
}