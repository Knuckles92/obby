import { useState, useEffect } from 'react'
import { Server, Activity, Circle, RefreshCw, Play, Square, RotateCw, Clock, Cpu, HardDrive, Terminal, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { Service, ServiceEvent, ServicesResponse, ServiceEventsResponse, ServiceActionResponse } from '../types/services'
import { apiFetch } from '../utils/api'

export default function Services() {
  const [services, setServices] = useState<Service[]>([])
  const [events, setEvents] = useState<ServiceEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [eventsLoading, setEventsLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [selectedService, setSelectedService] = useState<Service | null>(null)
  const [showEventLog, setShowEventLog] = useState(false)

  useEffect(() => {
    fetchServices()
    fetchEvents()

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      fetchServices()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const fetchServices = async () => {
    try {
      const response = await apiFetch('/api/services')
      const data: ServicesResponse = await response.json()
      if (data.success) {
        setServices(data.services)
      }
    } catch (error) {
      console.error('Error fetching services:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchEvents = async () => {
    try {
      const response = await apiFetch('/api/services/events/all?limit=50')
      const data: ServiceEventsResponse = await response.json()
      if (data.success) {
        setEvents(data.events)
      }
    } catch (error) {
      console.error('Error fetching events:', error)
    } finally {
      setEventsLoading(false)
    }
  }

  const handleServiceAction = async (serviceId: number, action: 'start' | 'stop' | 'restart') => {
    setActionLoading(serviceId)
    try {
      const response = await apiFetch(`/api/services/${serviceId}/${action}`, {
        method: 'POST'
      })
      const data: ServiceActionResponse = await response.json()

      if (data.success) {
        // Refresh services after action
        setTimeout(fetchServices, 1000)
        setTimeout(fetchEvents, 1000)
      } else {
        alert(`Failed to ${action} service: ${data.message}`)
      }
    } catch (error) {
      console.error(`Error ${action}ing service:`, error)
      alert(`Error ${action}ing service: ${error}`)
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'running':
        return <Circle className="w-3 h-3 fill-green-500 text-green-500 animate-pulse" />
      case 'stopped':
        return <Circle className="w-3 h-3 fill-gray-400 text-gray-400" />
      case 'degraded':
        return <Circle className="w-3 h-3 fill-yellow-500 text-yellow-500" />
      case 'error':
        return <Circle className="w-3 h-3 fill-red-500 text-red-500 animate-pulse" />
      default:
        return <Circle className="w-3 h-3 fill-gray-300 text-gray-300" />
    }
  }

  const getHealthIcon = (health?: string) => {
    switch (health) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'unhealthy':
        return <XCircle className="w-4 h-4 text-red-500" />
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />
    }
  }

  const getServiceTypeIcon = (type: string) => {
    return type === 'python' ? (
      <Terminal className="w-5 h-5 text-blue-500" />
    ) : (
      <Server className="w-5 h-5 text-cyan-500" />
    )
  }

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'N/A'
    const date = new Date(timestamp)
    return date.toLocaleString()
  }

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'start':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'stop':
        return 'text-gray-600 bg-gray-50 border-gray-200'
      case 'restart':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'health_check_pass':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'health_check_fail':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600">Loading services...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Server className="w-8 h-8 text-blue-600" />
              Service Management
            </h1>
            <p className="mt-2 text-gray-600">
              Monitor and manage all backend services
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowEventLog(!showEventLog)}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center gap-2 transition-colors"
            >
              <Activity className="w-4 h-4" />
              {showEventLog ? 'Hide' : 'Show'} Event Log
            </button>
            <button
              onClick={fetchServices}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {services.map((service) => (
          <div
            key={service.id}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            {/* Service Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {getServiceTypeIcon(service.service_type)}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    {service.name}
                    {getStatusIcon(service.status)}
                  </h3>
                  <p className="text-sm text-gray-600">{service.description}</p>
                </div>
              </div>
              {getHealthIcon(service.health)}
            </div>

            {/* Service Details */}
            <div className="space-y-2 mb-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Type:</span>
                <span className="font-medium text-gray-900 capitalize">{service.service_type}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Status:</span>
                <span className={`font-medium capitalize ${
                  service.status === 'running' ? 'text-green-600' :
                  service.status === 'error' ? 'text-red-600' :
                  service.status === 'degraded' ? 'text-yellow-600' :
                  'text-gray-600'
                }`}>
                  {service.status || 'Unknown'}
                </span>
              </div>
              {service.grpc_port && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">gRPC Port:</span>
                  <span className="font-mono text-gray-900">{service.grpc_port}</span>
                </div>
              )}
              {service.http_port && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">HTTP Port:</span>
                  <span className="font-mono text-gray-900">{service.http_port}</span>
                </div>
              )}
              {service.uptime_seconds !== undefined && service.status === 'running' && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Uptime:
                  </span>
                  <span className="font-medium text-gray-900">{formatUptime(service.uptime_seconds)}</span>
                </div>
              )}
              {service.memory_mb && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 flex items-center gap-1">
                    <HardDrive className="w-3 h-3" />
                    Memory:
                  </span>
                  <span className="font-medium text-gray-900">{service.memory_mb.toFixed(1)} MB</span>
                </div>
              )}
              {service.cpu_percent && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 flex items-center gap-1">
                    <Cpu className="w-3 h-3" />
                    CPU:
                  </span>
                  <span className="font-medium text-gray-900">{service.cpu_percent.toFixed(1)}%</span>
                </div>
              )}
            </div>

            {/* Health Check Message */}
            {service.health_check_message && (
              <div className="mb-4 p-2 bg-gray-50 rounded border border-gray-200">
                <p className="text-xs text-gray-600">{service.health_check_message}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2">
              {service.status === 'stopped' && service.service_type === 'go' && (
                <button
                  onClick={() => handleServiceAction(service.id, 'start')}
                  disabled={actionLoading === service.id}
                  className="flex-1 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm transition-colors"
                >
                  {actionLoading === service.id ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Start
                </button>
              )}
              {service.status === 'running' && service.service_type === 'go' && (
                <>
                  <button
                    onClick={() => handleServiceAction(service.id, 'restart')}
                    disabled={actionLoading === service.id}
                    className="flex-1 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm transition-colors"
                  >
                    {actionLoading === service.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <RotateCw className="w-4 h-4" />
                    )}
                    Restart
                  </button>
                  <button
                    onClick={() => handleServiceAction(service.id, 'stop')}
                    disabled={actionLoading === service.id}
                    className="flex-1 px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm transition-colors"
                  >
                    {actionLoading === service.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                    Stop
                  </button>
                </>
              )}
              {service.service_type === 'python' && (
                <div className="flex-1 px-3 py-2 bg-gray-100 text-gray-500 rounded text-center text-sm">
                  Cannot control backend
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Event Log */}
      {showEventLog && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Recent Events
          </h2>

          {eventsLoading ? (
            <div className="text-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-500" />
              <p className="text-gray-600">Loading events...</p>
            </div>
          ) : events.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No events recorded yet</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {events.map((event) => (
                <div
                  key={event.id}
                  className={`p-3 rounded border ${getEventTypeColor(event.event_type)}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">{event.service_name}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-white border">
                          {event.event_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      {event.message && (
                        <p className="text-sm">{event.message}</p>
                      )}
                      {event.details && (
                        <p className="text-xs mt-1 opacity-75">{event.details}</p>
                      )}
                    </div>
                    <span className="text-xs whitespace-nowrap ml-4">
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summary Stats */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Services</p>
              <p className="text-2xl font-bold text-gray-900">{services.length}</p>
            </div>
            <Server className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Running</p>
              <p className="text-2xl font-bold text-green-600">
                {services.filter(s => s.status === 'running').length}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Stopped</p>
              <p className="text-2xl font-bold text-gray-600">
                {services.filter(s => s.status === 'stopped').length}
              </p>
            </div>
            <Circle className="w-8 h-8 text-gray-400" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Healthy</p>
              <p className="text-2xl font-bold text-green-600">
                {services.filter(s => s.health === 'healthy').length}
              </p>
            </div>
            <Activity className="w-8 h-8 text-green-500" />
          </div>
        </div>
      </div>
    </div>
  )
}
