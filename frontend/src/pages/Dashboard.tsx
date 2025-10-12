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
  Trash2,
  TrendingUp,
  Zap,
  Database,
  Eye
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

  // Listen for admin-triggered clear events to refresh immediately
  useEffect(() => {
    const onCleared = () => {
      // Force a refresh outside of the 5s polling cycle
      fetchDashboardData()
    }
    window.addEventListener('dashboard-data-cleared', onCleared as EventListener)
    return () => {
      window.removeEventListener('dashboard-data-cleared', onCleared as EventListener)
    }
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [statusRes, eventsRes, diffsRes] = await Promise.all([
        apiFetch('/api/monitor/status'),
        apiFetch('/api/files/events?limit=10'),
        apiFetch('/api/files/diffs?limit=5')
      ])

      const statusData = await statusRes.json()
      const eventsData = await eventsRes.json()
      const diffsData = await diffsRes.json()

      setStatus(statusData)
      setRecentEvents(eventsData.events || [])
      setRecentDiffs(diffsData.diffs || [])

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
      const response = await apiFetch('/api/data/events/clear', {
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
    <div className="min-h-screen">
      {/* Modern Header */}
      <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
      }}>
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

        <div className="relative z-10 flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                <Eye className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            </div>
            <p className="text-blue-100 text-lg">Monitor your note changes in real-time with intelligent insights</p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Status Indicator */}
            <div className={`flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border transition-all duration-300 ${
              status.isActive
                ? 'bg-green-500/20 border-green-400/30 text-green-100'
                : 'bg-red-500/20 border-red-400/30 text-red-100'
            }`}>
              <div className={`w-2 h-2 rounded-full animate-pulse ${
                status.isActive ? 'bg-green-400' : 'bg-red-400'
              }`}></div>
              <span className="text-sm font-medium">
                {status.isActive ? 'Monitoring Active' : 'Monitoring Inactive'}
              </span>
            </div>

            {/* Control Button */}
            <button
              onClick={toggleMonitoring}
              disabled={monitoringLoading}
              className={`relative overflow-hidden px-6 py-3 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group ${
                status.isActive
                  ? 'bg-red-500/20 hover:bg-red-500/30 border border-red-400/30 text-red-100 hover:text-white'
                  : 'bg-green-500/20 hover:bg-green-500/30 border border-green-400/30 text-green-100 hover:text-white'
              }`}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
              <div className="relative flex items-center space-x-2">
                {monitoringLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                    <span>{status.isActive ? 'Stopping...' : 'Starting...'}</span>
                  </>
                ) : status.isActive ? (
                  <>
                    <Square className="h-4 w-4" />
                    <span>Stop Monitoring</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    <span>Start Monitoring</span>
                  </>
                )}
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Enhanced Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Monitoring Status Card */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-success) 5%, var(--color-primary) 5%)'
          }}></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl shadow-lg" style={{
                backgroundColor: status.isActive ? 'var(--color-success)' : 'var(--color-error)',
                boxShadow: `0 4px 6px -1px ${status.isActive ? 'var(--color-success)' : 'var(--color-error)'}20, 0 2px 4px -2px ${status.isActive ? 'var(--color-success)' : 'var(--color-error)'}20`
              }}>
                {status.isActive ? (
                  <CheckCircle className="h-6 w-6" style={{ color: 'var(--color-text-inverse)' }} />
                ) : (
                  <AlertCircle className="h-6 w-6" style={{ color: 'var(--color-text-inverse)' }} />
                )}
              </div>
              <TrendingUp className="h-5 w-5 transition-colors" style={{
                color: 'var(--color-text-secondary)',
                filter: 'brightness(0.7)'
              }} />
            </div>
            <div>
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Monitoring Status</p>
              <p className="text-2xl font-bold" style={{
                color: status.isActive ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {status.isActive ? 'Active' : 'Inactive'}
              </p>
              <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                <div className="h-full transition-all duration-1000" style={{
                  backgroundColor: status.isActive ? 'var(--color-success)' : 'var(--color-error)',
                  width: status.isActive ? '100%' : '0%'
                }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Watched Files Card */}
        <div
          className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer"
          onClick={() => setWatchedFilesModalOpen(true)}
          style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-info) 5%, var(--color-primary) 5%)'
          }}></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl shadow-lg" style={{
                backgroundColor: 'var(--color-info)',
                boxShadow: '0 4px 6px -1px var(--color-info)20, 0 2px 4px -2px var(--color-info)20'
              }}>
                <FolderOpen className="h-6 w-6" style={{ color: 'var(--color-text-inverse)' }} />
              </div>
              <Database className="h-5 w-5 transition-colors" style={{
                color: 'var(--color-info)',
                filter: 'brightness(0.8)'
              }} />
            </div>
            <div>
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Watched Files</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{status.totalFiles}</p>
              <div className="mt-3 flex items-center space-x-1">
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-divider)' }}>
                  <div className="h-full rounded-full transition-all duration-1000"
                       style={{
                         backgroundColor: 'var(--color-info)',
                         width: `${Math.min((status.totalFiles / 100) * 100, 100)}%`
                       }}></div>
                </div>
                <span className="text-xs font-medium" style={{ color: 'var(--color-info)' }}>{status.totalFiles}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Events Today Card */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-warning) 5%, var(--color-accent) 5%)'
          }}></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl shadow-lg" style={{
                backgroundColor: 'var(--color-warning)',
                boxShadow: '0 4px 6px -1px var(--color-warning)20, 0 2px 4px -2px var(--color-warning)20'
              }}>
                <Activity className="h-6 w-6" style={{ color: 'var(--color-text-inverse)' }} />
              </div>
              <Zap className="h-5 w-5 transition-colors" style={{
                color: 'var(--color-warning)',
                filter: 'brightness(0.8)'
              }} />
            </div>
            <div>
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Events Today</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{status.eventsToday}</p>
              <div className="mt-3 flex items-center space-x-1">
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-divider)' }}>
                  <div className="h-full rounded-full transition-all duration-1000"
                       style={{
                         backgroundColor: 'var(--color-warning)',
                         width: `${Math.min((status.eventsToday / 50) * 100, 100)}%`
                       }}></div>
                </div>
                <span className="text-xs font-medium" style={{ color: 'var(--color-warning)' }}>{status.eventsToday}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Diffs Card */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-success) 5%, var(--color-info) 5%)'
          }}></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl shadow-lg" style={{
                backgroundColor: 'var(--color-success)',
                boxShadow: '0 4px 6px -1px var(--color-success)20, 0 2px 4px -2px var(--color-success)20'
              }}>
                <GitBranch className="h-6 w-6" style={{ color: 'var(--color-text-inverse)' }} />
              </div>
              <GitBranch className="h-5 w-5 transition-colors" style={{
                color: 'var(--color-success)',
                filter: 'brightness(0.8)'
              }} />
            </div>
            <div>
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Recent Diffs</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{recentDiffs.length}</p>
              <div className="mt-3 flex items-center space-x-1">
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-divider)' }}>
                  <div className="h-full rounded-full transition-all duration-1000"
                       style={{
                         backgroundColor: 'var(--color-success)',
                         width: `${Math.min((recentDiffs.length / 10) * 100, 100)}%`
                       }}></div>
                </div>
                <span className="text-xs font-medium" style={{ color: 'var(--color-success)' }}>{recentDiffs.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>


      {/* Enhanced Activity Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Events Section */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border hover:shadow-xl transition-all duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-info) 3%, var(--color-primary) 3%)'
          }}></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-info)' }}>
                  <Activity className="h-5 w-5" style={{ color: 'var(--color-text-inverse)' }} />
                </div>
                <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>Recent Events</h3>
              </div>
              {recentEvents.length > 0 && (
                <button
                  onClick={() => setClearEventsDialogOpen(true)}
                  className="flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 hover:shadow-sm"
                  style={{
                    color: 'var(--color-error)',
                    backgroundColor: 'var(--color-error)',
                    border: '1px solid var(--color-error)',
                    filter: 'brightness(0.95)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.filter = 'brightness(1.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.filter = 'brightness(0.95)'}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear All
                </button>
              )}
            </div>

            {recentEvents.length > 0 ? (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {recentEvents.map((event, index) => (
                  <div key={event.id} className="group/item relative overflow-hidden rounded-xl p-4 shadow-sm border hover:shadow-md transition-all duration-200 hover:-translate-y-0.5" style={{
                    backgroundColor: 'var(--color-background)',
                    borderColor: 'var(--color-divider)'
                  }}>
                    <div className="absolute inset-0 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" style={{
                      background: 'linear-gradient(90deg, transparent, var(--color-surface), transparent)'
                    }}></div>
                    <div className="relative flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0 w-3 h-3 rounded-full shadow-sm" style={{
                          backgroundColor: event.type === 'created' ? 'var(--color-success)' :
                                           event.type === 'modified' ? 'var(--color-warning)' :
                                           event.type === 'deleted' ? 'var(--color-error)' :
                                           'var(--color-info)',
                          boxShadow: `0 0 0 3px ${event.type === 'created' ? 'var(--color-success)' :
                                               event.type === 'modified' ? 'var(--color-warning)' :
                                               event.type === 'deleted' ? 'var(--color-error)' :
                                               'var(--color-info)'}15`
                        }} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>{event.path.split('/').pop()}</p>
                          <p className="text-xs capitalize flex items-center" style={{ color: 'var(--color-text-secondary)' }}>
                            <span className="inline-block w-2 h-2 rounded-full mr-2" style={{
                              backgroundColor: event.type === 'created' ? 'var(--color-success)' :
                                               event.type === 'modified' ? 'var(--color-warning)' :
                                               event.type === 'deleted' ? 'var(--color-error)' :
                                               'var(--color-info)'
                            }}></span>
                            {event.type}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center text-xs px-2 py-1 rounded-md" style={{
                        color: 'var(--color-text-secondary)',
                        backgroundColor: 'var(--color-surface)'
                      }}>
                        <Clock className="h-3 w-3 mr-1" />
                        {formatTimeAgo(event.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: 'var(--color-surface)' }}>
                  <Activity className="h-8 w-8" style={{ color: 'var(--color-text-secondary)' }} />
                </div>
                <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>No recent events</p>
                <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Events will appear here when files are modified</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Diffs Section */}
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border hover:shadow-xl transition-all duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-success) 3%, var(--color-info) 3%)'
          }}></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-success)' }}>
                  <GitBranch className="h-5 w-5" style={{ color: 'var(--color-text-inverse)' }} />
                </div>
                <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>Recent Changes</h3>
              </div>
              <div className="text-xs px-2 py-1 rounded-md" style={{
                color: 'var(--color-text-secondary)',
                backgroundColor: 'var(--color-surface)'
              }}>
                Last 5 changes
              </div>
            </div>

            {recentDiffs.length > 0 ? (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {recentDiffs.map((diff, index) => (
                  <div key={diff.id} className="group/item relative overflow-hidden rounded-xl p-4 shadow-sm border hover:shadow-md transition-all duration-200 hover:-translate-y-0.5" style={{
                    backgroundColor: 'var(--color-background)',
                    borderColor: 'var(--color-divider)'
                  }}>
                    <div className="absolute inset-0 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" style={{
                      background: 'linear-gradient(90deg, transparent, var(--color-surface), transparent)'
                    }}></div>
                    <div className="relative">
                      <div className="flex items-start justify-between mb-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>{diff.filePath.split('/').pop()}</p>
                          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{diff.filePath.split('/').slice(0, -1).join('/') || 'Root'}</p>
                        </div>
                        <div className="flex items-center text-xs px-2 py-1 rounded-md ml-3" style={{
                          color: 'var(--color-text-secondary)',
                          backgroundColor: 'var(--color-surface)'
                        }}>
                          <Clock className="h-3 w-3 mr-1" />
                          {formatTimeAgo(diff.timestamp)}
                        </div>
                      </div>
                      <div className="rounded-lg p-3" style={{
                        backgroundColor: 'var(--color-surface)',
                        borderLeft: `4px solid var(--color-success)`
                      }}>
                        <p className="text-xs leading-relaxed line-clamp-3" style={{ color: 'var(--color-text-primary)' }}>{diff.content}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: 'var(--color-surface)' }}>
                  <GitBranch className="h-8 w-8" style={{ color: 'var(--color-text-secondary)' }} />
                </div>
                <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>No recent changes</p>
                <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>File changes will appear here</p>
              </div>
            )}
          </div>
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