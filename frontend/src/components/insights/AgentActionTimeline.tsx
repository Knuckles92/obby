import React, { useState, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

// Types for agent timeline
interface AgentActionLog {
  id: number;
  session_id: string;
  phase: 'data_collection' | 'file_exploration' | 'analysis' | 'generation' | 'error';
  operation: string;
  details?: Record<string, any>;
  files_processed?: number;
  total_files?: number;
  current_file?: string;
  timing?: Record<string, any>;
  timestamp: string;
}

interface AgentActionTimelineProps {
  logs: AgentActionLog[];
  sessionId?: string;
  compact?: boolean;
  showFilters?: boolean;
}

const AgentActionTimeline: React.FC<AgentActionTimelineProps> = ({
  logs,
  sessionId,
  compact = false,
  showFilters = true
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  const [selectedPhase, setSelectedPhase] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set());

  // Phase configuration
  const phaseConfig = {
    data_collection: {
      label: 'Data Collection',
      icon: '📊',
      color: '#3b82f6',
      description: 'Gathering signals from various sources'
    },
    file_exploration: {
      label: 'File Exploration',
      icon: '🔍',
      color: '#10b981',
      description: 'AI is examining files to understand changes'
    },
    analysis: {
      label: 'AI Analysis',
      icon: '🧠',
      color: '#8b5cf6',
      description: 'Processing patterns and generating insights'
    },
    generation: {
      label: 'Generation',
      icon: '✨',
      color: '#f59e0b',
      description: 'Creating final insights output'
    },
    error: {
      label: 'Error',
      icon: '❌',
      color: '#ef4444',
      description: 'An error occurred during processing'
    }
  };

  // Filter and process logs
  const filteredLogs = useMemo(() => {
    let filtered = logs;

    // Filter by phase
    if (selectedPhase !== 'all') {
      filtered = filtered.filter(log => log.phase === selectedPhase);
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(log =>
        log.operation.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.current_file?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        JSON.stringify(log.details).toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    return filtered.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [logs, selectedPhase, searchTerm]);

  // Calculate timeline statistics
  const timelineStats = useMemo(() => {
    const stats = {
      totalLogs: logs.length,
      phaseCounts: {} as Record<string, number>,
      duration: null as string | null,
      filesExplored: new Set<string>(),
      toolsUsed: new Set<string>()
    };

    // Count by phase
    logs.forEach(log => {
      stats.phaseCounts[log.phase] = (stats.phaseCounts[log.phase] || 0) + 1;

      // Track files explored
      if (log.current_file) {
        stats.filesExplored.add(log.current_file);
      }

      // Track tools used from details
      if (log.details?.tools_used) {
        if (Array.isArray(log.details.tools_used)) {
          log.details.tools_used.forEach(tool => stats.toolsUsed.add(tool));
        } else {
          stats.toolsUsed.add(String(log.details.tools_used));
        }
      }
    });

    // Calculate total duration
    if (logs.length > 1) {
      const start = new Date(logs[0].timestamp).getTime();
      const end = new Date(logs[logs.length - 1].timestamp).getTime();
      const duration = end - start;

      if (duration < 1000) {
        stats.duration = `${duration}ms`;
      } else if (duration < 60000) {
        stats.duration = `${(duration / 1000).toFixed(1)}s`;
      } else {
        stats.duration = `${(duration / 60000).toFixed(1)}m`;
      }
    }

    return stats;
  }, [logs]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString();
  };

  const toggleLogExpansion = (logId: number) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  const getPhaseIcon = (phase: string) => {
    return phaseConfig[phase as keyof typeof phaseConfig]?.icon || '🔄';
  };

  const getPhaseColor = (phase: string) => {
    return phaseConfig[phase as keyof typeof phaseConfig]?.color || '#6b7280';
  };

  const getPhaseLabel = (phase: string) => {
    return phaseConfig[phase as keyof typeof phaseConfig]?.label || phase;
  };

  if (logs.length === 0) {
    return (
      <div className={`text-center py-12 ${
        isDark ? 'text-gray-400' : 'text-gray-600'
      }`}>
        <div className="text-4xl mb-4">📋</div>
        <h3 className={`text-lg font-medium mb-2 ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>
          No Agent Actions Recorded
        </h3>
        <p className="text-sm">
          No agent action logs are available for this session.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className={`text-lg font-semibold ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>
            Agent Action Timeline
          </h3>
          {sessionId && (
            <p className={`text-sm ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              Session ID: {sessionId}
            </p>
          )}
        </div>

        {/* Timeline Stats */}
        <div className="flex items-center gap-4 text-sm">
          <div className={`px-3 py-1 rounded-full ${
            isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
          }`}>
            {timelineStats.totalLogs} actions
          </div>

          {timelineStats.duration && (
            <div className={`px-3 py-1 rounded-full ${
              isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
            }`}>
              {timelineStats.duration}
            </div>
          )}

          <div className={`px-3 py-1 rounded-full ${
            isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
          }`}>
            {timelineStats.filesExplored.size} files
          </div>
        </div>
      </div>

      {/* Filters */}
      {showFilters && !compact && (
        <div className={`p-4 rounded-lg border ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
        }`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Phase filter */}
            <div>
              <label className={`block text-sm font-medium mb-2 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Filter by Phase
              </label>
              <select
                value={selectedPhase}
                onChange={(e) => setSelectedPhase(e.target.value)}
                className={`w-full px-3 py-2 rounded-lg border ${
                  isDark
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-300 text-gray-900'
                }`}
              >
                <option value="all">All Phases</option>
                {Object.entries(phaseConfig).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.icon} {config.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Search */}
            <div>
              <label className={`block text-sm font-medium mb-2 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Search Operations
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search operations, files, or details..."
                className={`w-full px-3 py-2 rounded-lg border ${
                  isDark
                    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                    : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                }`}
              />
            </div>
          </div>

          {/* Phase distribution */}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className={`text-sm font-medium mb-2 ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              Phase Distribution
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(phaseConfig).map(([key, config]) => {
                const count = timelineStats.phaseCounts[key] || 0;
                if (count === 0) return null;

                return (
                  <div
                    key={key}
                    className={`px-3 py-1 rounded-full text-sm ${
                      isDark ? 'bg-gray-700' : 'bg-gray-100'
                    }`}
                    style={{ borderLeft: `3px solid ${config.color}` }}
                  >
                    {config.icon} {config.label}: {count}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-4">
        {filteredLogs.length === 0 ? (
          <div className={`text-center py-8 ${
            isDark ? 'text-gray-400' : 'text-gray-600'
          }`}>
            No logs match the current filters.
          </div>
        ) : (
          filteredLogs.map((log, index) => {
            const isExpanded = expandedLogs.has(log.id);
            const isFirstOfDay = index === 0 ||
              formatDate(log.timestamp) !== formatDate(filteredLogs[index - 1].timestamp);

            return (
              <div key={log.id}>
                {/* Date separator */}
                {isFirstOfDay && !compact && (
                  <div className={`text-sm font-medium mb-3 ${
                    isDark ? 'text-gray-400' : 'text-gray-600'
                  }`}>
                    {formatDate(log.timestamp)}
                  </div>
                )}

                {/* Timeline item */}
                <div className={`flex gap-4 ${
                  compact ? 'items-start' : 'items-start'
                }`}>
                  {/* Timeline line and icon */}
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-lg border-2`}
                      style={{ borderColor: getPhaseColor(log.phase) }}
                    >
                      {getPhaseIcon(log.phase)}
                    </div>

                    {/* Timeline line */}
                    {index < filteredLogs.length - 1 && (
                      <div
                        className="w-0.5 h-full mt-2"
                        style={{ backgroundColor: getPhaseColor(log.phase) }}
                      />
                    )}
                  </div>

                  {/* Content */}
                  <div className={`flex-1 pb-6 ${
                    compact ? 'min-w-0' : ''
                  }`}>
                    <div
                      className={`p-4 rounded-lg border cursor-pointer transition-all ${
                        isDark
                          ? 'border-gray-700 bg-gray-800 hover:bg-gray-750'
                          : 'border-gray-200 bg-white hover:bg-gray-50'
                      } ${isExpanded ? 'ring-2 ring-blue-500/20' : ''}`}
                      onClick={() => toggleLogExpansion(log.id)}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          <h4 className={`font-semibold ${
                            isDark ? 'text-white' : 'text-gray-900'
                          }`}>
                            {log.operation}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <span
                              className={`text-xs px-2 py-1 rounded-full`}
                              style={{
                                backgroundColor: `${getPhaseColor(log.phase)}20`,
                                color: getPhaseColor(log.phase)
                              }}
                            >
                              {getPhaseLabel(log.phase)}
                            </span>
                            <span className={`text-xs ${
                              isDark ? 'text-gray-500' : 'text-gray-400'
                            }`}>
                              {formatTimestamp(log.timestamp)}
                            </span>
                          </div>
                        </div>

                        <div className={`transform transition-transform ${
                          isExpanded ? 'rotate-90' : ''
                        }`}>
                          ▶
                        </div>
                      </div>

                      {/* Current file */}
                      {log.current_file && (
                        <div className={`text-sm font-mono mb-2 p-2 rounded ${
                          isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                        }`}>
                          📄 {log.current_file}
                        </div>
                      )}

                      {/* Progress bar */}
                      {log.files_processed !== undefined && log.total_files && (
                        <div className="mb-2">
                          <div className={`flex justify-between text-xs mb-1 ${
                            isDark ? 'text-gray-400' : 'text-gray-600'
                          }`}>
                            <span>Progress</span>
                            <span>{log.files_processed} / {log.total_files} files</span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${(log.files_processed / log.total_files) * 100}%`,
                                backgroundColor: getPhaseColor(log.phase)
                              }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Expanded details */}
                      {isExpanded && log.details && Object.keys(log.details).length > 0 && (
                        <div className={`mt-3 p-3 rounded text-xs ${
                          isDark ? 'bg-gray-900 text-gray-300' : 'bg-gray-50 text-gray-700'
                        }`}>
                          <div className={`font-medium mb-2 ${
                            isDark ? 'text-gray-200' : 'text-gray-800'
                          }`}>
                            Additional Details:
                          </div>
                          {Object.entries(log.details).map(([key, value]) => (
                            <div key={key} className="mb-1">
                              <strong>{key}:</strong>{' '}
                              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Summary */}
      {!compact && timelineStats.toolsUsed.size > 0 && (
        <div className={`mt-6 p-4 rounded-lg border ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
        }`}>
          <h4 className={`font-medium mb-3 ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>
            Session Summary
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className={`font-medium mb-1 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Files Explored
              </div>
              <div className={`font-mono ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {timelineStats.filesExplored.size} unique files
              </div>
            </div>

            <div>
              <div className={`font-medium mb-1 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Tools Used
              </div>
              <div className={`font-mono ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {Array.from(timelineStats.toolsUsed).join(', ')}
              </div>
            </div>

            <div>
              <div className={`font-medium mb-1 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Total Duration
              </div>
              <div className={`font-mono ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {timelineStats.duration || 'Calculating...'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentActionTimeline;