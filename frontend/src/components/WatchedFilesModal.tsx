import { useState, useEffect } from 'react'
import { X, FolderOpen, FileText, Clock, HardDrive } from 'lucide-react'
import { apiFetch } from '../utils/api'

interface WatchedFile {
  name: string
  path: string
  relativePath: string
  size: number
  lastModified: number
}

interface WatchedDirectory {
  path: string
  name: string
  fileCount: number
  files: WatchedFile[]
}

interface WatchedFilesData {
  isActive: boolean
  directories: WatchedDirectory[]
  totalFiles: number
  totalDirectories: number
}

interface WatchedFilesModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function WatchedFilesModal({ isOpen, onClose }: WatchedFilesModalProps) {
  const [data, setData] = useState<WatchedFilesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      fetchWatchedFiles()
    }
  }, [isOpen])

  const fetchWatchedFiles = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiFetch('/api/files/watched')
      
      if (!response.ok) {
        throw new Error('Failed to fetch watched files')
      }
      
      const watchedData = await response.json()
      setData(watchedData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watched files')
    } finally {
      setLoading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-full mr-3">
              <FolderOpen className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">Watched Files</h3>
              <p className="text-sm text-gray-500">
                {data ? `${data.totalFiles} files in ${data.totalDirectories} directories` : 'Loading...'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">Loading watched files...</span>
            </div>
          ) : error ? (
            <div className="text-center p-8">
              <div className="p-3 bg-red-100 rounded-full inline-block mb-4">
                <X className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Files</h3>
              <p className="text-gray-600">{error}</p>
              <button
                onClick={fetchWatchedFiles}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : !data?.isActive ? (
            <div className="text-center p-8">
              <div className="p-3 bg-yellow-100 rounded-full inline-block mb-4">
                <Clock className="h-8 w-8 text-yellow-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Monitoring Inactive</h3>
              <p className="text-gray-600">File monitoring is currently stopped. Start monitoring to see watched files.</p>
            </div>
          ) : data.directories.length === 0 ? (
            <div className="text-center p-8">
              <div className="p-3 bg-gray-100 rounded-full inline-block mb-4">
                <FolderOpen className="h-8 w-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Directories Watched</h3>
              <p className="text-gray-600">No directories are currently being monitored.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {data.directories.map((directory, index) => (
                <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                  {/* Directory Header */}
                  <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <FolderOpen className="h-5 w-5 text-blue-600 mr-2" />
                        <div>
                          <h4 className="text-sm font-medium text-gray-900">{directory.name}</h4>
                          <p className="text-xs text-gray-500">{directory.path}</p>
                        </div>
                      </div>
                      <div className="text-sm text-gray-600">
                        {directory.fileCount} file{directory.fileCount !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>

                  {/* Files List */}
                  <div className="divide-y divide-gray-100">
                    {directory.files.length > 0 ? (
                      <>
                        {directory.files.map((file, fileIndex) => (
                          <div key={fileIndex} className="px-4 py-3 hover:bg-gray-50">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center flex-1 min-w-0">
                                <FileText className="h-4 w-4 text-gray-400 mr-3 flex-shrink-0" />
                                <div className="min-w-0 flex-1">
                                  <p className="text-sm font-medium text-gray-900 truncate">
                                    {file.name}
                                  </p>
                                  <p className="text-xs text-gray-500 truncate">
                                    {file.relativePath}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center space-x-4 text-xs text-gray-500">
                                <div className="flex items-center">
                                  <HardDrive className="h-3 w-3 mr-1" />
                                  {formatFileSize(file.size)}
                                </div>
                                <div className="flex items-center">
                                  <Clock className="h-3 w-3 mr-1" />
                                  {formatDate(file.lastModified)}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                        {directory.fileCount > directory.files.length && (
                          <div className="px-4 py-3 bg-gray-50 text-center">
                            <p className="text-sm text-gray-600">
                              And {directory.fileCount - directory.files.length} more file{directory.fileCount - directory.files.length !== 1 ? 's' : ''}...
                            </p>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="px-4 py-8 text-center">
                        <p className="text-sm text-gray-500">No markdown files found in this directory</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}