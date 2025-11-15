import { useState, useEffect, useRef } from 'react'
import { FolderTree, Search, ChevronLeft, ChevronRight, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import FileTree from './FileTree'
import FuzzySearch from './FuzzySearch'
import { getFileTree, FileTreeNode, refreshFileTree } from '../utils/fileOperations'
import { hasCachedFileTree, clearFileTreeCache } from '../utils/fileTreeCache'

interface FileBrowserProps {
  isOpen: boolean
  onToggle: () => void
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
  contextFiles?: string[]
  onContextToggle?: (filePath: string, isSelected: boolean) => void
}

type BrowserMode = 'tree' | 'search'

export default function FileBrowser({ isOpen, onToggle, onFileSelect, selectedFile, contextFiles = [], onContextToggle }: FileBrowserProps) {
  const [mode, setMode] = useState<BrowserMode>('tree')
  const [tree, setTree] = useState<FileTreeNode | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isFirstLoad, setIsFirstLoad] = useState(false)
  const sseRef = useRef<EventSource | null>(null)

  // Subscribe to SSE for cache invalidation
  useEffect(() => {
    // Connect to file updates SSE
    const sse = new EventSource('/api/files/updates/stream')

    sse.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data)

        // Handle file tree invalidation events
        if (data.type === 'file_tree_invalidated') {
          console.log('[File Browser] Cache invalidated by server, clearing client cache')
          clearFileTreeCache()

          // Reload tree if currently viewing it
          if (isOpen && mode === 'tree') {
            loadFileTree()
          }
        }
      } catch (err) {
        console.error('[File Browser] Error processing SSE event:', err)
      }
    })

    sse.addEventListener('error', (err) => {
      console.error('[File Browser] SSE connection error:', err)
      // Connection will auto-reconnect
    })

    sseRef.current = sse

    // Cleanup on unmount
    return () => {
      if (sseRef.current) {
        sseRef.current.close()
        sseRef.current = null
      }
    }
  }, [isOpen, mode])

  // Load file tree when sidebar opens or when switching to tree mode
  useEffect(() => {
    if (isOpen && mode === 'tree' && !tree) {
      loadFileTree()
    }
  }, [isOpen, mode, tree])

  const loadFileTree = async () => {
    setLoading(true)
    setError(null)

    // Check if this is the first time loading (no cache exists)
    const hasCache = hasCachedFileTree()
    setIsFirstLoad(!hasCache)

    try {
      const response = await getFileTree()
      setTree(response.tree)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load file tree')
    } finally {
      setLoading(false)
      setIsFirstLoad(false)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await refreshFileTree()
      setTree(response.tree)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh file tree')
    } finally {
      setLoading(false)
    }
  }

  // Refresh tree when mode changes back to tree
  const handleModeChange = (newMode: BrowserMode) => {
    setMode(newMode)
    if (newMode === 'tree' && tree) {
      // Optional: Refresh tree when switching back
      // loadFileTree()
    }
  }

  // Collapsed state - show toggle button only
  if (!isOpen) {
    return (
      <div className="h-full flex items-start">
        <button
          onClick={onToggle}
          className="
            mt-4 ml-2 p-2 rounded-md
            bg-[var(--color-background)]
            border border-[var(--color-border)]
            text-[var(--color-text-primary)]
            hover:bg-[var(--color-hover)]
            transition-colors duration-150
            shadow-sm
          "
          title="Open file browser (Cmd/Ctrl+B)"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    )
  }

  // Expanded state
  return (
    <div className="h-full w-full flex-shrink-0 border-r border-[var(--color-border)] bg-[var(--color-background)] flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between px-4 py-3">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] uppercase tracking-wide">
            Files
          </h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleRefresh}
              className="p-1.5 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-hover)] transition-colors"
              title="Refresh file tree"
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-hover)] transition-colors"
              title="Close sidebar (Cmd/Ctrl+B)"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Mode toggle tabs */}
        <div className="flex border-t border-[var(--color-border)]">
          <button
            onClick={() => handleModeChange('tree')}
            className={`
              flex-1 flex items-center justify-center px-4 py-2.5 text-sm font-medium
              border-b-2 transition-colors duration-150
              ${mode === 'tree'
                ? 'border-[var(--color-primary)] text-[var(--color-primary)] bg-[color-mix(in_srgb,var(--color-primary)_10%,transparent)]'
                : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-hover)]'
              }
            `}
          >
            <FolderTree className="h-4 w-4 mr-2" />
            Tree
          </button>
          <button
            onClick={() => handleModeChange('search')}
            className={`
              flex-1 flex items-center justify-center px-4 py-2.5 text-sm font-medium
              border-b-2 transition-colors duration-150
              ${mode === 'search'
                ? 'border-[var(--color-primary)] text-[var(--color-primary)] bg-[color-mix(in_srgb,var(--color-primary)_10%,transparent)]'
                : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-hover)]'
              }
            `}
          >
            <Search className="h-4 w-4 mr-2" />
            Search
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {mode === 'tree' ? (
          loading ? (
            <div className="h-full flex flex-col items-center justify-center text-[var(--color-text-secondary)] px-6">
              <Loader2 className="h-8 w-8 animate-spin mb-3" />
              {isFirstLoad ? (
                <div className="text-center space-y-2">
                  <p className="text-sm font-medium">Building file index...</p>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    This will be faster next time!
                  </p>
                </div>
              ) : (
                <p className="text-sm">Loading files...</p>
              )}
            </div>
          ) : error ? (
            <div className="h-full flex flex-col items-center justify-center text-[var(--color-error)] px-4">
              <AlertCircle className="h-8 w-8 mb-3" />
              <p className="text-sm text-center mb-4">{error}</p>
              <button
                onClick={loadFileTree}
                className="px-4 py-2 bg-[var(--color-primary)] text-[var(--color-text-inverse)] text-sm rounded-md hover:bg-[color-mix(in_srgb,var(--color-primary)_80%,black)]"
              >
                Retry
              </button>
            </div>
          ) : tree ? (
            <FileTree
              tree={tree}
              onFileSelect={onFileSelect}
              selectedFile={selectedFile}
              contextFiles={contextFiles}
              onContextToggle={onContextToggle}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-[var(--color-text-secondary)] px-4">
              <FolderTree className="h-12 w-12 mb-3 opacity-50" />
              <p className="text-sm text-center">No files found</p>
            </div>
          )
        ) : (
          <FuzzySearch
            onFileSelect={onFileSelect}
            autoFocus={true}
          />
        )}
      </div>

      {/* Footer with hint */}
      <div className="flex-shrink-0 px-4 py-2 border-t border-[var(--color-border)] bg-[var(--color-surface)]">
        <p className="text-xs text-[var(--color-text-secondary)]">
          {mode === 'tree' ? (
            <>Press <kbd className="px-1.5 py-0.5 bg-[var(--color-background)] border border-[var(--color-border)] rounded text-xs font-mono">Cmd/Ctrl+P</kbd> for quick search</>
          ) : (
            <>Use fuzzy matching to find files quickly</>
          )}
        </p>
      </div>
    </div>
  )
}
