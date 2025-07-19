import { useState, useEffect } from 'react'
import { 
  Activity, 
  FileText, 
  FolderOpen, 
  GitBranch, 
  Play, 
  Square,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react'
import { MonitoringStatus, FileEvent, DiffEntry } from '../types'

export default function Dashboard() {
  const [status, setStatus] = useState<MonitoringStatus>({
    isActive: false,
    watchedPaths: [],
    totalFiles: 0,
    eventsToday: 0
  })
  const [recentEvents, setRecentEvents] = useState<FileEvent[]>([])
  const [recentDiffs, setRecentDiffs] = useState<DiffEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [statusRes, eventsRes, diffsRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/events?limit=10'),
        fetch('/api/diffs?limit=5')
      ])

      const statusData = await statusRes.json()
      const eventsData = await eventsRes.json()
      const diffsData = await diffsRes.json()

      setStatus(statusData)
      setRecentEvents(eventsData)
      setRecentDiffs(diffsData)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleMonitoring = async () => {
    try {
      const endpoint = status.isActive ? '/api/monitor/stop' : '/api/monitor/start'
      const response = await fetch(endpoint, { method: 'POST' })
      
      if (response.ok) {
        fetchDashboardData()
      }
    } catch (error) {
      console.error('Error toggling monitoring:', error)
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Monitor your note changes in real-time</p>
        </div>
        
        <button
          onClick={toggleMonitoring}
          className={`flex items-center px-4 py-2 rounded-md font-medium transition-colors ${
            status.isActive
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {status.isActive ? (
            <>
              <Square className="h-4 w-4 mr-2" />
              Stop Monitoring
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Start Monitoring
            </>
          )}
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className={`p-2 rounded-md ${status.isActive ? 'bg-green-100' : 'bg-red-100'}`}>
              {status.isActive ? (
                <CheckCircle className="h-6 w-6 text-green-600" />
              ) : (
                <AlertCircle className="h-6 w-6 text-red-600" />
              )}
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Status</p>
              <p className={`text-lg font-semibold ${status.isActive ? 'text-green-600' : 'text-red-600'}`}>
                {status.isActive ? 'Active' : 'Inactive'}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-md">
              <FolderOpen className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Watched Files</p>
              <p className="text-lg font-semibold text-gray-900">{status.totalFiles}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-md">
              <Activity className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Events Today</p>
              <p className="text-lg font-semibold text-gray-900">{status.eventsToday}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-md">
              <GitBranch className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Recent Diffs</p>
              <p className="text-lg font-semibold text-gray-900">{recentDiffs.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Watched Paths */}
      {status.watchedPaths.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Watched Directories</h3>
          <div className="space-y-2">
            {status.watchedPaths.map((path, index) => (
              <div key={index} className="flex items-center text-sm">
                <FolderOpen className="h-4 w-4 text-gray-400 mr-2" />
                <span className="text-gray-600">{path}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Events */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Recent Events</h3>
            <Activity className="h-5 w-5 text-gray-400" />
          </div>
          
          {recentEvents.length > 0 ? (
            <div className="space-y-3">
              {recentEvents.map((event) => (
                <div key={event.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                  <div className="flex items-center">
                    <div className={`w-2 h-2 rounded-full mr-3 ${
                      event.type === 'created' ? 'bg-green-500' :
                      event.type === 'modified' ? 'bg-yellow-500' :
                      event.type === 'deleted' ? 'bg-red-500' :
                      'bg-blue-500'
                    }`} />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{event.path}</p>
                      <p className="text-xs text-gray-600 capitalize">{event.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center text-xs text-gray-500">
                    <Clock className="h-3 w-3 mr-1" />
                    {formatTimeAgo(event.timestamp)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600 text-center py-8">No recent events</p>
          )}
        </div>

        {/* Recent Diffs */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Recent Diffs</h3>
            <GitBranch className="h-5 w-5 text-gray-400" />
          </div>
          
          {recentDiffs.length > 0 ? (
            <div className="space-y-3">
              {recentDiffs.map((diff) => (
                <div key={diff.id} className="p-3 bg-gray-50 rounded-md">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-900">{diff.filePath}</p>
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimeAgo(diff.timestamp)}
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 line-clamp-2">{diff.content}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600 text-center py-8">No recent diffs</p>
          )}
        </div>
      </div>
    </div>
  )
}