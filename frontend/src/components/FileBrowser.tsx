import { useState, useEffect } from 'react'
import { FolderTree, Search, ChevronLeft, ChevronRight, Loader2, AlertCircle } from 'lucide-react'
import FileTree from './FileTree'
import FuzzySearch from './FuzzySearch'
import { getFileTree, FileTreeNode } from '../utils/fileOperations'

interface FileBrowserProps {
  isOpen: boolean
  onToggle: () => void
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
}

type BrowserMode = 'tree' | 'search'

export default function FileBrowser({ isOpen, onToggle, onFileSelect, selectedFile }: FileBrowserProps) {
  const [mode, setMode] = useState<BrowserMode>('tree')
  const [tree, setTree] = useState<FileTreeNode | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load file tree when sidebar opens or when switching to tree mode
  useEffect(() => {
    if (isOpen && mode === 'tree' && !tree) {
      loadFileTree()
    }
  }, [isOpen, mode, tree])

  const loadFileTree = async () => {
    setLoading(true)
    setError(null)

    try {
      const fileTree = await getFileTree()
      setTree(fileTree)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load file tree')
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
            bg-white dark:bg-gray-800
            border border-gray-300 dark:border-gray-600
            text-gray-700 dark:text-gray-300
            hover:bg-gray-50 dark:hover:bg-gray-700
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
    <div className="h-full w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
            Files
          </h2>
          <button
            onClick={onToggle}
            className="p-1.5 rounded-md text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="Close sidebar (Cmd/Ctrl+B)"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>

        {/* Mode toggle tabs */}
        <div className="flex border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => handleModeChange('tree')}
            className={`
              flex-1 flex items-center justify-center px-4 py-2.5 text-sm font-medium
              border-b-2 transition-colors duration-150
              ${mode === 'tree'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800'
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
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800'
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
            <div className="h-full flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
              <Loader2 className="h-8 w-8 animate-spin mb-3" />
              <p className="text-sm">Loading files...</p>
            </div>
          ) : error ? (
            <div className="h-full flex flex-col items-center justify-center text-red-600 dark:text-red-400 px-4">
              <AlertCircle className="h-8 w-8 mb-3" />
              <p className="text-sm text-center mb-4">{error}</p>
              <button
                onClick={loadFileTree}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : tree ? (
            <FileTree
              tree={tree}
              onFileSelect={onFileSelect}
              selectedFile={selectedFile}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 dark:text-gray-400 px-4">
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
      <div className="flex-shrink-0 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {mode === 'tree' ? (
            <>Press <kbd className="px-1.5 py-0.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs font-mono">Cmd/Ctrl+P</kbd> for quick search</>
          ) : (
            <>Use fuzzy matching to find files quickly</>
          )}
        </p>
      </div>
    </div>
  )
}
