import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Save, Trash2, Palette, FolderOpen, Plus, RefreshCw, FileText, Eye, EyeOff } from 'lucide-react'
import { ConfigSettings, ModelsResponse, WatchPatternsResponse, IgnorePatternsResponse, WatchConfigResponse } from '../types'
import { apiFetch } from '../utils/api'
import ThemeSwitcher from '../components/ThemeSwitcher'

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

  useEffect(() => {
    fetchConfig()
    fetchModels()
    fetchWatchConfig()
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




  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
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

      {/* Theme Settings */}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Settings */}
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

        {/* Interactive Watch Configuration */}
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

        {/* Enhanced Ignore Patterns */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <FileText className="h-5 w-5 text-primary-600 mr-3" />
              <h3 className="text-lg font-medium text-gray-900">Ignore Patterns</h3>
            </div>
            <button
              onClick={() => setShowIgnoreHelp(!showIgnoreHelp)}
              className="p-2 text-gray-500 hover:text-gray-700"
              title="Show help"
            >
              {showIgnoreHelp ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          
          {showIgnoreHelp && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
              <h4 className="text-sm font-medium text-yellow-900 mb-2">Ignore Pattern Examples:</h4>
              <ul className="text-sm text-yellow-700 space-y-1">
                <li>• <code className="bg-yellow-100 px-1 rounded">*.tmp</code> - Ignore temporary files</li>
                <li>• <code className="bg-yellow-100 px-1 rounded">.git/</code> - Ignore git directory</li>
                <li>• <code className="bg-yellow-100 px-1 rounded">node_modules/</code> - Ignore node modules</li>
                <li>• <code className="bg-yellow-100 px-1 rounded">session_summary.md</code> - Ignore specific file</li>
                <li>• <code className="bg-yellow-100 px-1 rounded">*.swp</code> - Ignore editor swap files</li>
              </ul>
              <p className="text-sm text-yellow-600 mt-2">
                Patterns are saved to <code className="bg-yellow-100 px-1 rounded">.obbyignore</code> file in project root.
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
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                onKeyPress={(e) => e.key === 'Enter' && addIgnorePatternAPI()}
              />
              <button
                onClick={addIgnorePatternAPI}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {ignorePatterns.map((pattern, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-red-50 border border-red-200 rounded-md">
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
    </div>
  )
}
