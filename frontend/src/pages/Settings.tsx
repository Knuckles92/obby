import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Save, FolderPlus, Trash2 } from 'lucide-react'
import { ConfigSettings, ModelsResponse } from '../types'

export default function Settings() {
  const [config, setConfig] = useState<ConfigSettings>({
    checkInterval: 5,
    openaiApiKey: '',
    aiModel: 'gpt-4o',
    watchPaths: [],
    ignorePatterns: []
  })
  const [models, setModels] = useState<Record<string, string>>({})
  const [modelsLoading, setModelsLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newWatchPath, setNewWatchPath] = useState('')
  const [newIgnorePattern, setNewIgnorePattern] = useState('')

  useEffect(() => {
    fetchConfig()
    fetchModels()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config')
      const data = await response.json()
      setConfig({
        checkInterval: data.checkInterval || 5,
        openaiApiKey: data.openaiApiKey || '',
        aiModel: data.openaiModel || 'gpt-4o',
        watchPaths: data.watchPaths || [],
        ignorePatterns: data.ignorePatterns || []
      })
    } catch (error) {
      console.error('Error fetching config:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/models')
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
      const response = await fetch('/api/config', {
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

  const addWatchPath = () => {
    if (newWatchPath.trim() && !config.watchPaths.includes(newWatchPath.trim())) {
      setConfig({
        ...config,
        watchPaths: [...config.watchPaths, newWatchPath.trim()]
      })
      setNewWatchPath('')
    }
  }

  const removeWatchPath = (index: number) => {
    setConfig({
      ...config,
      watchPaths: config.watchPaths.filter((_, i) => i !== index)
    })
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
          className="btn-primary"
        >
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Settings */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">General Settings</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Check Interval (seconds)
              </label>
              <input
                type="number"
                min="1"
                max="3600"
                value={config.checkInterval}
                onChange={(e) => setConfig({ ...config, checkInterval: parseInt(e.target.value) || 5 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
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
          </div>
        </div>

        {/* Watch Paths */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Watch Paths</h3>
          
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={newWatchPath}
                onChange={(e) => setNewWatchPath(e.target.value)}
                placeholder="Enter directory path..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                onKeyPress={(e) => e.key === 'Enter' && addWatchPath()}
              />
              <button
                onClick={addWatchPath}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                <FolderPlus className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2 max-h-48 overflow-y-auto">
              {config.watchPaths.map((path, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                  <span className="text-sm text-gray-700">{path}</span>
                  <button
                    onClick={() => removeWatchPath(index)}
                    className="p-1 text-red-600 hover:bg-red-100 rounded"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Ignore Patterns */}
        <div className="card lg:col-span-2">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Ignore Patterns</h3>
          
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={newIgnorePattern}
                onChange={(e) => setNewIgnorePattern(e.target.value)}
                placeholder="Enter ignore pattern (e.g., *.tmp, .git/, node_modules/)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                onKeyPress={(e) => e.key === 'Enter' && addIgnorePattern()}
              />
              <button
                onClick={addIgnorePattern}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Add
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {config.ignorePatterns.map((pattern, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                  <span className="text-sm text-gray-700 font-mono">{pattern}</span>
                  <button
                    onClick={() => removeIgnorePattern(index)}
                    className="p-1 text-red-600 hover:bg-red-100 rounded"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            {config.ignorePatterns.length === 0 && (
              <p className="text-gray-500 text-center py-4">No ignore patterns configured</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}