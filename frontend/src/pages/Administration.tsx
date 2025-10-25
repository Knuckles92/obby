import { useState, useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { AdminHeader } from '../components/admin'
import OverviewTab from './admin/OverviewTab'
import DatabaseTab from './admin/DatabaseTab'
import ConfigTab from './admin/ConfigTab'
import { apiRequest } from '../utils/api'
import type { SystemStats, DatabaseStats } from '../types/admin'

export default function Administration() {
  const [activeTab, setActiveTab] = useState('overview')
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [databaseStats, setDatabaseStats] = useState<DatabaseStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Configuration state
  const [models, setModels] = useState<Record<string, string>>({})
  const [currentModel, setCurrentModel] = useState<string>('')
  const [config, setConfig] = useState<any>(null)
  const [configLoading, setConfigLoading] = useState(true)

  const fetchSystemStats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const statsResponse = await apiRequest('/api/admin/system/stats')
      setSystemStats(statsResponse)
      
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

        const [eventsResult, diffsResult] = await Promise.allSettled([
          withTimeout('/api/data/events/clear', { method: 'POST' }, 12000),
          withTimeout('/api/data/diffs/clear', { method: 'POST' }, 15000)
        ])

        const eventsOk = eventsResult.status === 'fulfilled'
        const diffsOk = diffsResult.status === 'fulfilled'

        window.dispatchEvent(new CustomEvent('dashboard-data-cleared', { detail: { source: 'admin', ts: Date.now() } }))

        let confirmedCount: number | null = null
        try {
          const status = await withTimeout('/api/monitor/status', { method: 'GET' }, 8000)
          if (status && typeof status.eventsToday === 'number') confirmedCount = status.eventsToday
        } catch (e) {
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

  const fetchConfig = async () => {
    try {
      setConfigLoading(true)

      const configResponse = await apiRequest('/api/config/')
      setConfig(configResponse)

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
    { id: 'overview', name: 'System Overview', icon: 'Activity' },
    { id: 'database', name: 'Database', icon: 'Database' },
    { id: 'config', name: 'Configuration', icon: 'Settings' },
  ]

  return (
    <div style={{ padding: 'var(--spacing-lg)' }}>
      <AdminHeader systemOnline={!!systemStats} loading={loading} onRefresh={fetchSystemStats} />

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
              {tab.name}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'overview' && (
        <OverviewTab 
          systemStats={systemStats} 
          loading={loading} 
          onOptimizeDatabase={optimizeDatabase}
          onClearLogs={clearLogs}
          onClearDashboardData={clearDashboardData}
        />
      )}

      {activeTab === 'database' && (
        <DatabaseTab 
          databaseStats={databaseStats} 
          loading={loading} 
          onOptimizeDatabase={optimizeDatabase}
        />
      )}

      {activeTab === 'config' && (
        <ConfigTab 
          config={config} 
          configLoading={configLoading} 
          models={models}
          currentModel={currentModel}
        />
      )}
    </div>
  )
}
