import { useState, useEffect } from 'react'
import {
  Activity,
  FolderOpen,
  GitBranch,
  Play,
  Square,
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2
} from 'lucide-react'
import { MonitoringStatus, FileEvent, DiffEntry } from '../types'
import ConfirmationDialog from '../components/ConfirmationDialog'
import WatchedFilesModal from '../components/WatchedFilesModal'
import { apiFetch } from '../utils/api'

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
  const [clearEventsDialogOpen, setClearEventsDialogOpen] = useState(false)
  const [clearEventsLoading, setClearEventsLoading] = useState(false)
  const [monitoringLoading, setMonitoringLoading] = useState(false)
  const [autoStartAttempted, setAutoStartAttempted] = useState(false)
  const [watchedFilesModalOpen, setWatchedFilesModalOpen] = useState(false)

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [statusRes, eventsRes, diffsRes] = await Promise.all([
        apiFetch('/api/status'),
        apiFetch('/api/events?limit=10'),
        apiFetch('/api/diffs?limit=5')
      ])

      const statusData = await statusRes.json()
      const eventsData = await eventsRes.json()
      const diffsData = await diffsRes.json()

      setStatus(statusData)
      setRecentEvents(eventsData)
      setRecentDiffs(diffsData)

      // Auto-start monitoring if it's not active and we haven't tried yet
      if (!statusData.isActive && !autoStartAttempted) {
        setAutoStartAttempted(true)
        console.log('Auto-starting monitoring...')
        toggleMonitoring()
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleMonitoring = async () => {
    try {
      setMonitoringLoading(true)
      const endpoint = status.isActive ? '/api/monitor/stop' : '/api/monitor/start'
      const response = await apiFetch(endpoint, { method: 'POST' })
      
      if (response.ok) {
        // Add a small delay to show the loading state
        await new Promise(resolve => setTimeout(resolve, 500))
        fetchDashboardData()
      } else {
        const error = await response.json()
        console.error('Error toggling monitoring:', error.error)
        alert('Failed to toggle monitoring: ' + error.error)
      }
    } catch (error) {
      console.error('Error toggling monitoring:', error)
      alert('Failed to toggle monitoring. Please try again.')
    } finally {
      setMonitoringLoading(false)
    }
  }

  const handleClearEvents = async () => {
    try {
      setClearEventsLoading(true)
      const response = await apiFetch('/api/events/clear', {
        method: 'POST'
      })
      
      if (response.ok) {
        const result = await response.json()
        console.log(result.message)
        // Refresh the dashboard data
        await fetchDashboardData()
        setClearEventsDialogOpen(false)
      } else {
        const error = await response.json()
        console.error('Error clearing events:', error.error)
        alert('Failed to clear events: ' + error.error)
      }
    } catch (error) {
      console.error('Error clearing events:', error)
      alert('Failed to clear events. Please try again.')
    } finally {
      setClearEventsLoading(false)
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
          disabled={monitoringLoading}
          className={`flex items-center px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 ${
            status.isActive
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {monitoringLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              {status.isActive ? 'Stopping...' : 'Starting...'}
            </>
          ) : status.isActive ? (
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

        <div 
          className="card cursor-pointer hover:shadow-md transition-shadow" 
          onClick={() => setWatchedFilesModalOpen(true)}
        >
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


      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Events */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <h3 className="text-lg font-medium text-gray-900">Recent Events</h3>
              <Activity className="h-5 w-5 text-gray-400 ml-2" />
            </div>
            {recentEvents.length > 0 && (
              <button
                onClick={() => setClearEventsDialogOpen(true)}
                className="flex items-center px-3 py-1 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
              >
                <Trash2 className="h-3 w-3 mr-1" />
                Clear
              </button>
            )}
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

      {/* Clear Events Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={clearEventsDialogOpen}
        onClose={() => setClearEventsDialogOpen(false)}
        onConfirm={handleClearEvents}
        title="Clear Recent Events"
        message="Are you sure you want to clear all recent events? This will remove the event history from the dashboard."
        confirmText="Clear Events"
        cancelText="Cancel"
        danger={true}
        loading={clearEventsLoading}
      />

      {/* Watched Files Modal */}
      <WatchedFilesModal
        isOpen={watchedFilesModalOpen}
        onClose={() => setWatchedFilesModalOpen(false)}
      />
    </div>
  )
}