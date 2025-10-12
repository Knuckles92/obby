import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Save, Trash2, Palette, FolderOpen, Plus, RefreshCw, FileText, Eye, EyeOff } from 'lucide-react'
import { ConfigSettings, ModelsResponse, WatchPatternsResponse, IgnorePatternsResponse, WatchConfigResponse } from '../types'
import { apiFetch } from '../utils/api'
import ThemeSwitcher from '../components/ThemeSwitcher'

export default function Settings() {
  const [config, setConfig] = useState<ConfigSettings>({
    checkInterval: 5,
    openaiApiKey: '',
    aiModel: 'gpt-4.1-mini',
    ignorePatterns: [],
    monitoringDirectory: 'notes',
    periodicCheckEnabled: true,
    aiUpdateInterval: 12,
    aiAutoUpdateEnabled: true,
    lastAiUpdateTimestamp: null
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
        checkInterval: data.checkInterval || 5,
        openaiApiKey: data.openaiApiKey || '',
        aiModel: data.aiModel || 'gpt-4.1-mini',
        ignorePatterns: data.ignorePatterns || [],
        monitoringDirectory: data.monitoringDirectory || 'notes',
        periodicCheckEnabled: data.periodicCheckEnabled ?? true,
        aiUpdateInterval: data.aiUpdateInterval || 12,
        aiAutoUpdateEnabled: data.aiAutoUpdateEnabled ?? true,
        lastAiUpdateTimestamp: data.lastAiUpdateTimestamp || null
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
          'gpt-4o': 'gpt-4o',
          'gpt-4.1': 'gpt-4.1',
          'gpt-4.1-mini': 'gpt-4.1-mini',
          'o4-mini': 'o4-mini',
          'gpt-4.1-nano': 'gpt-4.1-nano'
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
        'gpt-4o': 'gpt-4o', 
        'gpt-4.1': 'gpt-4.1',
        'gpt-4.1-mini': 'gpt-4.1-mini',
        'o4-mini': 'o4-mini',
        'gpt-4.1-nano': 'gpt-4.1-nano'
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



  const addIgnorePattern = () => {
    if (newIgnorePattern.trim() && !config.ignorePatterns.includes(newIgnorePattern.trim())) {
      setConfig({
        ...config,
        ignorePatterns: [...config.ignorePatterns, newIgnorePattern.trim()]
      })
      setNewIgnorePattern('')
    }
  }

  const removeIgnorePattern = (index: number) => {
    setConfig({
      ...config,
      ignorePatterns: config.ignorePatterns.filter((_, i) => i !== index)
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <SettingsIcon className="h-6 w-6 text-gray-600 mr-3" />
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        </div>
        
        <button
          onClick={saveConfig}
          disabled={saving}
          className="btn-primary flex items-center justify-center"
        >
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {/* Theme Settings */}
      <div className="card">
        <div className="flex items-center mb-4">
          <Palette className="h-5 w-5 text-primary-600 mr-3" />
          <h3 className="text-lg font-medium text-gray-900">Theme & Appearance</h3>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Current Theme
            </label>
            <ThemeSwitcher />
          </div>
          
          <div className="text-sm text-gray-600">
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
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">General Settings</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Periodic Check Interval (seconds)
              </label>
              <p className="text-sm text-gray-500 mb-2">
                In addition to real-time monitoring, Obby can also periodically scan all files for changes.
              </p>
              <input
                type="number"
                min="1"
                max="3600"
                value={config.checkInterval}
                onChange={(e) => setConfig({ ...config, checkInterval: parseInt(e.target.value) || 5 })}
                disabled={!config.periodicCheckEnabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
              />
            </div>

            <div>
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={config.periodicCheckEnabled}
                  onChange={(e) => setConfig({ ...config, periodicCheckEnabled: e.target.checked })}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="text-sm font-medium text-gray-700">
                  Enable Periodic Checking
                </span>
              </label>
              <p className="text-sm text-gray-500 mt-1 ml-7">
                When enabled, Obby will check all watched files at the specified interval,
                in addition to real-time change detection.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FolderOpen className="h-4 w-4 inline mr-2" />
                Monitoring Directory
              </label>
              <p className="text-sm text-gray-500 mb-2">
                The base directory that Obby monitors for changes. All generated summaries will be saved to the output/ directory.
              </p>
              <input
                type="text"
                value={config.monitoringDirectory || 'notes'}
                onChange={(e) => setConfig({ ...config, monitoringDirectory: e.target.value })}
                placeholder="notes"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
              <p className="text-sm text-gray-400 mt-1">
                ⚠️ Cannot be set to 'output' to prevent feedback loops
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                AI Model
              </label>
              <select
                value={config.aiModel}
                onChange={(e) => setConfig({ ...config, aiModel: e.target.value })}
                disabled={modelsLoading}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
              >
                {modelsLoading ? (
                  <option value="">Loading models...</option>
                ) : (
                  Object.entries(models).map(([key, value]) => {
                    // Create display names for better UX
                    const displayName = key === 'gpt-4o' ? 'GPT-4o (Latest)' :
                                       key === 'gpt-4.1' ? 'GPT-4.1' :
                                       key === 'gpt-4.1-mini' ? 'GPT-4.1 Mini' :
                                       key === 'o4-mini' ? 'O4 Mini' :
                                       key === 'gpt-4.1-nano' ? 'GPT-4.1 Nano' :
                                       key.charAt(0).toUpperCase() + key.slice(1)
                    
                    return (
                      <option key={key} value={value}>
                        {displayName}
                      </option>
                    )
                  })
                )}
              </select>
              {modelsLoading && (
                <p className="text-sm text-gray-500 mt-1">Fetching latest models...</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                OpenAI API Key
              </label>
              <input
                type="password"
                value={config.openaiApiKey}
                onChange={(e) => setConfig({ ...config, openaiApiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            {/* AI Update Frequency Section */}
            <div className="border-t border-gray-200 pt-4">
              <h4 className="text-md font-medium text-gray-900 mb-4">AI Update Frequency</h4>
              
              <div className="space-y-4">
                <div>
                  <label className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={config.aiAutoUpdateEnabled || false}
                      onChange={(e) => setConfig({ ...config, aiAutoUpdateEnabled: e.target.checked })}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      Enable Automatic AI Updates
                    </span>
                  </label>
                  <p className="text-sm text-gray-500 mt-1 ml-7">
                    When enabled, AI analysis will run automatically at the specified interval.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    AI Update Interval (hours)
                  </label>
                  <p className="text-sm text-gray-500 mb-2">
                    How often AI processing runs (separate from file monitoring). Default is 12 hours (twice daily).
                  </p>
                  <input
                    type="number"
                    min="1"
                    max="168"
                    value={config.aiUpdateInterval || 12}
                    onChange={(e) => setConfig({ ...config, aiUpdateInterval: parseInt(e.target.value) || 12 })}
                    disabled={!config.aiAutoUpdateEnabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Range: 1 hour to 168 hours (1 week)
                  </p>
                </div>

                {config.lastAiUpdateTimestamp && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Last AI Update
                    </label>
                    <p className="text-sm text-gray-600">
                      {new Date(config.lastAiUpdateTimestamp).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Interactive Watch Configuration */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <FolderOpen className="h-5 w-5 text-primary-600 mr-3" />
              <h3 className="text-lg font-medium text-gray-900">Watch Directories</h3>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowWatchHelp(!showWatchHelp)}
                className="p-2 text-gray-500 hover:text-gray-700"
                title="Show help"
              >
                {showWatchHelp ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={reloadWatchConfig}
                className="p-2 text-gray-500 hover:text-gray-700"
                title="Reload configuration"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>
          
          {showWatchHelp && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">Watch Pattern Examples:</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• <code className="bg-blue-100 px-1 rounded">notes/</code> - Monitor entire notes directory</li>
                <li>• <code className="bg-blue-100 px-1 rounded">*.md</code> - Monitor all markdown files</li>
                <li>• <code className="bg-blue-100 px-1 rounded">docs/</code> - Monitor docs directory</li>
                <li>• <code className="bg-blue-100 px-1 rounded">project_notes/</code> - Monitor specific subdirectory</li>
              </ul>
              <p className="text-sm text-blue-600 mt-2">
                Patterns are saved to <code className="bg-blue-100 px-1 rounded">.obbywatch</code> file in project root.
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
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                onKeyPress={(e) => e.key === 'Enter' && addWatchPattern()}
              />
              <button
                onClick={addWatchPattern}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
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
                <li>• <code className="bg-yellow-100 px-1 rounded">living_note.md</code> - Ignore specific file</li>
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
