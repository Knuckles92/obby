import { useState, useEffect } from 'react'
import { FileText, Clock, Hash, RefreshCw, Trash2, Archive, Copy } from 'lucide-react'
import { ContentDiff, FileChange, FileMonitoringStatus, PaginatedDiffsResponse, PaginatedChangesResponse, PaginationMetadata } from '../types'
import { apiFetch } from '../utils/api'
import ConfirmationDialog from '../components/ConfirmationDialog'

export default function DiffViewer() {
  const [diffs, setDiffs] = useState<ContentDiff[]>([])
  const [fileChanges, setFileChanges] = useState<FileChange[]>([])
  const [selectedDiff, setSelectedDiff] = useState<ContentDiff | null>(null)
  const [selectedChange, setSelectedChange] = useState<FileChange | null>(null)
  const [monitoringStatus, setMonitoringStatus] = useState<FileMonitoringStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showClearDialog, setShowClearDialog] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState<'diffs' | 'changes'>('diffs')
  const [copied, setCopied] = useState(false)

  // Pagination state
  const [diffsPagination, setDiffsPagination] = useState<PaginationMetadata | null>(null)
  const [changesPagination, setChangesPagination] = useState<PaginationMetadata | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    fetchFileData()
  }, [])

  const fetchFileData = async (reset: boolean = true) => {
    try {
      setError(null)
      
      // Reset pagination and data if this is a fresh fetch
      if (reset) {
        setDiffs([])
        setFileChanges([])
        setDiffsPagination(null)
        setChangesPagination(null)
      }
      
      // Fetch recent diffs
      const diffsResponse = await apiFetch('/api/files/diffs?limit=50')
      if (!diffsResponse.ok) {
        throw new Error(`Failed to fetch diffs: ${diffsResponse.status}`)
      }
      const diffsResponseData: PaginatedDiffsResponse = await diffsResponse.json()
      
      // Fetch recent file changes
      const changesResponse = await apiFetch('/api/files/changes?limit=50')
      if (!changesResponse.ok) {
        throw new Error(`Failed to fetch changes: ${changesResponse.status}`)
      }
      const changesResponseData: PaginatedChangesResponse = await changesResponse.json()
      
      // Fetch file monitoring status
      const statusResponse = await apiFetch('/api/files/monitoring-status') 
      const statusData = statusResponse.ok ? await statusResponse.json() : null
      
      setDiffs(diffsResponseData.diffs || [])
      setDiffsPagination(diffsResponseData.pagination)
      setFileChanges(changesResponseData.changes || [])
      setChangesPagination(changesResponseData.pagination)
      setMonitoringStatus(statusData)
      
    } catch (error) {
      console.error('Error fetching file data:', error)
      setError(error instanceof Error ? error.message : 'Failed to load file data')
      setDiffs([])
      setFileChanges([])
      setDiffsPagination(null)
      setChangesPagination(null)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await fetchFileData()
    } finally {
      setRefreshing(false)
    }
  }

  const loadMoreDiffs = async () => {
    if (!diffsPagination?.hasMore || loadingMore) return
    
    setLoadingMore(true)
    try {
      const offset = diffsPagination.offset + diffsPagination.limit
      const response = await apiFetch(`/api/files/diffs?limit=50&offset=${offset}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch more diffs: ${response.status}`)
      }
      
      const responseData: PaginatedDiffsResponse = await response.json()
      
      // Append new diffs to existing ones
      setDiffs(prevDiffs => [...prevDiffs, ...(responseData.diffs || [])])
      setDiffsPagination(responseData.pagination)
      
    } catch (error) {
      console.error('Error loading more diffs:', error)
      setError(error instanceof Error ? error.message : 'Failed to load more diffs')
    } finally {
      setLoadingMore(false)
    }
  }

  const loadMoreChanges = async () => {
    if (!changesPagination?.hasMore || loadingMore) return
    
    setLoadingMore(true)
    try {
      const offset = changesPagination.offset + changesPagination.limit
      const response = await apiFetch(`/api/files/changes?limit=50&offset=${offset}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch more changes: ${response.status}`)
      }
      
      const responseData: PaginatedChangesResponse = await response.json()
      
      // Append new changes to existing ones
      setFileChanges(prevChanges => [...prevChanges, ...(responseData.changes || [])])
      setChangesPagination(responseData.pagination)
      
    } catch (error) {
      console.error('Error loading more changes:', error)
      setError(error instanceof Error ? error.message : 'Failed to load more changes')
    } finally {
      setLoadingMore(false)
    }
  }

  const handleDiffSelection = (diff: ContentDiff) => {
    setSelectedDiff(diff)
    setSelectedChange(null)
  }

  const handleChangeSelection = (change: FileChange) => {
    setSelectedChange(change)
    setSelectedDiff(null)
  }

  const handleClearAllData = async () => {
    try {
      setClearing(true)
      // Note: This endpoint may need to be implemented
      const response = await apiFetch('/api/files/clear', {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error(`Failed to clear data: ${response.status}`)
      }
      
      await fetchFileData()
      setSelectedDiff(null)
      setSelectedChange(null)
      setShowClearDialog(false)
      
    } catch (error) {
      console.error('Error clearing data:', error)
      setError(error instanceof Error ? error.message : 'Failed to clear data')
    } finally {
      setClearing(false)
    }
  }

  const formatTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return `${Math.floor(diffMins / 1440)}d ago`
  }

  const getChangeTypeColor = (type: string) => {
    switch (type) {
      case 'created': return 'text-green-600 bg-green-50'
      case 'modified': return 'text-blue-600 bg-blue-50'
      case 'deleted': return 'text-red-600 bg-red-50'
      case 'moved': return 'text-purple-600 bg-purple-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const handleCopyDiff = async (diffContent: string) => {
    try {
      await navigator.clipboard.writeText(diffContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy diff content:', error)
    }
  }

  const renderSelectedContent = () => {
    if (selectedDiff) {
      return (
        <div>
          <div className="flex items-start space-x-4 mb-4 p-4 bg-gray-50 rounded-md">
            <FileText className="h-5 w-5 text-gray-600 mt-1" />
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <span className={`px-2 py-1 rounded-full text-xs ${getChangeTypeColor(selectedDiff.changeType)}`}>
                  {selectedDiff.changeType}
                </span>
                <code className="px-2 py-1 bg-gray-200 rounded text-sm font-mono">
                  {selectedDiff.id}
                </code>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{selectedDiff.filePath}</h3>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(selectedDiff.timestamp).toLocaleString()}</span>
                </div>
                <span>+{selectedDiff.linesAdded} -{selectedDiff.linesRemoved}</span>
              </div>
            </div>
          </div>
          
          {selectedDiff.diffContent && (
            <div className="border border-gray-200 rounded-md">
              <div className="p-3 bg-gray-50 border-b flex items-center justify-between">
                <h4 className="font-medium text-gray-900">Changes:</h4>
                <button
                  onClick={() => handleCopyDiff(selectedDiff.diffContent)}
                  className="flex items-center px-2 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                  title="Copy diff content"
                >
                  <Copy className="h-3 w-3 mr-1" />
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <pre className="text-xs bg-gray-900 text-gray-100 p-4 overflow-auto whitespace-pre-wrap max-h-96">
                {selectedDiff.diffContent}
              </pre>
            </div>
          )}
        </div>
      )
    }

    if (selectedChange) {
      return (
        <div>
          <div className="flex items-start space-x-4 mb-4 p-4 bg-gray-50 rounded-md">
            <FileText className="h-5 w-5 text-gray-600 mt-1" />
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <span className={`px-2 py-1 rounded-full text-xs ${getChangeTypeColor(selectedChange.changeType)}`}>
                  {selectedChange.changeType}
                </span>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{selectedChange.filePath}</h3>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatTimeAgo(selectedChange.timestamp)}</span>
                </div>
                {selectedChange.newContentHash && (
                  <div className="flex items-center space-x-1">
                    <Hash className="h-3 w-3" />
                    <code className="text-xs">{selectedChange.newContentHash.substring(0, 8)}</code>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className="p-4 bg-blue-50 rounded-md">
            <p className="text-sm text-blue-800">
              File change event recorded. Use the diff viewer above for detailed content comparison.
            </p>
          </div>
        </div>
      )
    }

    return (
      <p className="text-gray-600 text-center py-8">
        Select a diff or file change to view details
      </p>
    )
  }

  return (
    <div className="min-h-screen space-y-6">
      {/* Modern Header */}
      <div className="relative overflow-hidden rounded-2xl mb-2 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
      }}>
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

        <div className="relative z-10 flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                <Archive className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">File History</h1>
            </div>
            <p className="text-blue-100 text-lg">Browse recent diffs and file change events</p>
          </div>

          {monitoringStatus && (
            <div className={`flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border transition-all duration-300 ${
              monitoringStatus.monitoring_active
                ? 'bg-green-500/20 border-green-400/30 text-green-100'
                : 'bg-red-500/20 border-red-400/30 text-red-100'
            }`}>
              <div className={`w-2 h-2 rounded-full animate-pulse ${
                monitoringStatus.monitoring_active ? 'bg-green-400' : 'bg-red-400'
              }`}></div>
              <span className="text-sm font-medium">
                {monitoringStatus.monitoring_active ? 'Monitoring Active' : 'Monitoring Inactive'}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Panel - Details */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-lg font-medium mb-4" style={{ color: 'var(--color-text-primary)' }}>
            {selectedDiff ? 'Content Diff Details' : selectedChange ? 'File Change Details' : 'Details'}
          </h3>
          {renderSelectedContent()}
        </div>

        {/* Right Panel - Diffs and Changes */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('diffs')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'diffs'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Content Diffs ({diffsPagination?.total ?? diffs.length})
              </button>
              <button
                onClick={() => setActiveTab('changes')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'changes'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                File Changes ({changesPagination?.total ?? fileChanges.length})
              </button>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={handleRefresh}
                className="relative overflow-hidden px-3 py-2 text-sm font-semibold rounded-xl transition-all duration-300 text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100"
                disabled={loading || refreshing}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                <div className="relative flex items-center">
                  <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                  Refresh
                </div>
              </button>
              
              {(diffs.length > 0 || fileChanges.length > 0) && (
                <button
                  onClick={() => setShowClearDialog(true)}
                  className="relative overflow-hidden px-3 py-2 text-sm font-semibold rounded-xl transition-all duration-300 text-red-700 bg-red-50 border border-red-200 hover:bg-red-100"
                  disabled={loading || clearing}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                  <div className="relative flex items-center">
                    <Trash2 className="h-4 w-4 mr-2" />
                    Clear All
                  </div>
                </button>
              )}
            </div>
          </div>
          
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-600 mb-2">Error loading file data</p>
              <p className="text-sm text-gray-600 mb-4">{error}</p>
              <button
                onClick={() => fetchFileData()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {activeTab === 'diffs' && diffs.length > 0 && diffs.map((diff) => (
                <div
                  key={diff.id}
                  onClick={() => handleDiffSelection(diff)}
                  className={`group/item relative overflow-hidden p-3 rounded-md cursor-pointer transition-colors border ${
                    selectedDiff?.id === diff.id
                      ? 'bg-blue-50 border-blue-200'
                      : 'bg-gray-50 hover:bg-gray-100 border-gray-200'
                  }`}
                >
                  <div className="absolute inset-0 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" style={{
                    background: 'linear-gradient(90deg, transparent, var(--color-surface), transparent)'
                  }}></div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs ${getChangeTypeColor(diff.changeType)}`}>
                        {diff.changeType}
                      </span>
                      <code className="px-2 py-1 bg-gray-200 rounded text-xs font-mono">
                        {diff.id}
                      </code>
                    </div>
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimeAgo(diff.timestamp)}
                    </div>
                  </div>
                  <p className="text-sm font-medium text-gray-900 mb-1">{diff.filePath}</p>
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <span>+{diff.linesAdded} -{diff.linesRemoved}</span>
                    <span>{diff.changeType}</span>
                  </div>
                </div>
              ))}
              
              {activeTab === 'changes' && fileChanges.length > 0 && fileChanges.map((change) => (
                <div
                  key={change.id}
                  onClick={() => handleChangeSelection(change)}
                  className={`group/item relative overflow-hidden p-3 rounded-md cursor-pointer transition-colors border ${
                    selectedChange?.id === change.id
                      ? 'bg-blue-50 border-blue-200'
                      : 'bg-gray-50 hover:bg-gray-100 border-gray-200'
                  }`}
                >
                  <div className="absolute inset-0 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" style={{
                    background: 'linear-gradient(90deg, transparent, var(--color-surface), transparent)'
                  }}></div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs ${getChangeTypeColor(change.changeType)}`}>
                        {change.changeType}
                      </span>
                    </div>
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimeAgo(change.timestamp)}
                    </div>
                  </div>
                  <p className="text-sm font-medium text-gray-900">{change.filePath}</p>
                  {change.newContentHash && (
                    <p className="text-xs text-gray-500 font-mono mt-1">
                      {change.newContentHash.substring(0, 16)}...
                    </p>
                  )}
                </div>
              ))}
              
              {activeTab === 'diffs' && diffs.length === 0 && (
                <p className="text-gray-600 text-center py-8">No content diffs found</p>
              )}
              
              {activeTab === 'changes' && fileChanges.length === 0 && (
                <p className="text-gray-600 text-center py-8">No file changes found</p>
              )}

              {/* Load More Buttons */}
              {activeTab === 'diffs' && diffsPagination?.hasMore && (
                <div className="text-center py-4">
                  <button
                    onClick={loadMoreDiffs}
                    disabled={loadingMore}
                    className="flex items-center justify-center mx-auto px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loadingMore ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Loading more...
                      </>
                    ) : (
                      `Load More (${diffsPagination.total - diffs.length} remaining)`
                    )}
                  </button>
                </div>
              )}

              {activeTab === 'changes' && changesPagination?.hasMore && (
                <div className="text-center py-4">
                  <button
                    onClick={loadMoreChanges}
                    disabled={loadingMore}
                    className="flex items-center justify-center mx-auto px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loadingMore ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Loading more...
                      </>
                    ) : (
                      `Load More (${changesPagination.total - fileChanges.length} remaining)`
                    )}
                  </button>
                </div>
              )}

              {/* Pagination Info */}
              {activeTab === 'diffs' && diffsPagination && diffs.length > 0 && (
                <div className="text-center py-2 border-t border-gray-200 text-xs text-gray-500">
                  Showing {diffs.length} of {diffsPagination.total} content diffs
                </div>
              )}

              {activeTab === 'changes' && changesPagination && fileChanges.length > 0 && (
                <div className="text-center py-2 border-t border-gray-200 text-xs text-gray-500">
                  Showing {fileChanges.length} of {changesPagination.total} file changes
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <ConfirmationDialog
        isOpen={showClearDialog}
        onClose={() => setShowClearDialog(false)}
        onConfirm={handleClearAllData}
        title="Clear All File History"
        message={`Are you sure you want to clear all ${diffs.length} diff(s) and ${fileChanges.length} file change(s) from the database? This will not affect your actual files.`}
        confirmText="Clear All"
        cancelText="Cancel"
        danger={true}
        loading={clearing}
        extraWarning="This will only clear Obby's database records, not your actual files."
      />
    </div>
  )
}