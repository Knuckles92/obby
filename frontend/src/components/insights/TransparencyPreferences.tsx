import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { api } from '../../utils/api';

// Types for transparency preferences
interface TransparencySettings {
  progress_display_mode: 'minimal' | 'standard' | 'detailed';
  show_file_exploration: boolean;
  show_ai_reasoning: boolean;
  show_performance_metrics: boolean;
  show_data_sources: boolean;
  real_time_updates: boolean;
  auto_open_progress: boolean;
  store_agent_logs: boolean;
  log_retention_days: number;
  notification_preferences: {
    generation_complete: boolean;
    error_occurred: boolean;
    long_running_analysis: boolean;
  };
  ui_preferences: {
    compact_mode: boolean;
    show_timestamps: boolean;
    show_tool_usage: boolean;
    color_code_phases: boolean;
  };
}

interface TransparencyPreferencesProps {
  isVisible: boolean;
  onClose: () => void;
  onSave?: (settings: TransparencySettings) => void;
}

const TransparencyPreferences: React.FC<TransparencyPreferencesProps> = ({
  isVisible,
  onClose,
  onSave
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  const [settings, setSettings] = useState<TransparencySettings>({
    progress_display_mode: 'standard',
    show_file_exploration: true,
    show_ai_reasoning: true,
    show_performance_metrics: true,
    show_data_sources: true,
    real_time_updates: true,
    auto_open_progress: false,
    store_agent_logs: true,
    log_retention_days: 7,
    notification_preferences: {
      generation_complete: true,
      error_occurred: true,
      long_running_analysis: false
    },
    ui_preferences: {
      compact_mode: false,
      show_timestamps: true,
      show_tool_usage: true,
      color_code_phases: true
    }
  });

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'display' | 'notifications' | 'storage' | 'ui'>('display');

  // Load existing settings on mount
  useEffect(() => {
    if (isVisible) {
      loadSettings();
    }
  }, [isVisible]);

  const loadSettings = async () => {
    try {
      const response = await api.get('/api/config/transparency-preferences');
      if (response.success && response.data) {
        setSettings(response.data);
      }
    } catch (error) {
      console.error('Failed to load transparency preferences:', error);
    }
  };

  const saveSettings = async () => {
    try {
      setLoading(true);
      const response = await api.post('/api/config/transparency-preferences', settings);
      if (response.success) {
        onSave?.(settings);
        onClose();
      }
    } catch (error) {
      console.error('Failed to save transparency preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = <K extends keyof TransparencySettings>(
    key: K,
    value: TransparencySettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const updateNestedSetting = <K extends keyof TransparencySettings['notification_preferences']>(
    category: 'notification_preferences' | 'ui_preferences',
    key: K,
    value: any
  ) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  const resetToDefaults = () => {
    setSettings({
      progress_display_mode: 'standard',
      show_file_exploration: true,
      show_ai_reasoning: true,
      show_performance_metrics: true,
      show_data_sources: true,
      real_time_updates: true,
      auto_open_progress: false,
      store_agent_logs: true,
      log_retention_days: 7,
      notification_preferences: {
        generation_complete: true,
        error_occurred: true,
        long_running_analysis: false
      },
      ui_preferences: {
        compact_mode: false,
        show_timestamps: true,
        show_tool_usage: true,
        color_code_phases: true
      }
    });
  };

  const getDisplayModeDescription = (mode: string) => {
    const descriptions = {
      minimal: 'Show only basic progress information with minimal details',
      standard: 'Show balanced information with key metrics and operations',
      detailed: 'Show comprehensive information including all agent actions and detailed metrics'
    };
    return descriptions[mode as keyof typeof descriptions] || '';
  };

  if (!isVisible) return null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${
      isDark ? 'bg-black/50' : 'bg-black/30'
    }`}>
      <div className={`w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-xl shadow-2xl ${
        isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
      } border`}>

        {/* Header */}
        <div className={`px-6 py-4 border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl">⚙️</div>
              <div>
                <h2 className={`text-xl font-semibold ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  AI Transparency Preferences
                </h2>
                <p className={`text-sm ${
                  isDark ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  Configure how much detail you want to see about AI operations
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={resetToDefaults}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  isDark
                    ? 'hover:bg-gray-700 text-gray-400'
                    : 'hover:bg-gray-200 text-gray-600'
                }`}
              >
                Reset to Defaults
              </button>

              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onClose();
                }}
                className={`p-2 rounded-lg transition-colors ${
                  isDark
                    ? 'hover:bg-gray-700 text-gray-400'
                    : 'hover:bg-gray-200 text-gray-600'
                }`}
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        {/* Tab navigation */}
        <div className={`flex border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
        }`}>
          <button
            onClick={() => setActiveTab('display')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'display'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Display Settings
          </button>

          <button
            onClick={() => setActiveTab('notifications')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'notifications'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Notifications
          </button>

          <button
            onClick={() => setActiveTab('storage')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'storage'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Storage & Privacy
          </button>

          <button
            onClick={() => setActiveTab('ui')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'ui'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            UI Preferences
          </button>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto p-6" style={{ height: 'calc(90vh - 200px)' }}>

          {/* Display Settings Tab */}
          {activeTab === 'display' && (
            <div className="space-y-6">
              {/* Progress Display Mode */}
              <div>
                <h3 className={`text-lg font-semibold mb-3 ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  Progress Display Mode
                </h3>
                <div className="space-y-3">
                  {(['minimal', 'standard', 'detailed'] as const).map(mode => (
                    <label
                      key={mode}
                      className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
                        settings.progress_display_mode === mode
                          ? isDark ? 'border-blue-500 bg-blue-500/10' : 'border-blue-500 bg-blue-50'
                          : isDark ? 'border-gray-700 hover:border-gray-600' : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="progress_display_mode"
                        value={mode}
                        checked={settings.progress_display_mode === mode}
                        onChange={(e) => updateSetting('progress_display_mode', e.target.value as any)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className={`font-medium capitalize ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>
                          {mode}
                        </div>
                        <div className={`text-sm mt-1 ${
                          isDark ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {getDisplayModeDescription(mode)}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Information Display Options */}
              <div>
                <h3 className={`text-lg font-semibold mb-3 ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  Information Display
                </h3>
                <div className="space-y-3">
                  {[
                    { key: 'show_file_exploration', label: 'Show File Exploration', description: 'Display which files the AI is currently examining' },
                    { key: 'show_ai_reasoning', label: 'Show AI Reasoning', description: 'Display AI\'s decision-making process and analysis steps' },
                    { key: 'show_performance_metrics', label: 'Show Performance Metrics', description: 'Display timing, file counts, and efficiency metrics' },
                    { key: 'show_data_sources', label: 'Show Data Sources', description: 'Display which data sources are being analyzed' }
                  ].map(({ key, label, description }) => (
                    <label
                      key={key}
                      className={`flex items-start gap-3 p-3 rounded-lg ${
                        isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={settings[key as keyof typeof settings] as boolean}
                        onChange={(e) => updateSetting(key as keyof typeof settings, e.target.checked)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className={`font-medium ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>
                          {label}
                        </div>
                        <div className={`text-sm ${
                          isDark ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Real-time Updates */}
              <div>
                <h3 className={`text-lg font-semibold mb-3 ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  Real-time Updates
                </h3>
                <div className="space-y-3">
                  <label
                    className={`flex items-start gap-3 p-3 rounded-lg ${
                      isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={settings.real_time_updates}
                      onChange={(e) => updateSetting('real_time_updates', e.target.checked)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className={`font-medium ${
                        isDark ? 'text-white' : 'text-gray-900'
                      }`}>
                        Enable Real-time Updates
                      </div>
                      <div className={`text-sm ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Show live progress updates during AI analysis
                      </div>
                    </div>
                  </label>

                  <label
                    className={`flex items-start gap-3 p-3 rounded-lg ${
                      isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={settings.auto_open_progress}
                      onChange={(e) => updateSetting('auto_open_progress', e.target.checked)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className={`font-medium ${
                        isDark ? 'text-white' : 'text-gray-900'
                      }`}>
                        Auto-open Progress Dashboard
                      </div>
                      <div className={`text-sm ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Automatically open the progress dashboard when AI analysis starts
                      </div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <div>
                <h3 className={`text-lg font-semibold mb-3 ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  Notification Preferences
                </h3>
                <div className="space-y-3">
                  {[
                    { key: 'generation_complete', label: 'Generation Complete', description: 'Notify when AI insights generation is complete' },
                    { key: 'error_occurred', label: 'Error Occurred', description: 'Notify when an error occurs during AI analysis' },
                    { key: 'long_running_analysis', label: 'Long-running Analysis', description: 'Notify when analysis is taking longer than expected' }
                  ].map(({ key, label, description }) => (
                    <label
                      key={key}
                      className={`flex items-start gap-3 p-3 rounded-lg ${
                        isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={settings.notification_preferences[key as keyof typeof settings.notification_preferences]}
                        onChange={(e) => updateNestedSetting('notification_preferences', key as any, e.target.checked)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className={`font-medium ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>
                          {label}
                        </div>
                        <div className={`text-sm ${
                          isDark ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Storage & Privacy Tab */}
          {activeTab === 'storage' && (
            <div className="space-y-6">
              <div>
                <h3 className={`text-lg font-semibold mb-3 ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  Agent Log Storage
                </h3>
                <div className="space-y-4">
                  <label
                    className={`flex items-start gap-3 p-3 rounded-lg ${
                      isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={settings.store_agent_logs}
                      onChange={(e) => updateSetting('store_agent_logs', e.target.checked)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className={`font-medium ${
                        isDark ? 'text-white' : 'text-gray-900'
                      }`}>
                        Store Agent Action Logs
                      </div>
                      <div className={`text-sm ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Keep detailed logs of AI actions for transparency and debugging
                      </div>
                    </div>
                  </label>

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${
                      isDark ? 'text-gray-300' : 'text-gray-700'
                    }`}>
                      Log Retention Period: {settings.log_retention_days} days
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="30"
                      value={settings.log_retention_days}
                      onChange={(e) => updateSetting('log_retention_days', parseInt(e.target.value))}
                      className="w-full"
                      disabled={!settings.store_agent_logs}
                    />
                    <div className="flex justify-between text-xs mt-1">
                      <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>1 day</span>
                      <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>30 days</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className={`p-4 rounded-lg border ${
                isDark ? 'border-yellow-700 bg-yellow-900/20' : 'border-yellow-200 bg-yellow-50'
              }`}>
                <div className="flex items-start gap-2">
                  <span className="text-yellow-600">⚠️</span>
                  <div className={`text-sm ${
                    isDark ? 'text-yellow-200' : 'text-yellow-800'
                  }`}>
                    <strong>Privacy Note:</strong> Agent logs contain information about file access patterns and AI operations. These are stored locally and are used only for transparency and debugging purposes.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* UI Preferences Tab */}
          {activeTab === 'ui' && (
            <div className="space-y-6">
              <div>
                <h3 className={`text-lg font-semibold mb-3 ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  User Interface
                </h3>
                <div className="space-y-3">
                  {[
                    { key: 'compact_mode', label: 'Compact Mode', description: 'Use a more compact layout for progress information' },
                    { key: 'show_timestamps', label: 'Show Timestamps', description: 'Display detailed timestamps for all operations' },
                    { key: 'show_tool_usage', label: 'Show Tool Usage', description: 'Display which AI tools are being used' },
                    { key: 'color_code_phases', label: 'Color-code Phases', description: 'Use different colors to distinguish analysis phases' }
                  ].map(({ key, label, description }) => (
                    <label
                      key={key}
                      className={`flex items-start gap-3 p-3 rounded-lg ${
                        isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={settings.ui_preferences[key as keyof typeof settings.ui_preferences]}
                        onChange={(e) => updateNestedSetting('ui_preferences', key as any, e.target.checked)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className={`font-medium ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>
                          {label}
                        </div>
                        <div className={`text-sm ${
                          isDark ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className={`px-6 py-4 border-t ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className={`px-4 py-2 rounded-lg transition-colors ${
                isDark
                  ? 'bg-gray-700 hover:bg-gray-600 text-white'
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
              }`}
            >
              Cancel
            </button>

            <button
              onClick={saveSettings}
              disabled={loading}
              className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                loading
                  ? 'bg-gray-500 text-white cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              )}
              {loading ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransparencyPreferences;