import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Save, Trash2, Palette, FolderOpen, Plus, RefreshCw, FileText, Eye, EyeOff, Monitor, Database, Cpu, HardDrive, Activity, AlertTriangle, Download, Upload, MemoryStick } from 'lucide-react'
import { ConfigSettings, ModelsResponse, WatchPatternsResponse, IgnorePatternsResponse, WatchConfigResponse } from '../types'
import { apiRequest, apiFetch } from '../utils/api'
import { ThemeSwitcher } from '../components/ui'
import StatCard from '../components/admin/StatCard'
import ActionButton from '../components/admin/ActionButton'
import { AgentLogsViewer } from '../components/admin/AgentLogsViewer'
import type { SystemStats, DatabaseStats } from '../types/admin'

export default function Settings() {
  const [config, setConfig] = useState<ConfigSettings>({
    aiModel: 'haiku',
    ignorePatterns: [],
    monitoringDirectory: 'notes'
  })
  const [models, setModels] = useState<Record<string, string>>({})
  const [modelsLoading, setModelsLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newIgnorePattern, setNewIgnorePattern] = useState('')

  // Watch configuration state
  const [watchPatterns, setWatchPatterns] = useState<string[]>([])
  const [ignorePatterns, setIgnorePatterns] = useState<string[]>([])
  const [newWatchPattern, setNewWatchPattern] = useState('')
  const [watchConfigLoading, setWatchConfigLoading] = useState(true)
  const [showWatchHelp, setShowWatchHelp] = useState(false)
  const [showIgnoreHelp, setShowIgnoreHelp] = useState(false)

  // Tab management
  const [activeTab, setActiveTab] = useState('general')

  // Admin functionality state
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [databaseStats, setDatabaseStats] = useState<DatabaseStats | null>(null)
  const [adminLoading, setAdminLoading] = useState(false)
  const [dbResetSliderConfirmed, setDbResetSliderConfirmed] = useState(false)
  const [dbResetConfirmationPhrase, setDbResetConfirmationPhrase] = useState('')
  const [dbResetLoading, setDbResetLoading] = useState(false)
  const [dbResetSuccess, setDbResetSuccess] = useState<any>(null)
  const [dbResetError, setDbResetError] = useState<string | null>(null)


  const tabs = [
    { id: 'general', label: 'General', icon: SettingsIcon },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'watch-ignore', label: 'Watch & Ignore', icon: FolderOpen },
    { id: 'system-overview', label: 'System Overview', icon: Monitor },
    { id: 'database', label: 'Database', icon: Database },
    { id: 'system-config', label: 'System Configuration', icon: Cpu },
    { id: 'agent-activity', label: 'Agent Activity', icon: Activity }
  ]

  useEffect(() => {
    fetchConfig()
    fetchModels()
    fetchWatchConfig()
    fetchAdminData()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await apiFetch('/api/config/')
      const data = await response.json()
      setConfig({
        aiModel: data.aiModel || 'haiku',
        ignorePatterns: data.ignorePatterns || [],
        monitoringDirectory: data.monitoringDirectory || 'notes'
      })
    } catch (error) {
      console.error('Error fetching config:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchModels = async () => {
    try {
      // Fetch dynamic models from backend (redirect-safe path)
      const response = await apiFetch('/api/config/models')
      const data: ModelsResponse = await response.json()
      
      if (data.error) {
        console.error('Error from models API:', data.error)
        // Fallback to default models if API fails
        setModels({
          haiku: 'haiku',
          sonnet: 'sonnet',
          opus: 'opus'
        })
      } else {
        setModels(data.models)
        // If current config model is missing, prefer backend's current/default
        const availableModelIds = new Set(Object.values(data.models))
        if (!availableModelIds.has(config.aiModel)) {
          const preferred = data.currentModel || data.defaultModel
          if (preferred) {
            setConfig((prev) => ({ ...prev, aiModel: preferred }))
          }
        }
      }
    } catch (error) {
      console.error('Error fetching models:', error)
      // Fallback to default models if fetch fails
      setModels({
        haiku: 'haiku',
        sonnet: 'sonnet',
        opus: 'opus'
      })
    } finally {
      setModelsLoading(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    try {
      const response = await apiFetch('/api/config/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      
      if (response.ok) {
        alert('Configuration saved successfully!')
      } else {
        alert('Failed to save configuration')
      }
    } catch (error) {
      console.error('Error saving config:', error)
      alert('Error saving configuration')
    } finally {
      setSaving(false)
    }
  }

  const fetchWatchConfig = async () => {
    try {
      const [watchResponse, ignoreResponse] = await Promise.all([
        apiFetch('/api/watch-config/watch-patterns'),
        apiFetch('/api/watch-config/ignore-patterns')
      ])
      
      const watchData: WatchPatternsResponse = await watchResponse.json()
      const ignoreData: IgnorePatternsResponse = await ignoreResponse.json()
      
      if (watchData.success) {
        setWatchPatterns(watchData.patterns)
      }
      
      if (ignoreData.success) {
        setIgnorePatterns(ignoreData.patterns)
      }
    } catch (error) {
      console.error('Error fetching watch config:', error)
    } finally {
      setWatchConfigLoading(false)
    }
  }

  const addWatchPattern = async () => {
    if (!newWatchPattern.trim()) return
    
    try {
      const response = await apiFetch('/api/watch-config/watch-patterns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern: newWatchPattern.trim() })
      })
      
      const data: WatchConfigResponse = await response.json()
      
      if (data.success) {
        setWatchPatterns(data.patterns)
        setNewWatchPattern('')
        alert(data.message)
      } else {
        alert(`Failed to add pattern: ${data.message}`)
      }
    } catch (error) {
      console.error('Error adding watch pattern:', error)
      alert('Error adding watch pattern')
    }
  }

  const removeWatchPattern = async (pattern: string) => {
    try {
      const response = await apiFetch('/api/watch-config/watch-patterns', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern })
      })
      
      const data: WatchConfigResponse = await response.json()
      
      if (data.success) {
        setWatchPatterns(data.patterns)
        alert(data.message)
      } else {
        alert(`Failed to remove pattern: ${data.message}`)
      }
    } catch (error) {
      console.error('Error removing watch pattern:', error)
      alert('Error removing watch pattern')
    }
  }

  const addIgnorePatternAPI = async () => {
    if (!newIgnorePattern.trim()) return
    
    try {
      const response = await apiFetch('/api/watch-config/ignore-patterns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern: newIgnorePattern.trim() })
      })
      
      const data: WatchConfigResponse = await response.json()
      
      if (data.success) {
        setIgnorePatterns(data.patterns)
        setNewIgnorePattern('')
        alert(data.message)
      } else {
        alert(`Failed to add pattern: ${data.message}`)
      }
    } catch (error) {
      console.error('Error adding ignore pattern:', error)
      alert('Error adding ignore pattern')
    }
  }

  const removeIgnorePatternAPI = async (pattern: string) => {
    try {
      const response = await apiFetch('/api/watch-config/ignore-patterns', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern })
      })
      
      const data: WatchConfigResponse = await response.json()
      
      if (data.success) {
        setIgnorePatterns(data.patterns)
        alert(data.message)
      } else {
        alert(`Failed to remove pattern: ${data.message}`)
      }
    } catch (error) {
      console.error('Error removing ignore pattern:', error)
      alert('Error removing ignore pattern')
    }
  }

  const reloadWatchConfig = async () => {
    try {
      const response = await apiFetch('/api/watch-config/reload', {
        method: 'POST'
      })

      const data = await response.json()

      if (data.success) {
        setWatchPatterns(data.watchPatterns)
        setIgnorePatterns(data.ignorePatterns)
        alert('Watch configuration reloaded successfully!')
      } else {
        alert('Failed to reload watch configuration')
      }
    } catch (error) {
      console.error('Error reloading watch config:', error)
      alert('Error reloading watch configuration')
    }
  }

  const fetchAdminData = async () => {
    try {
      const [systemResponse, databaseResponse] = await Promise.all([
        apiRequest('/api/admin/system/stats'),
        apiRequest('/api/admin/database/stats')
      ])

      if (systemResponse.success) {
        setSystemStats(systemResponse)
      }

      if (databaseResponse.success) {
        setDatabaseStats(databaseResponse)
      }
    } catch (error) {
      console.error('Error fetching admin data:', error)
    }
  }


  const optimizeDatabase = async () => {
    setAdminLoading(true)
    try {
      const response = await apiRequest('/api/admin/database/optimize', {
        method: 'POST'
      })

      if (response.success) {
        alert('Database optimized successfully!')
        fetchAdminData()
      } else {
        alert('Failed to optimize database')
      }
    } catch (error) {
      console.error('Error optimizing database:', error)
      alert('Error optimizing database')
    } finally {
      setAdminLoading(false)
    }
  }

  const clearLogs = async () => {
    setAdminLoading(true)
    try {
      const response = await apiRequest('/api/admin/clear-logs', {
        method: 'POST'
      })

      if (response.success) {
        alert('Logs cleared successfully!')
      } else {
        alert('Failed to clear logs')
      }
    } catch (error) {
      console.error('Error clearing logs:', error)
      alert('Error clearing logs')
    } finally {
      setAdminLoading(false)
    }
  }

  const clearDashboardData = async () => {
    setAdminLoading(true)
    try {
      const response = await apiRequest('/api/admin/clear-dashboard-data', {
        method: 'POST'
      })

      if (response.success) {
        alert('Dashboard data cleared successfully!')
      } else {
        alert('Failed to clear dashboard data')
      }
    } catch (error) {
      console.error('Error clearing dashboard data:', error)
      alert('Error clearing dashboard data')
    } finally {
      setAdminLoading(false)
    }
  }

  const resetDatabase = async () => {
    if (!dbResetSliderConfirmed || dbResetConfirmationPhrase.trim().toLowerCase() !== 'if i ruin my database it is my fault') {
      setDbResetError('Please complete both safety confirmations before proceeding.')
      return
    }

    try {
      setDbResetLoading(true)
      setDbResetError(null)
      setDbResetSuccess(null)

      const response = await apiRequest('/api/admin/database/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          confirmationPhrase: dbResetConfirmationPhrase.trim(),
          sliderConfirmed: dbResetSliderConfirmed,
          enableBackup: true
        })
      })

      if (response.success) {
        setDbResetSuccess(response)
        setDbResetSliderConfirmed(false)
        setDbResetConfirmationPhrase('')
        fetchAdminData()
      } else {
        setDbResetError(response.error || 'Database reset failed')
      }
    } catch (err: any) {
      setDbResetError(err.message || 'Failed to reset database')
      console.error('Error resetting database:', err)
    } finally {
      setDbResetLoading(false)
    }
  }




  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return (
          <div className="space-y-6">
            <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border transition-all duration-300 hover:shadow-xl hover:-translate-y-1" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <h3 className="text-lg font-medium mb-4" style={{ color: 'var(--color-text-primary)' }}>General Settings</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                    <FolderOpen className="h-4 w-4 inline mr-2" />
                    Monitoring Directory
                  </label>
                  <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                    The base directory that Obby monitors for changes. All generated summaries will be saved to the output/ directory.
                  </p>
                  <input
                    type="text"
                    value={config.monitoringDirectory || 'notes'}
                    onChange={(e) => setConfig({ ...config, monitoringDirectory: e.target.value })}
                    placeholder="notes"
                    className="w-full px-3 py-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: 'var(--color-background)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid'
                    }}
                  />
                  <p className="text-sm mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    ⚠️ Cannot be set to 'output' to prevent feedback loops
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                    AI Model
                  </label>
                  <p className="text-sm mb-3" style={{ color: 'var(--color-text-secondary)' }}>
                    <strong>Claude model used for:</strong> Session summaries, semantic analysis, and other AI-assisted features.
                  </p>
                  <select
                    value={config.aiModel}
                    onChange={(e) => setConfig({ ...config, aiModel: e.target.value })}
                    disabled={modelsLoading}
                    className="w-full px-3 py-2 rounded-md disabled:opacity-50 transition-colors"
                    style={{
                      backgroundColor: 'var(--color-background)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid'
                    }}
                  >
                    {modelsLoading ? (
                      <option value="">Loading models...</option>
                    ) : (
                      Object.entries(models).map(([key, value]) => {
                        const displayName = key.charAt(0).toUpperCase() + key.slice(1)
                        return (
                          <option key={key} value={value}>
                            {`Claude ${displayName}`}
                          </option>
                        )
                      })
                    )}
                  </select>
                  {modelsLoading && (
                    <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Fetching latest models...</p>
                  )}
                </div>

                <div className="rounded-xl p-4" style={{
                  backgroundColor: 'var(--color-info-bg, #dbeafe)',
                  border: '1px solid var(--color-info-border, #93c5fd)'
                }}>
                  <h4 className="text-sm font-medium mb-2" style={{ color: 'var(--color-info-text, #1e40af)' }}>🤖 Claude for Interactive Chat</h4>
                  <p className="text-sm mb-2" style={{ color: 'var(--color-info-text, #1e40af)' }}>
                    <strong>Claude (Anthropic) is used for:</strong> Interactive conversations, tool-based chat, file operations, and shell commands.
                  </p>
                  <p className="text-sm" style={{ color: 'var(--color-info-text, #2563eb)' }}>
                    Claude provides powerful built-in tools for reading files, executing commands, and exploring your codebase interactively.
                    Set <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-info-bg-light, #bfdbfe)' }}>ANTHROPIC_API_KEY</code> environment variable to enable Claude chat features.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      case 'appearance':
        return (
          <div className="group relative rounded-2xl p-6 shadow-lg border transition-all duration-300 hover:shadow-xl hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
            overflow: 'visible'
          }}>
            <div className="flex items-center mb-4">
              <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-primary)' }}>
                <Palette className="h-5 w-5" style={{ color: 'var(--color-text-inverse)' }} />
              </div>
              <h3 className="text-lg font-medium ml-3" style={{ color: 'var(--color-text-primary)' }}>Theme & Appearance</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                  Current Theme
                </label>
                <ThemeSwitcher />
              </div>

              <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                <p>Choose from 11 beautiful themes across different categories:</p>
                <ul className="mt-2 space-y-1 ml-4">
                  <li>• <strong>Professional:</strong> Corporate, Minimal, Classic</li>
                  <li>• <strong>Creative:</strong> Cyberpunk, Forest, Ocean</li>
                  <li>• <strong>Accessible:</strong> High Contrast, Large Text</li>
                  <li>• <strong>Special:</strong> Vintage, Neon, Winter</li>
                </ul>
              </div>
            </div>
          </div>
        )

      case 'watch-ignore':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Watch Configuration */}
            <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border transition-all duration-300 hover:shadow-xl hover:-translate-y-1" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-success)' }}>
                    <FolderOpen className="h-5 w-5" style={{ color: 'var(--color-text-inverse)' }} />
                  </div>
                  <h3 className="text-lg font-medium ml-3" style={{ color: 'var(--color-text-primary)' }}>Watch Directories</h3>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setShowWatchHelp(!showWatchHelp)}
                    className="p-2 rounded-lg transition-colors"
                    style={{
                      color: 'var(--color-text-secondary)',
                      backgroundColor: showWatchHelp ? 'var(--color-surface)' : 'transparent'
                    }}
                    title="Show help"
                  >
                    {showWatchHelp ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={reloadWatchConfig}
                    className="p-2 rounded-lg transition-colors"
                    style={{ color: 'var(--color-text-secondary)' }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-surface)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    title="Reload configuration"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {showWatchHelp && (
                <div className="rounded-xl p-4 mb-4" style={{
                  backgroundColor: 'var(--color-info-bg, #dbeafe)',
                  border: '1px solid var(--color-info-border, #93c5fd)'
                }}>
                  <h4 className="text-sm font-medium mb-2" style={{ color: 'var(--color-info-text, #1e40af)' }}>Watch Pattern Examples:</h4>
                  <ul className="text-sm space-y-1" style={{ color: 'var(--color-info-text, #1e40af)' }}>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-info-bg-light, #bfdbfe)' }}>notes/</code> - Monitor entire notes directory</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-info-bg-light, #bfdbfe)' }}>*.md</code> - Monitor all markdown files</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-info-bg-light, #bfdbfe)' }}>docs/</code> - Monitor docs directory</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-info-bg-light, #bfdbfe)' }}>project_notes/</code> - Monitor specific subdirectory</li>
                  </ul>
                  <p className="text-sm mt-2" style={{ color: 'var(--color-info-text, #2563eb)' }}>
                    Patterns are saved to <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-info-bg-light, #bfdbfe)' }}>.obbywatch</code> file in project root.
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newWatchPattern}
                    onChange={(e) => setNewWatchPattern(e.target.value)}
                    placeholder="Enter watch pattern (e.g., notes/, *.md, docs/)"
                    className="flex-1 px-3 py-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: 'var(--color-background)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid'
                    }}
                    onKeyPress={(e) => e.key === 'Enter' && addWatchPattern()}
                  />
                  <button
                    onClick={addWatchPattern}
                    className="px-4 py-2 text-white rounded-xl transition-all duration-200 flex items-center"
                    style={{ backgroundColor: 'var(--color-success)' }}
                    onMouseEnter={(e) => e.currentTarget.style.filter = 'brightness(1.1)'}
                    onMouseLeave={(e) => e.currentTarget.style.filter = 'brightness(1)'}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </button>
                </div>

                {watchConfigLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-2">
                    {watchPatterns.map((pattern, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-md">
                        <div className="flex items-center">
                          <FolderOpen className="h-4 w-4 text-green-600 mr-2" />
                          <span className="text-sm text-gray-700 font-mono">{pattern}</span>
                        </div>
                        <button
                          onClick={() => removeWatchPattern(pattern)}
                          className="p-1 text-red-600 hover:bg-red-100 rounded"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {!watchConfigLoading && watchPatterns.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No watch patterns configured</p>
                )}
              </div>
            </div>

            {/* Ignore Patterns */}
            <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border transition-all duration-300 hover:shadow-xl hover:-translate-y-1" style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-warning)' }}>
                    <FileText className="h-5 w-5" style={{ color: 'var(--color-text-inverse)' }} />
                  </div>
                  <h3 className="text-lg font-medium ml-3" style={{ color: 'var(--color-text-primary)' }}>Ignore Patterns</h3>
                </div>
                <button
                  onClick={() => setShowIgnoreHelp(!showIgnoreHelp)}
                  className="p-2 rounded-lg transition-colors"
                  style={{
                    color: 'var(--color-text-secondary)',
                    backgroundColor: showIgnoreHelp ? 'var(--color-surface)' : 'transparent'
                  }}
                  title="Show help"
                >
                  {showIgnoreHelp ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {showIgnoreHelp && (
                <div className="rounded-xl p-4 mb-4" style={{
                  backgroundColor: 'var(--color-warning-bg, #fef3c7)',
                  border: '1px solid var(--color-warning-border, #f59e0b)'
                }}>
                  <h4 className="text-sm font-medium mb-2" style={{ color: 'var(--color-warning-text, #92400e)' }}>Ignore Pattern Examples:</h4>
                  <ul className="text-sm space-y-1" style={{ color: 'var(--color-warning-text, #92400e)' }}>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-warning-bg-light, #fde68a)' }}>*.tmp</code> - Ignore temporary files</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-warning-bg-light, #fde68a)' }}>.git/</code> - Ignore git directory</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-warning-bg-light, #fde68a)' }}>node_modules/</code> - Ignore node modules</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-warning-bg-light, #fde68a)' }}>session_summary.md</code> - Ignore specific file</li>
                    <li>• <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-warning-bg-light, #fde68a)' }}>*.swp</code> - Ignore editor swap files</li>
                  </ul>
                  <p className="text-sm mt-2" style={{ color: 'var(--color-warning-text, #b45309)' }}>
                    Patterns are saved to <code className="px-1 rounded" style={{ backgroundColor: 'var(--color-warning-bg-light, #fde68a)' }}>.obbyignore</code> file in project root.
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newIgnorePattern}
                    onChange={(e) => setNewIgnorePattern(e.target.value)}
                    placeholder="Enter ignore pattern (e.g., *.tmp, .git/, node_modules/)"
                    className="flex-1 px-3 py-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: 'var(--color-background)',
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                      border: '1px solid'
                    }}
                    onKeyPress={(e) => e.key === 'Enter' && addIgnorePatternAPI()}
                  />
                  <button
                    onClick={addIgnorePatternAPI}
                    className="px-4 py-2 text-white rounded-xl transition-all duration-200 flex items-center"
                    style={{ backgroundColor: 'var(--color-warning)' }}
                    onMouseEnter={(e) => e.currentTarget.style.filter = 'brightness(1.1)'}
                    onMouseLeave={(e) => e.currentTarget.style.filter = 'brightness(1)'}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </button>
                </div>

                {watchConfigLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-2">
                    {ignorePatterns.map((pattern, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-md">
                        <div className="flex items-center">
                          <FileText className="h-4 w-4 text-red-600 mr-2" />
                          <span className="text-sm text-gray-700 font-mono">{pattern}</span>
                        </div>
                        <button
                          onClick={() => removeIgnorePatternAPI(pattern)}
                          className="p-1 text-red-600 hover:bg-red-100 rounded"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {!watchConfigLoading && ignorePatterns.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No ignore patterns configured</p>
                )}
              </div>
            </div>
          </div>
        )

      case 'system-overview':
        return (
          <div>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0, marginBottom: 'var(--spacing-lg)' }}>System Overview</h2>

            {systemStats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-xl)' }}>
                <StatCard title="CPU Cores" value={systemStats.stats.system.cpu_count} icon={Activity} color="success" />
                <StatCard title="Memory Usage" value={`${Math.round(systemStats.stats.system.memory_percent)}%`} icon={MemoryStick} color="info" percentage={systemStats.stats.system.memory_percent} />
                <StatCard title="CPU Usage" value={`${Math.round(systemStats.stats.system.cpu_percent)}%`} icon={Cpu} color="warning" percentage={systemStats.stats.system.cpu_percent} />
                <StatCard title="Disk Usage" value={`${Math.round(systemStats.stats.system.disk_percent)}%`} icon={HardDrive} color="primary" percentage={systemStats.stats.system.disk_percent} />
                <StatCard title="Process PID" value={systemStats.stats.process.pid} icon={Activity} color="success" />
                <StatCard title="Process Memory" value={`${Math.round(systemStats.stats.process.memory_percent)}%`} icon={Database} color="info" percentage={systemStats.stats.process.memory_percent} />
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
                <ActionButton onClick={optimizeDatabase} icon={Database} busy={adminLoading}>
                  Optimize Database
                </ActionButton>
                <ActionButton onClick={clearLogs} icon={Trash2} variant="danger" busy={adminLoading}>
                  Clear Logs
                </ActionButton>
                <ActionButton onClick={clearDashboardData} icon={Trash2} variant="danger" busy={adminLoading}>
                  Clear Dashboard Data
                </ActionButton>
              </div>
            </div>
          </div>
        )

      case 'database':
        return (
          <div>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-lg)' }}>Database Management</h2>

            {databaseStats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-xl)' }}>
                <StatCard title="Total Records" value={databaseStats.database_stats.total_records?.toLocaleString() || 'N/A'} icon={Database} color="info" />
                <StatCard title="Total Diffs" value={databaseStats.database_stats.total_diffs?.toLocaleString() || 'N/A'} icon={Activity} color="success" />
                <StatCard title="Index Size" value={databaseStats.database_stats.index_size || 'N/A'} icon={HardDrive} color="primary" />
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
                <ActionButton onClick={optimizeDatabase} icon={RefreshCw} busy={adminLoading}>
                  Optimize Database
                </ActionButton>
                <ActionButton onClick={() => alert('Backup feature coming soon!')} icon={Download} variant="secondary" busy={adminLoading}>
                  Create Backup
                </ActionButton>
                <ActionButton onClick={() => alert('Restore feature coming soon!')} icon={Upload} variant="secondary" busy={adminLoading}>
                  Restore Backup
                </ActionButton>
              </div>
            </div>

            {databaseStats && (
              <div style={{
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--border-radius-lg)',
                padding: 'var(--spacing-lg)',
                marginBottom: 'var(--spacing-lg)'
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

                {dbResetSuccess && (
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
                    {dbResetSuccess.message}
                    {dbResetSuccess.recovery_info?.backup_available && (
                      <>
                        <br />
                        <strong>Backup saved:</strong> {dbResetSuccess.recovery_info.backup_location}
                      </>
                    )}
                  </div>
                )}

                {dbResetError && (
                  <div style={{
                    backgroundColor: 'var(--color-error)',
                    color: 'white',
                    padding: 'var(--spacing-md)',
                    borderRadius: 'var(--border-radius-md)',
                    marginBottom: 'var(--spacing-md)',
                    fontSize: 'var(--font-size-sm)'
                  }}>
                    <strong>Error:</strong> {dbResetError}
                  </div>
                )}

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
                      onClick={() => setDbResetSliderConfirmed(!dbResetSliderConfirmed)}
                      style={{
                        width: '3.5rem',
                        height: '1.75rem',
                        backgroundColor: dbResetSliderConfirmed ? 'var(--color-error)' : 'var(--color-border)',
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
                        left: dbResetSliderConfirmed ? '1.875rem' : '0.125rem',
                        transition: 'left 0.2s ease',
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
                      }} />
                    </div>
                  </label>
                </div>

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
                    value={dbResetConfirmationPhrase}
                    onChange={(e) => setDbResetConfirmationPhrase(e.target.value)}
                    placeholder="Type the confirmation phrase exactly..."
                    disabled={dbResetLoading}
                    style={{
                      width: '100%',
                      padding: 'var(--spacing-sm)',
                      border: `1px solid ${dbResetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' ? 'var(--color-success)' : 'var(--color-border)'}`,
                      borderRadius: 'var(--border-radius-md)',
                      fontSize: 'var(--font-size-sm)',
                      backgroundColor: dbResetLoading ? 'var(--color-surface)' : 'white',
                      color: 'var(--color-text-primary)'
                    }}
                  />
                </div>

                <button
                  onClick={resetDatabase}
                  disabled={!dbResetSliderConfirmed || dbResetConfirmationPhrase.trim().toLowerCase() !== 'if i ruin my database it is my fault' || dbResetLoading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-sm)',
                    padding: 'var(--spacing-md) var(--spacing-lg)',
                    backgroundColor: dbResetSliderConfirmed && dbResetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' && !dbResetLoading ? 'var(--color-error)' : 'var(--color-border)',
                    color: dbResetSliderConfirmed && dbResetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' && !dbResetLoading ? 'white' : 'var(--color-text-secondary)',
                    border: 'none',
                    borderRadius: 'var(--border-radius-md)',
                    cursor: dbResetSliderConfirmed && dbResetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' && !dbResetLoading ? 'pointer' : 'not-allowed',
                    opacity: dbResetSliderConfirmed && dbResetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' && !dbResetLoading ? 1 : 0.6,
                    transition: 'all 0.2s ease',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-semibold)'
                  }}
                >
                  <Trash2 style={{ width: '1rem', height: '1rem' }} />
                  {dbResetLoading ? 'Resetting Database...' : 'Reset Database'}
                </button>
              </div>
            </div>
          </div>
        )

      case 'system-config':
        return (
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
                  <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Real-time updates</span>
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
                Real-time AI processing using Claude Agent SDK for intelligent summaries and semantic analysis.
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
                    <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Session Summaries</span>
                  </div>
                  <p style={{
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--font-size-sm)',
                    margin: '0 0 var(--spacing-sm) 0',
                    lineHeight: '1.5'
                  }}>
                    Generates rolling project summaries using the Claude Agent SDK. Changes are aggregated and summarized on a schedule to keep the session overview up to date. Configure cadence and automation in the Settings page. Requires <code style={{
                      backgroundColor: 'var(--color-surface)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: 'var(--font-size-xs)'
                    }}>ANTHROPIC_API_KEY</code> in the environment.
                  </p>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 'var(--spacing-sm)',
                    marginTop: 'var(--spacing-sm)'
                  }}>
                    <div style={{ fontSize: 'var(--font-size-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Processing:</span>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', marginLeft: 'var(--spacing-xs)' }}>
                        Real-time (30s debounce)
                      </span>
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Status:</span>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', marginLeft: 'var(--spacing-xs)' }}>
                        {config.aiModel ? 'Active' : 'Not configured'}
                      </span>
                    </div>
                  </div>
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
                    Extracts topics, keywords, and impact levels from file changes using Claude models. Enables powerful search and filtering by semantic content. Results are stored in <code style={{
                      backgroundColor: 'var(--color-surface)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: 'var(--font-size-xs)'
                    }}>SemanticModel</code> with FTS5 indexing for fast semantic search.
                  </p>
                  <div>
                    <div style={{
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--color-text-secondary)',
                      marginBottom: 'var(--spacing-xs)'
                    }}>
                      Current Model: <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                        {config.aiModel || 'Not configured'}
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
                </div>
              </div>
            </div>

          </div>
        )

      case 'agent-activity':
        return (
          <div>
            <AgentLogsViewer />
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen space-y-6">
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
                <SettingsIcon className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
            </div>
            <p className="text-blue-100 text-lg">Configure your Obby monitoring and AI preferences</p>
          </div>

          <button
            onClick={saveConfig}
            disabled={saving}
            className="relative overflow-hidden px-6 py-3 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group bg-white/20 hover:bg-white/30 border border-white/30 text-white"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
            <div className="relative flex items-center space-x-2">
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>Save Changes</span>
                </>
              )}
            </div>
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 mb-8" style={{
        backgroundColor: 'var(--color-surface)',
        padding: 'var(--spacing-md)',
        borderRadius: 'var(--border-radius-lg)',
        border: '1px solid var(--color-border)'
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200"
            style={{
              backgroundColor: activeTab === tab.id ? 'var(--color-primary)' : 'transparent',
              color: activeTab === tab.id ? 'white' : 'var(--color-text-secondary)',
              border: activeTab === tab.id ? 'none' : '1px solid var(--color-border)',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              if (activeTab !== tab.id) {
                e.currentTarget.style.backgroundColor = 'var(--color-background)'
                e.currentTarget.style.color = 'var(--color-text-primary)'
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== tab.id) {
                e.currentTarget.style.backgroundColor = 'transparent'
                e.currentTarget.style.color = 'var(--color-text-secondary)'
              }
            }}
          >
            <tab.icon className="h-4 w-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="transition-all duration-300 ease-in-out">
        {renderTabContent()}
      </div>
    </div>
  )
}
