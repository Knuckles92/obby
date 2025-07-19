import { useState, useEffect } from 'react'
import { GitBranch, Clock, FileText } from 'lucide-react'
import { DiffEntry } from '../types'
import { apiFetch } from '../utils/api'

export default function DiffViewer() {
  const [diffs, setDiffs] = useState<DiffEntry[]>([])
  const [selectedDiff, setSelectedDiff] = useState<DiffEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDiffs()
  }, [])

  const fetchDiffs = async () => {
    try {
      setError(null)
      const response = await apiFetch('/api/diffs?limit=50')
      
      if (!response.ok) {
        throw new Error(`Failed to fetch diffs: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      
      if (Array.isArray(data)) {
        setDiffs(data)
      } else if (data.error) {
        throw new Error(data.error)
      } else {
        throw new Error('Invalid response format')
      }
    } catch (error) {
      console.error('Error fetching diffs:', error)
      setError(error instanceof Error ? error.message : 'Failed to load diffs')
      setDiffs([])
    } finally {
      setLoading(false)
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

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <GitBranch className="h-6 w-6 text-gray-600 mr-3" />
        <h1 className="text-2xl font-bold text-gray-900">Diff Viewer</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Diff List */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Changes</h3>
          
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-600 mb-2">Error loading diffs</p>
              <p className="text-sm text-gray-600 mb-4">{error}</p>
              <button
                onClick={fetchDiffs}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : diffs.length > 0 ? (
            <div className="space-y-2">
              {diffs.map((diff) => (
                <div
                  key={diff.id}
                  onClick={() => setSelectedDiff(diff)}
                  className={`p-3 rounded-md cursor-pointer transition-colors ${
                    selectedDiff?.id === diff.id ? 'bg-primary-50 border border-primary-200' : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-900">{diff.filePath}</p>
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimeAgo(diff.timestamp)}
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 line-clamp-1">{diff.content.substring(0, 100)}...</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600 text-center py-8">No diffs found</p>
          )}
        </div>

        {/* Diff Content */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Diff Content</h3>
          
          {selectedDiff ? (
            <div>
              <div className="flex items-center mb-4 p-3 bg-gray-50 rounded-md">
                <FileText className="h-4 w-4 text-gray-600 mr-2" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{selectedDiff.filePath}</p>
                  <p className="text-xs text-gray-600">{new Date(selectedDiff.timestamp).toLocaleString()}</p>
                </div>
              </div>
              
              <div className="space-y-2">
                {selectedDiff.size && selectedDiff.content.length < selectedDiff.size && (
                  <div className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-md">
                    Content truncated. Showing {selectedDiff.content.length} of {selectedDiff.size} characters.
                  </div>
                )}
                <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto whitespace-pre-wrap">
                  {selectedDiff.content}
                </pre>
              </div>
            </div>
          ) : (
            <p className="text-gray-600 text-center py-8">Select a diff to view details</p>
          )}
        </div>
      </div>
    </div>
  )
}