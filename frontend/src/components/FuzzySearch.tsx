import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, FileText, Loader2, X } from 'lucide-react'
import { searchFiles, FileSearchResult, formatFileDate } from '../utils/fileOperations'
import { debounce } from '../utils/fuzzyMatch'

interface FuzzySearchProps {
  onFileSelect: (filePath: string) => void
  onClose?: () => void
  autoFocus?: boolean
}

export default function FuzzySearch({ onFileSelect, onClose, autoFocus = false }: FuzzySearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FileSearchResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  // Focus input on mount if autoFocus is true
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults([])
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const response = await searchFiles(searchQuery, 20)
        setResults(response.results)
        setSelectedIndex(0)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Search failed')
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300),
    []
  )

  // Handle query change
  useEffect(() => {
    if (query) {
      setLoading(true)
      debouncedSearch(query)
    } else {
      setResults([])
      setLoading(false)
    }
  }, [query, debouncedSearch])

  // Scroll selected item into view
  useEffect(() => {
    if (resultsRef.current && results.length > 0) {
      const selectedElement = resultsRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      }
    }
  }, [selectedIndex, results.length])

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (results.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, results.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (results[selectedIndex]) {
          handleSelect(results[selectedIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        if (onClose) {
          onClose()
        } else {
          setQuery('')
          setResults([])
        }
        break
    }
  }

  // Handle file selection
  const handleSelect = (result: FileSearchResult) => {
    onFileSelect(result.relativePath)
    setQuery('')
    setResults([])
  }

  // Highlight matched text
  const highlightMatch = (text: string, matchType: string) => {
    if (!query) return text

    const regex = new RegExp(`(${query.split('').join('.*')})`, 'gi')
    const parts = text.split(regex)

    return (
      <span>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <span key={i} className="bg-yellow-200 dark:bg-yellow-700">
              {part}
            </span>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </span>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search input */}
      <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {loading ? (
              <Loader2 className="h-5 w-5 text-gray-400 animate-spin" />
            ) : (
              <Search className="h-5 w-5 text-gray-400" />
            )}
          </div>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Fuzzy search files... (Cmd/Ctrl+P)"
            className="
              block w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600
              rounded-md leading-5 bg-white dark:bg-gray-800
              text-gray-900 dark:text-gray-100
              placeholder-gray-500 dark:placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              sm:text-sm
            "
          />
          {query && (
            <button
              onClick={() => {
                setQuery('')
                setResults([])
                inputRef.current?.focus()
              }}
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
            >
              <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
            </button>
          )}
        </div>

        {/* Keyboard hint */}
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">↑↓</span> navigate • <span className="font-medium">Enter</span> select • <span className="font-medium">Esc</span> close
        </div>
      </div>

      {/* Results */}
      <div ref={resultsRef} className="flex-1 overflow-auto">
        {error && (
          <div className="p-4 text-center text-red-600 dark:text-red-400">
            <p className="text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && query && results.length === 0 && (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <Search className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No files found for "{query}"</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {results.map((result, index) => (
              <div
                key={result.path}
                onClick={() => handleSelect(result)}
                onMouseEnter={() => setSelectedIndex(index)}
                className={`
                  px-4 py-3 cursor-pointer transition-colors duration-150
                  ${index === selectedIndex
                    ? 'bg-blue-50 dark:bg-blue-900/30 border-l-2 border-blue-600'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800 border-l-2 border-transparent'
                  }
                `}
              >
                <div className="flex items-start">
                  <FileText className={`
                    h-5 w-5 mr-3 flex-shrink-0 mt-0.5
                    ${index === selectedIndex
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-gray-400'
                    }
                  `} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {highlightMatch(result.name, result.matchType)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                      {result.relativePath}
                    </p>
                    <div className="flex items-center mt-1 text-xs text-gray-400 dark:text-gray-500 space-x-3">
                      <span>{formatFileDate(result.lastModified)}</span>
                      <span className="capitalize">{result.matchType} match</span>
                    </div>
                  </div>
                  {index === selectedIndex && (
                    <div className="ml-2 text-xs font-medium text-blue-600 dark:text-blue-400">
                      ↵
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading state for initial query */}
        {loading && !results.length && query && (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <Loader2 className="h-8 w-8 mx-auto mb-3 animate-spin" />
            <p className="text-sm">Searching...</p>
          </div>
        )}
      </div>

      {/* Results count */}
      {results.length > 0 && (
        <div className="flex-shrink-0 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {results.length} {results.length === 1 ? 'result' : 'results'} found
          </p>
        </div>
      )}
    </div>
  )
}
