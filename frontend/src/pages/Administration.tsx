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

  // Database reset state
  const [resetSliderConfirmed, setResetSliderConfirmed] = useState(false)
  const [resetConfirmationPhrase, setResetConfirmationPhrase] = useState('')
  const [resetLoading, setResetLoading] = useState(false)
  const [resetSuccess, setResetSuccess] = useState<any>(null)
  const [resetError, setResetError] = useState<string | null>(null)

  // Configuration state
  const [models, setModels] = useState<Record<string, string>>({})
  const [currentModel, setCurrentModel] = useState<string>('')
  const [config, setConfig] = useState<any>(null)
  const [configLoading, setConfigLoading] = useState(true)

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

  const clearDashboardData = async () => {
    if (confirm('Clear dashboard data? This will remove recent events and diffs displayed on the dashboard.')) {
      try {
        setLoading(true)
        // Helper to add a timeout to fetch via AbortController
        const withTimeout = async (endpoint: string, options: RequestInit = {}, timeoutMs = 10000) => {
          const controller = new AbortController()
          const id = setTimeout(() => controller.abort(), timeoutMs)
          try {
            const res = await apiRequest(endpoint, { ...options, signal: controller.signal })
            return res
          } finally {
            clearTimeout(id)
          }
        }

        // Run clears in parallel with independent timeouts to avoid a single hang blocking both
        const [eventsResult, diffsResult] = await Promise.allSettled([
          withTimeout('/api/data/events/clear', { method: 'POST' }, 12000),
          withTimeout('/api/data/diffs/clear', { method: 'POST' }, 15000)
        ])

        const eventsOk = eventsResult.status === 'fulfilled'
        const diffsOk = diffsResult.status === 'fulfilled'

        // Dispatch a global event so Dashboard can immediately refresh without waiting for polling
        window.dispatchEvent(new CustomEvent('dashboard-data-cleared', { detail: { source: 'admin', ts: Date.now() } }))

        // Optionally confirm by fetching latest status (eventsToday)
        let confirmedCount: number | null = null
        try {
          const status = await withTimeout('/api/monitor/status', { method: 'GET' }, 8000)
          if (status && typeof status.eventsToday === 'number') confirmedCount = status.eventsToday
        } catch (e) {
          // Non-fatal; status confirm is best-effort
          console.warn('Unable to confirm status after clear:', e)
        }

        const msgParts = [
          eventsOk ? 'events cleared' : 'events clear failed',
          diffsOk ? 'diffs cleared' : 'diffs clear failed'
        ]
        const suffix = confirmedCount !== null ? ` Current events today: ${confirmedCount}` : ''
        alert(`Dashboard data clear completed: ${msgParts.join(', ')}.${suffix}`)
      } catch (err) {
        setError('Failed to clear dashboard data')
        console.error('Error clearing dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
  }

  const resetDatabase = async () => {
    // Final confirmation before proceeding
    if (!resetSliderConfirmed || resetConfirmationPhrase.trim().toLowerCase() !== 'if i ruin my database it is my fault') {
      setResetError('Please complete both safety confirmations before proceeding.')
      return
    }

    try {
      setResetLoading(true)
      setResetError(null)
      setResetSuccess(null)

      const response = await apiRequest('/api/admin/database/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          confirmationPhrase: resetConfirmationPhrase.trim(),
          sliderConfirmed: resetSliderConfirmed,
          enableBackup: true
        })
      })

      if (response.success) {
        setResetSuccess(response)
        setResetSliderConfirmed(false)
        setResetConfirmationPhrase('')
        // Refresh stats after reset
        setTimeout(() => {
          fetchSystemStats()
        }, 1000)
      } else {
        setResetError(response.error || 'Database reset failed')
      }
    } catch (err: any) {
      setResetError(err.message || 'Failed to reset database')
      console.error('Error resetting database:', err)
    } finally {
      setResetLoading(false)
    }
  }

  const handleResetSliderToggle = () => {
    setResetSliderConfirmed(!resetSliderConfirmed)
    if (resetError) setResetError(null)
  }

  const handlePhraseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setResetConfirmationPhrase(e.target.value)
    if (resetError) setResetError(null)
  }

  const isResetEnabled = () => {
    return resetSliderConfirmed && 
           resetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' &&
           !resetLoading
  }

  const fetchConfig = async () => {
    try {
      setConfigLoading(true)

      // Fetch configuration
      const configResponse = await apiRequest('/api/config/')
      setConfig(configResponse)

      // Fetch models list
      const modelsResponse = await apiRequest('/api/config/models')
      if (modelsResponse && !modelsResponse.error) {
        setModels(modelsResponse.models || {})
        setCurrentModel(modelsResponse.currentModel || configResponse.aiModel || '')
      }
    } catch (err) {
      console.error('Error fetching configuration:', err)
    } finally {
      setConfigLoading(false)
    }
  }

  useEffect(() => {
    fetchSystemStats()
    fetchConfig()
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
              <ActionButton onClick={clearDashboardData} icon={Trash2} variant="danger">
                Clear Dashboard Data
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

          {/* Danger Zone Section */}
          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '2px solid var(--color-error)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)',
            marginTop: 'var(--spacing-xl)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-md)' }}>
              <AlertTriangle style={{ width: '1.5rem', height: '1.5rem', color: 'var(--color-error)' }} />
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-error)', margin: 0 }}>
                Danger Zone
              </h3>
            </div>
            
            <div style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid var(--color-error)',
              borderRadius: 'var(--border-radius-md)',
              padding: 'var(--spacing-md)',
              marginBottom: 'var(--spacing-lg)'
            }}>
              <h4 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-error)', margin: '0 0 var(--spacing-sm) 0' }}>
                Reset Database
              </h4>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', margin: '0 0 var(--spacing-md) 0' }}>
                This will permanently delete ALL data from the database including file tracking history, semantic analysis, session summaries, and all other stored information. 
                A backup will be created automatically before the reset.
              </p>

              {/* Success Message */}
              {resetSuccess && (
                <div style={{
                  backgroundColor: 'var(--color-success)',
                  color: 'white',
                  padding: 'var(--spacing-md)',
                  borderRadius: 'var(--border-radius-md)',
                  marginBottom: 'var(--spacing-md)',
                  fontSize: 'var(--font-size-sm)'
                }}>
                  <strong>Database Reset Successful!</strong>
                  <br />
                  {resetSuccess.message}
                  {resetSuccess.recovery_info?.backup_available && (
                    <>
                      <br />
                      <strong>Backup saved:</strong> {resetSuccess.recovery_info.backup_location}
                    </>
                  )}
                </div>
              )}

              {/* Error Message */}
              {resetError && (
                <div style={{
                  backgroundColor: 'var(--color-error)',
                  color: 'white',
                  padding: 'var(--spacing-md)',
                  borderRadius: 'var(--border-radius-md)',
                  marginBottom: 'var(--spacing-md)',
                  fontSize: 'var(--font-size-sm)'
                }}>
                  <strong>Error:</strong> {resetError}
                </div>
              )}

              {/* Safety Confirmation Slider */}
              <div style={{ marginBottom: 'var(--spacing-md)' }}>
                <label style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 'var(--spacing-md)', 
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-medium)'
                }}>
                  <span>I understand the risks and consequences</span>
                  <div 
                    onClick={handleResetSliderToggle}
                    style={{
                      width: '3.5rem',
                      height: '1.75rem',
                      backgroundColor: resetSliderConfirmed ? 'var(--color-error)' : 'var(--color-border)',
                      borderRadius: '0.875rem',
                      position: 'relative',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s ease'
                    }}
                  >
                    <div style={{
                      width: '1.5rem',
                      height: '1.5rem',
                      backgroundColor: 'white',
                      borderRadius: '50%',
                      position: 'absolute',
                      top: '0.125rem',
                      left: resetSliderConfirmed ? '1.875rem' : '0.125rem',
                      transition: 'left 0.2s ease',
                      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
                    }} />
                  </div>
                </label>
              </div>

              {/* Confirmation Phrase Input */}
              <div style={{ marginBottom: 'var(--spacing-lg)' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: 'var(--font-size-sm)', 
                  fontWeight: 'var(--font-weight-medium)',
                  marginBottom: 'var(--spacing-xs)'
                }}>
                  Type the following phrase to confirm: <span style={{ color: 'var(--color-error)', fontWeight: 'var(--font-weight-bold)' }}>
                    if i ruin my database it is my fault
                  </span>
                </label>
                <input
                  type="text"
                  value={resetConfirmationPhrase}
                  onChange={handlePhraseChange}
                  placeholder="Type the confirmation phrase exactly..."
                  disabled={resetLoading}
                  style={{
                    width: '100%',
                    padding: 'var(--spacing-sm)',
                    border: `1px solid ${resetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' ? 'var(--color-success)' : 'var(--color-border)'}`,
                    borderRadius: 'var(--border-radius-md)',
                    fontSize: 'var(--font-size-sm)',
                    backgroundColor: resetLoading ? 'var(--color-surface)' : 'white',
                    color: 'var(--color-text-primary)'
                  }}
                />
              </div>

              {/* Reset Button */}
              <button
                onClick={resetDatabase}
                disabled={!isResetEnabled()}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-sm)',
                  padding: 'var(--spacing-md) var(--spacing-lg)',
                  backgroundColor: isResetEnabled() ? 'var(--color-error)' : 'var(--color-border)',
                  color: isResetEnabled() ? 'white' : 'var(--color-text-secondary)',
                  border: 'none',
                  borderRadius: 'var(--border-radius-md)',
                  cursor: isResetEnabled() ? 'pointer' : 'not-allowed',
                  opacity: isResetEnabled() ? 1 : 0.6,
                  transition: 'all 0.2s ease',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-semibold)'
                }}
              >
                <Trash2 style={{ width: '1rem', height: '1rem' }} />
                {resetLoading ? 'Resetting Database...' : 'Reset Database'}
              </button>
            </div>
          </div>
        </div>
      )}


      {activeTab === 'config' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>System Configuration</h2>
          </div>

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>Monitoring Settings</h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: '1.5' }}>
              These settings control how Obby monitors your files and detects changes in real-time.
            </p>
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--spacing-sm) 0' }}>
                <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Auto-monitoring</span>
                {configLoading ? (
                  <div style={{
                    width: '1rem',
                    height: '1rem',
                    border: '2px solid var(--color-border)',
                    borderTopColor: 'var(--color-primary)',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }} />
                ) : (
                  <div style={{
                    width: '3rem',
                    height: '1.5rem',
                    backgroundColor: config?.periodicCheckEnabled ? 'var(--color-primary)' : 'var(--color-border)',
                    borderRadius: '0.75rem',
                    position: 'relative'
                  }}>
                    <div style={{
                      width: '1.25rem',
                      height: '1.25rem',
                      backgroundColor: 'white',
                      borderRadius: '50%',
                      position: 'absolute',
                      top: '0.125rem',
                      right: config?.periodicCheckEnabled ? '0.125rem' : 'auto',
                      left: config?.periodicCheckEnabled ? 'auto' : '0.125rem',
                      transition: 'all 0.2s ease'
                    }} />
                  </div>
                )}
              </div>
              <div style={{
                paddingLeft: 'var(--spacing-md)',
                paddingBottom: 'var(--spacing-sm)',
                borderBottom: '1px solid var(--color-border)'
              }}>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                  lineHeight: '1.5'
                }}>
                  When enabled, Obby automatically starts monitoring files in directories specified in <code style={{
                    backgroundColor: 'var(--color-border)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>.obbywatch</code>. Uses watchdog library for real-time file change detection with zero latency. Excludes patterns from <code style={{
                    backgroundColor: 'var(--color-border)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>.obbyignore</code>. Recommended: Keep enabled for active development.
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--spacing-sm) 0' }}>
                <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Real-time updates</span>
                {configLoading ? (
                  <div style={{
                    width: '1rem',
                    height: '1rem',
                    border: '2px solid var(--color-border)',
                    borderTopColor: 'var(--color-primary)',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }} />
                ) : (
                  <div style={{
                    width: '3rem',
                    height: '1.5rem',
                    backgroundColor: 'var(--color-primary)',
                    borderRadius: '0.75rem',
                    position: 'relative'
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
                )}
              </div>
              <div style={{
                paddingLeft: 'var(--spacing-md)',
                paddingBottom: 'var(--spacing-sm)'
              }}>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                  lineHeight: '1.5'
                }}>
                  Enables Server-Sent Events (SSE) to push updates to the frontend instantly at <code style={{
                    backgroundColor: 'var(--color-border)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>/api/session-summary/events</code> and <code style={{
                    backgroundColor: 'var(--color-border)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>/api/summary-notes/events</code>. When disabled, the dashboard will only refresh on page reload. Essential for collaborative environments.
                </p>
              </div>
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>File Tracking</h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: '1.5' }}>
              Configuration for how Obby tracks file changes, generates diffs, and manages file versions.
            </p>
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
              <div style={{
                padding: 'var(--spacing-md)',
                backgroundColor: 'rgba(var(--color-primary-rgb), 0.05)',
                borderRadius: 'var(--border-radius-md)',
                border: '1px solid var(--color-border)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
                  <Database style={{ width: '1rem', height: '1rem', color: 'var(--color-primary)' }} />
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Content Hashing</span>
                </div>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                  lineHeight: '1.5'
                }}>
                  Uses SHA-256 hashing to detect actual content changes rather than relying solely on modification timestamps. Prevents false positives from tools that touch files without changing content. Implemented via <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>FileContentTracker</code> in <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>core/file_tracker.py</code>.
                </p>
              </div>

              <div style={{
                padding: 'var(--spacing-md)',
                backgroundColor: 'rgba(var(--color-primary-rgb), 0.05)',
                borderRadius: 'var(--border-radius-md)',
                border: '1px solid var(--color-border)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
                  <Activity style={{ width: '1rem', height: '1rem', color: 'var(--color-primary)' }} />
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Diff Generation</span>
                </div>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                  lineHeight: '1.5'
                }}>
                  Creates native unified diffs showing line-by-line changes between file versions. Pure file-system based diff generation without git dependencies. Stored in <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>ContentDiffModel</code> table with FTS5 search indexing for fast retrieval.
                </p>
              </div>

              <div style={{
                padding: 'var(--spacing-md)',
                backgroundColor: 'rgba(var(--color-primary-rgb), 0.05)',
                borderRadius: 'var(--border-radius-md)',
                border: '1px solid var(--color-border)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
                  <HardDrive style={{ width: '1rem', height: '1rem', color: 'var(--color-primary)' }} />
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Version History</span>
                </div>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                  lineHeight: '1.5'
                }}>
                  Maintains complete version history for every tracked file. Each version includes content hash, timestamp, and full diff. Enables time-travel queries and comprehensive change analysis. Stored via <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>FileVersionModel</code> with connection pooling for thread-safe access.
                </p>
              </div>
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>AI Processing</h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: '1.5' }}>
              Settings for OpenAI integration, including batch processing and semantic analysis.
            </p>
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
              <div style={{
                padding: 'var(--spacing-md)',
                backgroundColor: 'rgba(59, 130, 246, 0.05)',
                borderRadius: 'var(--border-radius-md)',
                border: '1px solid rgba(59, 130, 246, 0.2)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
                  <Cpu style={{ width: '1rem', height: '1rem', color: 'rgb(59, 130, 246)' }} />
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Batch Processing</span>
                </div>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: '0 0 var(--spacing-sm) 0',
                  lineHeight: '1.5'
                }}>
                  Groups multiple file changes together for efficient AI analysis. Reduces API costs and improves performance by processing changes in scheduled batches rather than one-by-one. Managed by <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>ai/batch_processor.py</code>. Configure batch size and interval in <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>config.json</code> via Settings page.
                </p>
                {configLoading ? (
                  <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--spacing-sm)' }}>
                    <div style={{
                      width: '1rem',
                      height: '1rem',
                      border: '2px solid var(--color-border)',
                      borderTopColor: 'var(--color-primary)',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite'
                    }} />
                  </div>
                ) : (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 'var(--spacing-sm)',
                    marginTop: 'var(--spacing-sm)'
                  }}>
                    <div style={{ fontSize: 'var(--font-size-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>AI Update Interval:</span>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', marginLeft: 'var(--spacing-xs)' }}>
                        {config?.aiUpdateInterval || 12} hours
                      </span>
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Auto Updates:</span>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', marginLeft: 'var(--spacing-xs)' }}>
                        {config?.aiAutoUpdateEnabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div style={{
                padding: 'var(--spacing-md)',
                backgroundColor: 'rgba(59, 130, 246, 0.05)',
                borderRadius: 'var(--border-radius-md)',
                border: '1px solid rgba(59, 130, 246, 0.2)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
                  <Activity style={{ width: '1rem', height: '1rem', color: 'rgb(59, 130, 246)' }} />
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Semantic Analysis</span>
                </div>
                <p style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  margin: '0 0 var(--spacing-sm) 0',
                  lineHeight: '1.5'
                }}>
                  Extracts topics, keywords, and impact levels from file changes using OpenAI models. Enables powerful search and filtering by semantic content. Requires OPENAI_API_KEY environment variable. Results stored in <code style={{
                    backgroundColor: 'var(--color-surface)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: 'var(--font-size-xs)'
                  }}>SemanticModel</code> with FTS5 indexing for fast semantic search.
                </p>
                {configLoading ? (
                  <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--spacing-sm)' }}>
                    <div style={{
                      width: '1rem',
                      height: '1rem',
                      border: '2px solid var(--color-border)',
                      borderTopColor: 'var(--color-primary)',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite'
                    }} />
                  </div>
                ) : (
                  <div>
                    <div style={{
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--color-text-secondary)',
                      marginBottom: 'var(--spacing-xs)'
                    }}>
                      Current Model: <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                        {currentModel || config?.aiModel || 'Not configured'}
                      </span>
                    </div>
                    {Object.keys(models).length > 0 && (
                      <div style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-text-secondary)'
                      }}>
                        Available Models: <span style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>
                          {Object.keys(models).join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--border-radius-lg)',
            padding: 'var(--spacing-lg)'
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>Advanced Configuration</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-lg)', fontSize: 'var(--font-size-sm)', lineHeight: '1.6' }}>
              Fine-tune monitoring behavior, configure AI processing models, manage watch directories, and set output paths.
              These settings are stored in <code style={{
                backgroundColor: 'var(--color-border)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>config.json</code> and <code style={{
                backgroundColor: 'var(--color-border)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>config/settings.py</code>.
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