import { useState, useEffect, useRef } from 'react'
import { Search, X, Clock, FileText, ChevronUp, ChevronDown } from 'lucide-react'
import { SummaryNote } from '../types'

interface SearchResultsPopupProps {
  isOpen: boolean
  onClose: () => void
  searchTerm: string
  searchResults: SummaryNote[]
  loading: boolean
  onSelectResult: (filename: string) => void
}

export default function SearchResultsPopup({
  isOpen,
  onClose,
  searchTerm,
  searchResults,
  loading,
  onSelectResult
}: SearchResultsPopupProps) {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const overlayRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0)
  }, [searchResults])

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      } else if (event.key === 'ArrowDown') {
        event.preventDefault()
        setSelectedIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : prev
        )
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : prev)
      } else if (event.key === 'Enter' && searchResults.length > 0) {
        event.preventDefault()
        handleSelectResult(searchResults[selectedIndex].filename)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, searchResults, selectedIndex, onClose])

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return
    
    const selectedElement = listRef.current.children[selectedIndex] as HTMLElement
    if (selectedElement) {
      selectedElement.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      })
    }
  }, [selectedIndex])

  const handleSelectResult = (filename: string) => {
    onSelectResult(filename)
    onClose()
  }

  const handleBackdropClick = (event: React.MouseEvent) => {
    if (event.target === overlayRef.current) {
      onClose()
    }
  }

  const highlightSearchTerm = (text: string, searchTerm: string) => {
    if (!searchTerm.trim()) return text
    
    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    const parts = text.split(regex)
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark 
          key={index} 
          className="bg-yellow-200 text-yellow-900 px-1 rounded"
          style={{
            backgroundColor: 'var(--color-warning)25',
            color: 'var(--color-warning)',
            borderRadius: 'var(--border-radius-sm)'
          }}
        >
          {part}
        </mark>
      ) : (
        <span key={index}>{part}</span>
      )
    )
  }

  const formatTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return `${Math.floor(diffDays / 30)} months ago`
  }

  if (!isOpen) return null

  return (
    <div 
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.4)',
        backdropFilter: 'blur(8px)'
      }}
      onClick={handleBackdropClick}
    >
      <div 
        className="w-full max-w-2xl bg-white rounded-lg shadow-2xl max-h-[80vh] flex flex-col"
        style={{
          backgroundColor: 'var(--color-background)',
          borderRadius: 'var(--border-radius-lg)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '1px solid var(--color-border)'
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div 
          className="flex items-center justify-between p-6 border-b"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex items-center space-x-3">
            <div 
              className="p-2 rounded-md"
              style={{ backgroundColor: 'var(--color-primary)15' }}
            >
              <Search 
                className="h-5 w-5"
                style={{ color: 'var(--color-primary)' }}
              />
            </div>
            <div>
              <h2 
                className="text-lg font-semibold"
                style={{ 
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-lg)',
                  fontWeight: 'var(--font-weight-semibold)'
                }}
              >
                Search Results
              </h2>
              <p 
                className="text-sm"
                style={{ 
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)'
                }}
              >
                {loading ? 'Searching...' : `${searchResults.length} results for "${searchTerm}"`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md transition-colors hover:bg-gray-100"
            style={{
              borderRadius: 'var(--border-radius-md)',
              transition: 'background-color 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-hover)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            <X 
              className="h-5 w-5"
              style={{ color: 'var(--color-text-secondary)' }}
            />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <div 
                className="animate-spin rounded-full h-8 w-8 border-b-2"
                style={{ borderColor: 'var(--color-primary)' }}
              />
            </div>
          ) : searchResults.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 space-y-3">
              <FileText 
                className="h-12 w-12 text-gray-400"
                style={{ color: 'var(--color-text-secondary)50' }}
              />
              <p 
                className="text-gray-600"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                No summaries found for "{searchTerm}"
              </p>
            </div>
          ) : (
            <div 
              ref={listRef}
              className="overflow-y-auto max-h-[50vh] p-2"
            >
              {searchResults.map((summary, index) => (
                <div
                  key={summary.filename}
                  className={`p-4 rounded-md cursor-pointer transition-all duration-150 mb-2 ${
                    index === selectedIndex ? 'ring-2' : ''
                  }`}
                  style={{
                    backgroundColor: index === selectedIndex 
                      ? 'var(--color-primary)10' 
                      : 'var(--color-surface)',
                    borderRadius: 'var(--border-radius-md)',
                    border: index === selectedIndex 
                      ? `2px solid var(--color-primary)` 
                      : `1px solid var(--color-border)`,
                    transition: 'all 0.15s ease'
                  }}
                  onClick={() => handleSelectResult(summary.filename)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 
                        className="font-medium text-sm mb-1 truncate"
                        style={{
                          color: 'var(--color-text-primary)',
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 'var(--font-weight-medium)'
                        }}
                      >
                        {highlightSearchTerm(summary.title, searchTerm)}
                      </h3>
                      <p 
                        className="text-xs line-clamp-2 mb-2"
                        style={{
                          color: 'var(--color-text-secondary)',
                          fontSize: 'var(--font-size-xs)'
                        }}
                      >
                        {highlightSearchTerm(summary.preview, searchTerm)}
                      </p>
                      <div className="flex items-center space-x-3 text-xs">
                        <div 
                          className="flex items-center space-x-1"
                          style={{ color: 'var(--color-text-secondary)' }}
                        >
                          <Clock className="h-3 w-3" />
                          <span>{formatTimeAgo(summary.timestamp)}</span>
                        </div>
                        <div 
                          style={{ color: 'var(--color-text-secondary)' }}
                        >
                          {summary.word_count} words
                        </div>
                      </div>
                    </div>
                    {index === selectedIndex && (
                      <div 
                        className="ml-3 p-1 rounded"
                        style={{ backgroundColor: 'var(--color-primary)' }}
                      >
                        <ChevronDown 
                          className="h-3 w-3 text-white transform rotate-[-90deg]"
                          style={{ color: 'var(--color-text-inverse)' }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {searchResults.length > 0 && (
          <div 
            className="p-4 border-t"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <div className="flex items-center justify-between text-xs">
              <div 
                className="flex items-center space-x-4"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                <div className="flex items-center space-x-1">
                  <kbd 
                    className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs"
                    style={{
                      backgroundColor: 'var(--color-surface)',
                      borderColor: 'var(--color-border)',
                      borderRadius: 'var(--border-radius-sm)'
                    }}
                  >
                    <ChevronUp className="h-3 w-3 inline mr-1" />
                    <ChevronDown className="h-3 w-3 inline" />
                  </kbd>
                  <span>Navigate</span>
                </div>
                <div className="flex items-center space-x-1">
                  <kbd 
                    className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs"
                    style={{
                      backgroundColor: 'var(--color-surface)',
                      borderColor: 'var(--color-border)',
                      borderRadius: 'var(--border-radius-sm)'
                    }}
                  >
                    Enter
                  </kbd>
                  <span>Select</span>
                </div>
                <div className="flex items-center space-x-1">
                  <kbd 
                    className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs"
                    style={{
                      backgroundColor: 'var(--color-surface)',
                      borderColor: 'var(--color-border)',
                      borderRadius: 'var(--border-radius-sm)'
                    }}
                  >
                    Esc
                  </kbd>
                  <span>Close</span>
                </div>
              </div>
              <div 
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {selectedIndex + 1} of {searchResults.length}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}