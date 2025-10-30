import React, { useState, useEffect, useMemo } from 'react'
import { X, Search, Plus, Minus, FileText, RefreshCw } from 'lucide-react'
import { fuzzyMatch, fuzzyFilterPaths, getHighlightedSegments } from '../utils/fuzzyMatch'

interface ContextFile {
  path: string
  name: string
  type: 'file' | 'directory'
  size?: number
  lastModified?: number
  children?: ContextFile[]
}

interface ContextModalProps {
  isOpen: boolean
  onClose: () => void
  currentContextFiles: string[]
  onContextChange: (selectedFiles: string[]) => void
  watchedFiles: ContextFile[]
  currentViewedFile?: string
  modifiedFiles?: Set<string>
  filesMetadata?: Map<string, { lastModified: number, size: number }>
  onRefreshContext?: () => Promise<void>
  recentlyViewedFiles?: string[]
}

export function ContextModal({
  isOpen,
  onClose,
  currentContextFiles,
  onContextChange,
  watchedFiles,
  currentViewedFile,
  modifiedFiles = new Set(),
  filesMetadata = new Map(),
  onRefreshContext,
  recentlyViewedFiles = []
}: ContextModalProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set())
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    setSelectedFiles(currentContextFiles)
  }, [currentContextFiles])

  const flattenFiles = (files: ContextFile[]): ContextFile[] => {
    const result: ContextFile[] = []
    const traverse = (items: ContextFile[], prefix = '') => {
      for (const item of items) {
        if (item.type === 'file') {
          result.push(item)
        } else if (item.type === 'directory' && item.children) {
          traverse(item.children, prefix + item.name + '/')
        }
      }
    }
    traverse(files)
    return result
  }

  const allFiles = useMemo(() => flattenFiles(watchedFiles), [watchedFiles])

  const fileMap = useMemo(() => {
    const map = new Map<string, ContextFile>()
    for (const file of allFiles) {
      map.set(file.path, file)
    }
    return map
  }, [allFiles])

  const recentFileEntries = useMemo(() => {
    return recentlyViewedFiles
      .map((path) => {
        if (!path) return null
        const existing = fileMap.get(path)
        if (existing) return existing
        const name = path.split('/').pop() || path
        return { path, name, type: 'file' as const }
      })
      .filter((entry): entry is ContextFile => Boolean(entry && entry.path))
  }, [recentlyViewedFiles, fileMap])

  const filteredFiles = useMemo(() => {
    if (!searchQuery) return allFiles
    return fuzzyFilterPaths(allFiles.map(f => f.path), searchQuery)
      .map(result => allFiles.find(f => f.path === result.path))
      .filter(Boolean) as ContextFile[]
  }, [allFiles, searchQuery])

  const toggleFileSelection = (filePath: string) => {
    setSelectedFiles(prev => 
      prev.includes(filePath) 
        ? prev.filter(f => f !== filePath)
        : [...prev, filePath]
    )
  }

  const addFileToContext = (filePath: string) => {
    if (!filePath) return

    if (!currentContextFiles.includes(filePath)) {
      onContextChange([...currentContextFiles, filePath])
    }

    setSelectedFiles(prev =>
      prev.includes(filePath) ? prev : [...prev, filePath]
    )
  }

  const removeFileFromContext = (filePath: string) => {
    if (!filePath) return

    if (currentContextFiles.includes(filePath)) {
      onContextChange(currentContextFiles.filter(f => f !== filePath))
    }

    setSelectedFiles(prev => prev.filter(f => f !== filePath))
  }

  const addSelectedToContext = () => {
    const newContext = [...currentContextFiles]
    for (const file of selectedFiles) {
      if (!newContext.includes(file)) {
        newContext.push(file)
      }
    }
    onContextChange(newContext)
    onClose()
  }

  const removeSelectedFromContext = () => {
    const newContext = currentContextFiles.filter(f => !selectedFiles.includes(f))
    onContextChange(newContext)
    onClose()
  }

  const clearAllContext = () => {
    onContextChange([])
    setSelectedFiles([])
    onClose()
  }

  const handleRefreshContext = async () => {
    if (!onRefreshContext || isRefreshing) return

    setIsRefreshing(true)
    try {
      await onRefreshContext()
    } catch (error) {
      console.error('Failed to refresh context:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  const highlightMatch = (text: string) => {
    if (!searchQuery) return text
    const segments = getHighlightedSegments(text, searchQuery)
    return segments.map((segment, i) => 
      segment.isMatch ? (
        <span key={i} className="bg-yellow-200 text-yellow-900">{segment.text}</span>
      ) : (
        <span key={i}>{segment.text}</span>
      )
    )
  }

  const getFileIcon = (file: ContextFile) => {
    return <FileText className="w-4 h-4 text-gray-500" />
  }

  const formatTimeAgo = (timestamp: number) => {
    const now = Date.now()
    const diff = now - (timestamp * 1000) // Convert seconds to milliseconds
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return new Date(timestamp * 1000).toLocaleDateString()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Manage Context Files</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-6 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>

          {recentFileEntries.length > 0 && (
            <div className="mt-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700">Recently Viewed</h3>
                <span className="text-xs text-gray-500">{recentFileEntries.length} file{recentFileEntries.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="mt-2 space-y-2 max-h-40 overflow-y-auto pr-1">
                {recentFileEntries.map((file) => {
                  const isInContext = currentContextFiles.includes(file.path)
                  const isModified = modifiedFiles.has(file.path)

                  return (
                    <div
                      key={`recent-${file.path}`}
                      className={`flex items-center gap-2 p-2 rounded border transition-colors ${
                        isInContext ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
                      }`}
                    >
                      {getFileIcon(file)}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-800 truncate">{file.name}</div>
                        <div className="text-xs text-gray-500 truncate">{file.path}</div>
                      </div>
                      {isModified && (
                        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">Modified</span>
                      )}
                      <button
                        onClick={() => (isInContext ? removeFileFromContext(file.path) : addFileToContext(file.path))}
                        className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded ${
                          isInContext
                            ? 'text-red-600 bg-red-50 hover:bg-red-100'
                            : 'text-blue-600 bg-blue-50 hover:bg-blue-100'
                        }`}
                      >
                        {isInContext ? (
                          <>
                            <Minus className="w-3 h-3" />
                            Remove
                          </>
                        ) : (
                          <>
                            <Plus className="w-3 h-3" />
                            Add
                          </>
                        )}
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Current Context */}
        {currentContextFiles.length > 0 && (
          <div className="p-6 border-b bg-gray-50">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-sm text-gray-700">Current Context ({currentContextFiles.length} files)</h3>
              <div className="flex items-center gap-2">
                {onRefreshContext && (
                  <button
                    onClick={handleRefreshContext}
                    disabled={isRefreshing}
                    className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed"
                    title="Refresh file metadata"
                  >
                    <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                )}
                <button
                  onClick={clearAllContext}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  Clear All
                </button>
              </div>
            </div>
            <div className="space-y-2">
              {currentContextFiles.map((filePath, index) => {
                const isModified = modifiedFiles.has(filePath)
                const metadata = filesMetadata.get(filePath)

                return (
                  <div
                    key={filePath}
                    className={`flex items-center gap-2 p-2 rounded text-sm ${
                      isModified ? 'bg-amber-50 border border-amber-200' : 'bg-white border border-gray-200'
                    }`}
                  >
                    {index === 0 && currentViewedFile === filePath && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Primary</span>
                    )}
                    {isModified && (
                      <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">Modified</span>
                    )}
                    <FileText className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span className="text-gray-700 font-medium">{filePath.split('/').pop()}</span>
                      {metadata && (
                        <div className="text-xs text-gray-500">
                          Last updated: {formatTimeAgo(metadata.lastModified)}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* File List */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-2">
            {filteredFiles.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-8 border border-dashed border-gray-200 rounded-lg">
                No files match your search or watch filters.
              </div>
            ) : (
              filteredFiles.map((file) => {
                const isSelected = selectedFiles.includes(file.path)
                const isInContext = currentContextFiles.includes(file.path)
                const isPrimary = currentViewedFile === file.path

                return (
                  <div
                    key={file.path}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      isSelected ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50 border-gray-200'
                    } ${isInContext ? 'ring-2 ring-blue-500' : ''}`}
                    onClick={() => toggleFileSelection(file.path)}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleFileSelection(file.path)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    {getFileIcon(file)}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {highlightMatch(file.name)}
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {highlightMatch(file.path)}
                      </div>
                    </div>
                    {isPrimary && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Current</span>
                    )}
                    {isInContext && !isPrimary && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">In Context</span>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
          </div>
          <div className="flex gap-3">
            {selectedFiles.length > 0 && (
              <>
                <button
                  onClick={removeSelectedFromContext}
                  className="flex items-center gap-2 px-4 py-2 text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <Minus className="w-4 h-4" />
                  Remove Selected
                </button>
                <button
                  onClick={addSelectedToContext}
                  className="flex items-center gap-2 px-4 py-2 text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add Selected
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
