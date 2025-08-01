import { useState, useEffect } from 'react'
import { FileText, Clock, Hash, RefreshCw, Trash2, Archive, Copy } from 'lucide-react'
import { ContentDiff, FileChange, FileMonitoringStatus } from '../types'
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

  useEffect(() => {
    fetchFileData()
  }, [])

  const fetchFileData = async () => {
    try {
      setError(null)
      
      // Fetch recent diffs
      const diffsResponse = await apiFetch('/api/files/diffs?limit=50')
      if (!diffsResponse.ok) {
        throw new Error(`Failed to fetch diffs: ${diffsResponse.status}`)
      }
      const diffsData = await diffsResponse.json()
      
      // Fetch recent file changes
      const changesResponse = await apiFetch('/api/files/changes?limit=50')
      const changesData = changesResponse.ok ? await changesResponse.json() : []
      
      // Fetch file monitoring status
      const statusResponse = await apiFetch('/api/files/monitoring-status') 
      const statusData = statusResponse.ok ? await statusResponse.json() : null
      
      setDiffs(Array.isArray(diffsData) ? diffsData : [])
      setFileChanges(Array.isArray(changesData) ? changesData : [])
      setMonitoringStatus(statusData)
      
    } catch (error) {
      console.error('Error fetching file data:', error)
      setError(error instanceof Error ? error.message : 'Failed to load file data')
      setDiffs([])
      setFileChanges([])
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Archive className="h-6 w-6 text-gray-600 mr-3" />
          <h1 className="text-2xl font-bold text-gray-900">File History</h1>
        </div>
        
        {monitoringStatus && (
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <div className="flex items-center space-x-1">
              <FileText className="h-4 w-4" />
              <span>{monitoringStatus.tracked_files_count} files tracked</span>
            </div>
            <div className="flex items-center space-x-1">
              <Hash className="h-4 w-4" />
              <span>{monitoringStatus.system_type}</span>
            </div>
            {monitoringStatus.monitoring_active && (
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                Active
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Details */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            {selectedDiff ? 'Content Diff Details' : selectedChange ? 'File Change Details' : 'Details'}
          </h3>
          {renderSelectedContent()}
        </div>

        {/* Right Panel - Diffs and Changes */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('diffs')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'diffs'
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Content Diffs ({diffs.length})
              </button>
              <button
                onClick={() => setActiveTab('changes')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'changes'
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                File Changes ({fileChanges.length})
              </button>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={handleRefresh}
                className="flex items-center px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
                disabled={loading || refreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              
              {(diffs.length > 0 || fileChanges.length > 0) && (
                <button
                  onClick={() => setShowClearDialog(true)}
                  className="flex items-center px-3 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
                  disabled={loading || clearing}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear All
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
                onClick={fetchFileData}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
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
                  className={`p-3 rounded-md cursor-pointer transition-colors ${
                    selectedDiff?.id === diff.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
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
                  className={`p-3 rounded-md cursor-pointer transition-colors ${
                    selectedChange?.id === change.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
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