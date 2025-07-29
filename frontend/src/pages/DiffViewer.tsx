import { useState, useEffect } from 'react'
import { GitBranch, Clock, FileText, Trash2, User, Hash, GitCommit as GitCommitIcon } from 'lucide-react'
import { GitCommit, GitWorkingChange, GitRepositoryStatus } from '../types'
import { apiFetch } from '../utils/api'
import ConfirmationDialog from '../components/ConfirmationDialog'

export default function DiffViewer() {
  const [commits, setCommits] = useState<GitCommit[]>([])
  const [workingChanges, setWorkingChanges] = useState<GitWorkingChange[]>([])
  const [selectedCommit, setSelectedCommit] = useState<GitCommit | null>(null)
  const [selectedWorkingChange, setSelectedWorkingChange] = useState<GitWorkingChange | null>(null)
  const [repoStatus, setRepoStatus] = useState<GitRepositoryStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showClearDialog, setShowClearDialog] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [activeTab, setActiveTab] = useState<'commits' | 'working'>('commits')

  useEffect(() => {
    fetchGitData()
  }, [])

  const fetchGitData = async () => {
    try {
      setError(null)
      
      // Fetch commits (using the existing /api/diffs endpoint which now returns git commits)
      const commitsResponse = await apiFetch('/api/diffs?limit=50')
      if (!commitsResponse.ok) {
        throw new Error(`Failed to fetch commits: ${commitsResponse.status}`)
      }
      const commitsData = await commitsResponse.json()
      
      // Fetch working changes
      const workingResponse = await apiFetch('/api/git/working-changes')
      const workingData = workingResponse.ok ? await workingResponse.json() : []
      
      // Fetch repository status
      const statusResponse = await apiFetch('/api/git/status') 
      const statusData = statusResponse.ok ? await statusResponse.json() : null
      
      setCommits(Array.isArray(commitsData) ? commitsData : [])
      setWorkingChanges(Array.isArray(workingData) ? workingData : [])
      setRepoStatus(statusData)
      
    } catch (error) {
      console.error('Error fetching git data:', error)
      setError(error instanceof Error ? error.message : 'Failed to load git data')
      setCommits([])
      setWorkingChanges([])
    } finally {
      setLoading(false)
    }
  }

  const handleCommitSelection = (commit: GitCommit) => {
    setSelectedCommit(commit)
    setSelectedWorkingChange(null)
  }

  const handleWorkingChangeSelection = (change: GitWorkingChange) => {
    setSelectedWorkingChange(change)
    setSelectedCommit(null)
  }

  const handleClearAllDiffs = async () => {
    try {
      setClearing(true)
      const response = await apiFetch('/api/diffs/clear', {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error(`Failed to clear diffs: ${response.status}`)
      }
      
      await fetchGitData()
      setSelectedCommit(null)
      setSelectedWorkingChange(null)
      setShowClearDialog(false)
      
    } catch (error) {
      console.error('Error clearing diffs:', error)
      setError(error instanceof Error ? error.message : 'Failed to clear diffs')
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
      case 'added': return 'text-green-600 bg-green-50'
      case 'modified': return 'text-blue-600 bg-blue-50'
      case 'deleted': return 'text-red-600 bg-red-50'
      case 'renamed': return 'text-purple-600 bg-purple-50'
      case 'untracked': return 'text-yellow-600 bg-yellow-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'staged': return 'text-green-600 bg-green-100'
      case 'unstaged': return 'text-orange-600 bg-orange-100'
      case 'untracked': return 'text-yellow-600 bg-yellow-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const renderSelectedContent = () => {
    if (selectedCommit) {
      return (
        <div>
          <div className="flex items-start space-x-4 mb-4 p-4 bg-gray-50 rounded-md">
            <GitCommitIcon className="h-5 w-5 text-gray-600 mt-1" />
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <code className="px-2 py-1 bg-gray-200 rounded text-sm font-mono">
                  {selectedCommit.shortHash}
                </code>
                <span className="text-sm text-gray-500">on {selectedCommit.branch}</span>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{selectedCommit.message}</h3>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <User className="h-3 w-3" />
                  <span>{selectedCommit.author}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(selectedCommit.timestamp).toLocaleString()}</span>
                </div>
                <span>{selectedCommit.filesChanged} file(s) changed</span>
              </div>
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900">Files Changed:</h4>
            {selectedCommit.changes.map((change, index) => (
              <div key={index} className="border border-gray-200 rounded-md">
                <div className="flex items-center justify-between p-3 bg-gray-50 border-b">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-gray-600" />
                    <span className="font-medium">{change.path}</span>
                    <span className={`px-2 py-1 rounded-full text-xs ${getChangeTypeColor(change.type)}`}>
                      {change.type}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    +{change.linesAdded} -{change.linesRemoved}
                  </div>
                </div>
                {change.diff && (
                  <pre className="text-xs bg-gray-900 text-gray-100 p-4 overflow-auto whitespace-pre-wrap max-h-96">
                    {change.diff}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )
    }

    if (selectedWorkingChange) {
      return (
        <div>
          <div className="flex items-start space-x-4 mb-4 p-4 bg-gray-50 rounded-md">
            <FileText className="h-5 w-5 text-gray-600 mt-1" />
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(selectedWorkingChange.status)}`}>
                  {selectedWorkingChange.status}
                </span>
                <span className={`px-2 py-1 rounded-full text-xs ${getChangeTypeColor(selectedWorkingChange.changeType)}`}>
                  {selectedWorkingChange.changeType}
                </span>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{selectedWorkingChange.filePath}</h3>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <GitBranch className="h-3 w-3" />
                  <span>{selectedWorkingChange.branch}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatTimeAgo(selectedWorkingChange.timestamp)}</span>
                </div>
              </div>
            </div>
          </div>
          
          {selectedWorkingChange.diff && (
            <div className="border border-gray-200 rounded-md">
              <div className="p-3 bg-gray-50 border-b">
                <h4 className="font-medium text-gray-900">Changes:</h4>
              </div>
              <pre className="text-xs bg-gray-900 text-gray-100 p-4 overflow-auto whitespace-pre-wrap max-h-96">
                {selectedWorkingChange.diff}
              </pre>
            </div>
          )}
        </div>
      )
    }

    return (
      <p className="text-gray-600 text-center py-8">
        Select a commit or working change to view details
      </p>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <GitBranch className="h-6 w-6 text-gray-600 mr-3" />
          <h1 className="text-2xl font-bold text-gray-900">Git History</h1>
        </div>
        
        {repoStatus && (
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <div className="flex items-center space-x-1">
              <GitBranch className="h-4 w-4" />
              <span>{repoStatus.branch}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Hash className="h-4 w-4" />
              <code className="text-xs">{(repoStatus.headCommit || 'unknown').substring(0, 8)}</code>
            </div>
            {repoStatus.isDirty && (
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs">
                {repoStatus.stagedFiles + repoStatus.unstagedFiles + repoStatus.untrackedFiles} pending
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Commits and Working Changes */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('commits')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'commits'
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Commits ({commits.length})
              </button>
              <button
                onClick={() => setActiveTab('working')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'working'
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Working Changes ({workingChanges.length})
              </button>
            </div>
            
            {(commits.length > 0 || workingChanges.length > 0) && (
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
          
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-600 mb-2">Error loading git data</p>
              <p className="text-sm text-gray-600 mb-4">{error}</p>
              <button
                onClick={fetchGitData}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {activeTab === 'commits' && commits.length > 0 && commits.map((commit) => (
                <div
                  key={commit.id}
                  onClick={() => handleCommitSelection(commit)}
                  className={`p-3 rounded-md cursor-pointer transition-colors ${
                    selectedCommit?.id === commit.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <code className="px-2 py-1 bg-gray-200 rounded text-xs font-mono">
                        {commit.shortHash}
                      </code>
                      <span className="text-sm text-gray-600">{commit.branch}</span>
                    </div>
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimeAgo(commit.timestamp)}
                    </div>
                  </div>
                  <p className="text-sm font-medium text-gray-900 mb-1">{commit.message}</p>
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <span>{commit.author}</span>
                    <span>{commit.filesChanged} file(s)</span>
                  </div>
                </div>
              ))}
              
              {activeTab === 'working' && workingChanges.length > 0 && workingChanges.map((change) => (
                <div
                  key={change.id}
                  onClick={() => handleWorkingChangeSelection(change)}
                  className={`p-3 rounded-md cursor-pointer transition-colors ${
                    selectedWorkingChange?.id === change.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(change.status)}`}>
                        {change.status}
                      </span>
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
                </div>
              ))}
              
              {activeTab === 'commits' && commits.length === 0 && (
                <p className="text-gray-600 text-center py-8">No commits found</p>
              )}
              
              {activeTab === 'working' && workingChanges.length === 0 && (
                <p className="text-gray-600 text-center py-8">No working changes</p>
              )}
            </div>
          )}
        </div>

        {/* Right Panel - Details */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            {selectedCommit ? 'Commit Details' : selectedWorkingChange ? 'Change Details' : 'Details'}
          </h3>
          {renderSelectedContent()}
        </div>
      </div>

      <ConfirmationDialog
        isOpen={showClearDialog}
        onClose={() => setShowClearDialog(false)}
        onConfirm={handleClearAllDiffs}
        title="Clear All Git History"
        message={`Are you sure you want to clear all ${commits.length} commit(s) and ${workingChanges.length} working change(s) from the database? This will not affect your actual git repository.`}
        confirmText="Clear All"
        cancelText="Cancel"
        danger={true}
        loading={clearing}
        extraWarning="This will only clear Obby's database records, not your git history."
      />
    </div>
  )
}