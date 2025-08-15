import { useState, useEffect } from 'react'
import { 
  Shield, 
  Database, 
  Settings, 
  Activity, 
  Server, 
  HardDrive, 
  Cpu, 
  MemoryStick, 
  RefreshCw,
  Trash2,
  Download,
  Upload,
  AlertTriangle
} from 'lucide-react'
import { apiRequest } from '../utils/api'

interface SystemStats {
  stats: {
    system: {
      cpu_percent: number
      cpu_count: number
      memory_total: number
      memory_available: number
      memory_percent: number
      disk_total: number
      disk_used: number
      disk_free: number
      disk_percent: number
    }
    process: {
      memory_rss: number
      memory_vms: number
      memory_percent: number
      cpu_percent: number
      pid: number
      num_threads: number
    }
  }
  timestamp: number
}

interface DatabaseStats {
  database_stats: {
    total_records: number
    total_diffs: number
    index_size: string
    last_optimized: string
    query_performance: number
  }
  success: boolean
}

export default function Administration() {
  const [activeTab, setActiveTab] = useState('overview')
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [databaseStats, setDatabaseStats] = useState<DatabaseStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSystemStats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch system stats
      const statsResponse = await apiRequest('/api/admin/system/stats')
      setSystemStats(statsResponse)
      
      // Fetch database stats
      const dbStatsResponse = await apiRequest('/api/admin/database/stats')
      setDatabaseStats(dbStatsResponse)
    } catch (err) {
      setError('Failed to fetch system statistics')
      console.error('Error fetching stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const optimizeDatabase = async () => {
    try {
      setLoading(true)
      const response = await apiRequest('/api/admin/database/optimize', { method: 'POST' })
      alert(response.message || 'Database optimization completed successfully!')
      fetchSystemStats()
    } catch (err) {
      setError('Failed to optimize database')
      console.error('Error optimizing database:', err)
    } finally {
      setLoading(false)
    }
  }

  const clearLogs = async () => {
    if (confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
      try {
        setLoading(true)
        const response = await apiRequest('/api/admin/system/clear-logs', { method: 'POST' })
        alert(response.message || 'Logs cleared successfully!')
        fetchSystemStats()
      } catch (err) {
        setError('Failed to clear logs')
        console.error('Error clearing logs:', err)
      } finally {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    fetchSystemStats()
  }, [])

  const tabs = [
    { id: 'overview', name: 'System Overview', icon: Activity },
    { id: 'database', name: 'Database', icon: Database },
    { id: 'config', name: 'Configuration', icon: Settings },
  ]

  const StatCard = ({ title, value, icon: Icon, color = 'blue', percentage }: {
    title: string
    value: string | number
    icon: any
    color?: string
    percentage?: number
  }) => (
    <div style={{
      backgroundColor: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--border-radius-lg)',
      padding: 'var(--spacing-lg)',
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--spacing-md)'
    }}>
      <div style={{
        backgroundColor: `var(--color-${color})`,
        borderRadius: 'var(--border-radius-md)',
        padding: 'var(--spacing-sm)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Icon style={{ width: '1.5rem', height: '1.5rem', color: 'white' }} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ 
          fontSize: 'var(--font-size-sm)', 
          color: 'var(--color-text-secondary)',
          marginBottom: 'var(--spacing-xs)'
        }}>
          {title}
        </div>
        <div style={{ 
          fontSize: 'var(--font-size-xl)', 
          fontWeight: 'var(--font-weight-bold)',
          color: 'var(--color-text-primary)'
        }}>
          {value}
        </div>
        {percentage !== undefined && (
          <div style={{
            width: '100%',
            height: '4px',
            backgroundColor: 'var(--color-border)',
            borderRadius: '2px',
            marginTop: 'var(--spacing-xs)',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${percentage}%`,
              height: '100%',
              backgroundColor: `var(--color-${color})`,
              transition: 'width 0.3s ease'
            }} />
          </div>
        )}
      </div>
    </div>
  )

  const ActionButton = ({ onClick, icon: Icon, children, variant = 'primary', disabled = false }: {
    onClick: () => void
    icon: any
    children: React.ReactNode
    variant?: 'primary' | 'secondary' | 'danger'
    disabled?: boolean
  }) => (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-sm)',
        padding: 'var(--spacing-md) var(--spacing-lg)',
        backgroundColor: variant === 'danger' ? 'var(--color-error)' : 
                        variant === 'secondary' ? 'var(--color-surface)' : 'var(--color-primary)',
        color: variant === 'secondary' ? 'var(--color-text-primary)' : 'white',
        border: variant === 'secondary' ? '1px solid var(--color-border)' : 'none',
        borderRadius: 'var(--border-radius-md)',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled || loading ? 0.6 : 1,
        transition: 'all 0.2s ease'
      }}
    >
      <Icon style={{ width: '1rem', height: '1rem' }} />
      {children}
    </button>
  )

  return (
    <div style={{ padding: 'var(--spacing-lg)' }}>
      {/* Header */}
      <div style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-md)' }}>
          <Shield style={{ width: '2rem', height: '2rem', color: 'var(--color-primary)' }} />
          <h1 style={{ 
            fontSize: 'var(--font-size-2xl)', 
            fontWeight: 'var(--font-weight-bold)',
            color: 'var(--color-text-primary)',
            margin: 0
          }}>
            Administration Panel
          </h1>
        </div>
        <p style={{ 
          color: 'var(--color-text-secondary)', 
          fontSize: 'var(--font-size-base)',
          margin: 0
        }}>
          Manage system settings, monitor performance, and maintain your Obby instance
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div style={{
          backgroundColor: 'var(--color-error)',
          color: 'white',
          padding: 'var(--spacing-md)',
          borderRadius: 'var(--border-radius-md)',
          marginBottom: 'var(--spacing-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-sm)'
        }}>
          <AlertTriangle style={{ width: '1.25rem', height: '1.25rem' }} />
          {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{
        borderBottom: '1px solid var(--color-border)',
        marginBottom: 'var(--spacing-xl)'
      }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-md)' }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)',
                padding: 'var(--spacing-md) var(--spacing-lg)',
                backgroundColor: 'transparent',
                border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid var(--color-primary)' : '2px solid transparent',
                color: activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <tab.icon style={{ width: '1.25rem', height: '1.25rem' }} />
              {tab.name}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>System Overview</h2>
            <ActionButton onClick={fetchSystemStats} icon={RefreshCw}>
              Refresh
            </ActionButton>
          </div>

          {systemStats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-xl)' }}>
              <StatCard title="CPU Cores" value={systemStats.stats.system.cpu_count} icon={Server} color="green" />
              <StatCard title="Memory Usage" value={`${Math.round(systemStats.stats.system.memory_percent)}%`} icon={MemoryStick} color="blue" percentage={systemStats.stats.system.memory_percent} />
              <StatCard title="CPU Usage" value={`${Math.round(systemStats.stats.system.cpu_percent)}%`} icon={Cpu} color="orange" percentage={systemStats.stats.system.cpu_percent} />
              <StatCard title="Disk Usage" value={`${Math.round(systemStats.stats.system.disk_percent)}%`} icon={HardDrive} color="purple" percentage={systemStats.stats.system.disk_percent} />
              <StatCard title="Process PID" value={systemStats.stats.process.pid} icon={Activity} color="green" />
              <StatCard title="Process Memory" value={`${Math.round(systemStats.stats.process.memory_percent)}%`} icon={Database} color="blue" percentage={systemStats.stats.process.memory_percent} />
            </div>
          )}

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Quick Actions</h3>
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
              <ActionButton onClick={optimizeDatabase} icon={Database}>
                Optimize Database
              </ActionButton>
              <ActionButton onClick={clearLogs} icon={Trash2} variant="danger">
                Clear Logs
              </ActionButton>
              <ActionButton onClick={() => alert('Export feature coming soon!')} icon={Download} variant="secondary">
                Export Data
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'database' && (
        <div>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-lg)' }}>Database Management</h2>
          
          {databaseStats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-xl)' }}>
              <StatCard title="Total Records" value={databaseStats.database_stats.total_records?.toLocaleString() || 'N/A'} icon={Database} color="blue" />
              <StatCard title="Total Diffs" value={databaseStats.database_stats.total_diffs?.toLocaleString() || 'N/A'} icon={Activity} color="green" />
              <StatCard title="Index Size" value={databaseStats.database_stats.index_size || 'N/A'} icon={HardDrive} color="purple" />
            </div>
          )}

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Database Operations</h3>
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
              <ActionButton onClick={optimizeDatabase} icon={RefreshCw}>
                Optimize Database
              </ActionButton>
              <ActionButton onClick={() => alert('Backup feature coming soon!')} icon={Download} variant="secondary">
                Create Backup
              </ActionButton>
              <ActionButton onClick={() => alert('Restore feature coming soon!')} icon={Upload} variant="secondary">
                Restore Backup
              </ActionButton>
            </div>
          </div>

          {databaseStats && (
            <div style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--border-radius-lg)',
              padding: 'var(--spacing-lg)'
            }}>
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Database Information</h3>
              <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Last Optimized:</span>
                  <span>{databaseStats.database_stats.last_optimized || 'Never'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Total Records:</span>
                  <span>{databaseStats.database_stats.total_records?.toLocaleString() || 'N/A'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Index Size:</span>
                  <span>{databaseStats.database_stats.index_size || 'N/A'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}


      {activeTab === 'config' && (
        <div>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-lg)' }}>System Configuration</h2>
          
          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Monitoring Settings</h3>
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Auto-monitoring</span>
                <div style={{
                  width: '3rem',
                  height: '1.5rem',
                  backgroundColor: 'var(--color-primary)',
                  borderRadius: '0.75rem',
                  position: 'relative',
                  cursor: 'pointer'
                }}>
                  <div style={{
                    width: '1.25rem',
                    height: '1.25rem',
                    backgroundColor: 'white',
                    borderRadius: '50%',
                    position: 'absolute',
                    top: '0.125rem',
                    right: '0.125rem',
                    transition: 'all 0.2s ease'
                  }} />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Real-time updates</span>
                <div style={{
                  width: '3rem',
                  height: '1.5rem',
                  backgroundColor: 'var(--color-primary)',
                  borderRadius: '0.75rem',
                  position: 'relative',
                  cursor: 'pointer'
                }}>
                  <div style={{
                    width: '1.25rem',
                    height: '1.25rem',
                    backgroundColor: 'white',
                    borderRadius: '50%',
                    position: 'absolute',
                    top: '0.125rem',
                    right: '0.125rem',
                    transition: 'all 0.2s ease'
                  }} />
                </div>
              </div>
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Advanced Configuration</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-lg)' }}>
              Advanced configuration options are available through the main Settings page.
            </p>
            <ActionButton onClick={() => window.location.href = '/settings'} icon={Settings} variant="secondary">
              Go to Settings
            </ActionButton>
          </div>
        </div>
      )}
    </div>
  )
}