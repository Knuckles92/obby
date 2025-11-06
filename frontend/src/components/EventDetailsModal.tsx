import { useState, useEffect } from 'react'
import { X, File, Clock, HardDrive, ExternalLink, Copy, CheckCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../utils/api'
import { FileEvent, ContentDiff } from '../types'

interface EventDetailsResponse {
  event: FileEvent;
  diff: ContentDiff | null;
}

interface EventDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  eventId: string;
  sourceType?: 'event' | 'diff';  // Determines which endpoint to use
}

export default function EventDetailsModal({ isOpen, onClose, eventId, sourceType = 'event' }: EventDetailsModalProps) {
  const [data, setData] = useState<EventDetailsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (isOpen && eventId) {
      fetchEventDetails()
    }
  }, [isOpen, eventId, sourceType])

  const fetchEventDetails = async () => {
    try {
      setLoading(true)
      setError(null)
      // Choose endpoint based on source type
      const endpoint = sourceType === 'diff'
        ? `/api/files/diffs/${eventId}/details`
        : `/api/files/events/${eventId}/details`

      const response = await apiFetch(endpoint)

      if (!response.ok) {
        throw new Error('Failed to fetch event details')
      }

      const eventData = await response.json()
      setData(eventData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load event details')
    } finally {
      setLoading(false)
    }
  }

  const formatFileSize = (bytes: number | undefined) => {
    if (!bytes || bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getRelativeTime = (timestamp: string) => {
    const now = new Date()
    const eventTime = new Date(timestamp)
    const diffMs = now.getTime() - eventTime.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`

    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`

    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'created': return 'bg-green-100 text-green-800 border-green-200'
      case 'modified': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'deleted': return 'bg-red-100 text-red-800 border-red-200'
      case 'moved': return 'bg-purple-100 text-purple-800 border-purple-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getEventTypeIcon = (type: string) => {
    const className = "h-6 w-6"
    switch (type) {
      case 'created': return <File className={className} />
      case 'modified': return <File className={className} />
      case 'deleted': return <X className={className} />
      case 'moved': return <File className={className} />
      default: return <File className={className} />
    }
  }

  const handleCopyPath = async () => {
    if (data?.event.path) {
      try {
        await navigator.clipboard.writeText(data.event.path)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('Failed to copy path:', err)
      }
    }
  }

  const handleViewDiff = () => {
    if (data?.diff) {
      // Navigate to diff viewer with the diff ID
      navigate(`/diffs?diffId=${data.diff.id}`)
      onClose()
    }
  }

  const getFileName = (path: string) => {
    const parts = path.split('/')
    return parts[parts.length - 1]
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center flex-1 min-w-0">
            <div className={`p-2 rounded-full mr-3 border ${data ? getEventTypeColor(data.event.type) : 'bg-gray-100'}`}>
              {data ? getEventTypeIcon(data.event.type) : <File className="h-6 w-6" />}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-medium text-gray-900 truncate">
                {data ? getFileName(data.event.path) : 'Loading...'}
              </h3>
              <p className="text-sm text-gray-500">
                {data ? (
                  <span className="capitalize">{data.event.type} event</span>
                ) : (
                  'Loading event details...'
                )}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 ml-4"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">Loading event details...</span>
            </div>
          ) : error ? (
            <div className="text-center p-8">
              <div className="p-3 bg-red-100 rounded-full inline-block mb-4">
                <X className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Event</h3>
              <p className="text-gray-600">{error}</p>
              <button
                onClick={fetchEventDetails}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : data ? (
            <div className="space-y-6">
              {/* Event Metadata */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Event Details</h4>
                <div className="space-y-3">
                  {/* Full Path */}
                  <div className="flex items-start">
                    <File className="h-4 w-4 text-gray-400 mr-2 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-gray-500 mb-1">File Path</div>
                      <div className="text-sm text-gray-900 font-mono break-all">
                        {data.event.path}
                      </div>
                    </div>
                  </div>

                  {/* Timestamp */}
                  <div className="flex items-start">
                    <Clock className="h-4 w-4 text-gray-400 mr-2 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 mb-1">Timestamp</div>
                      <div className="text-sm text-gray-900">
                        {formatDate(data.event.timestamp)}
                        <span className="text-gray-500 ml-2">({getRelativeTime(data.event.timestamp)})</span>
                      </div>
                    </div>
                  </div>

                  {/* File Size */}
                  {data.event.size !== undefined && (
                    <div className="flex items-start">
                      <HardDrive className="h-4 w-4 text-gray-400 mr-2 mt-0.5" />
                      <div className="flex-1">
                        <div className="text-xs text-gray-500 mb-1">File Size</div>
                        <div className="text-sm text-gray-900">
                          {formatFileSize(data.event.size)}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Diff Preview */}
              {data.diff ? (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Changes</h4>
                  <div className="space-y-3">
                    {/* Stats */}
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center">
                        <span className="text-green-600 font-medium">+{data.diff.linesAdded}</span>
                        <span className="text-gray-500 ml-1">additions</span>
                      </div>
                      <div className="flex items-center">
                        <span className="text-red-600 font-medium">-{data.diff.linesRemoved}</span>
                        <span className="text-gray-500 ml-1">deletions</span>
                      </div>
                    </div>

                    {/* Diff Content Preview */}
                    <div className="bg-white rounded border border-gray-200 p-3 max-h-64 overflow-auto">
                      <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                        {data.diff.diffContent}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                  <p className="text-sm text-yellow-800">
                    No diff content available for this event. This may occur for file deletions or if the diff data hasn't been captured yet.
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer with Actions */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={handleCopyPath}
            disabled={!data}
            className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {copied ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copy Path
              </>
            )}
          </button>

          {data?.diff && (
            <button
              onClick={handleViewDiff}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View Full Diff
            </button>
          )}

          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
