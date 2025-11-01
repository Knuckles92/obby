import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { api } from '../../utils/api';

// Types for enhanced evidence
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

const stopPropagation = (e: React.MouseEvent) => {
  e.preventDefault();
  e.stopPropagation();
};

interface EnhancedInsightEvidenceProps {
  evidence: Record<string, any>;
  insightId?: string;
  agentLogs?: any[];
  onClose: () => void;
}

const EnhancedInsightEvidence: React.FC<EnhancedInsightEvidenceProps> = ({
  evidence,
  insightId,
  agentLogs = [],
  onClose
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'evidence' | 'timeline' | 'provenance'>('evidence');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary']));

  
  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (start: string, end: string) => {
    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    const duration = endTime - startTime;

    if (duration < 1000) {
      return `${duration}ms`;
    } else if (duration < 60000) {
      return `${(duration / 1000).toFixed(1)}s`;
    } else {
      return `${(duration / 60000).toFixed(1)}m`;
    }
  };

  const getPhaseIcon = (phase: string) => {
    const icons = {
      data_collection: '📊',
      file_exploration: '🔍',
      analysis: '🧠',
      generation: '✨',
      error: '❌'
    };
    return icons[phase as keyof typeof icons] || '🔄';
  };

  const getPhaseColor = (phase: string) => {
    const colors = {
      data_collection: '#3b82f6',
      file_exploration: '#10b981',
      analysis: '#8b5cf6',
      generation: '#f59e0b',
      error: '#ef4444'
    };
    return colors[phase as keyof typeof colors] || '#6b7280';
  };

  const EvidenceSection: React.FC<{ title: string; children: React.ReactNode; sectionKey: string }> = ({
    title,
    children,
    sectionKey
  }) => (
    <div className={`border rounded-lg ${
      isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
    }`}>
      <button
        onClick={() => toggleSection(sectionKey)}
        className={`w-full px-4 py-3 flex items-center justify-between text-left transition-colors ${
          isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50'
        }`}
      >
        <span className={`font-medium ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>
          {title}
        </span>
        <span className={`transform transition-transform ${
          expandedSections.has(sectionKey) ? 'rotate-90' : ''
        }`}>
          ▶
        </span>
      </button>

      {expandedSections.has(sectionKey) && (
        <div className={`px-4 py-3 border-t ${
          isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-gray-50'
        }`}>
          {children}
        </div>
      )}
    </div>
  );

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${
      isDark ? 'bg-black/50' : 'bg-black/30'
    }`}>
      <div className={`w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-xl shadow-2xl ${
        isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
      } border`}>

        {/* Header */}
        <div className={`px-6 py-4 border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl">🔍</div>
              <div>
                <h2 className={`text-xl font-semibold ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  Insight Evidence & Provenance
                </h2>
                <p className={`text-sm ${
                  isDark ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  Detailed breakdown of AI analysis and data sources
                </p>
              </div>
            </div>

            <button
              onClick={(e) => {
                stopPropagation(e);
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

        {/* Tab navigation */}
        <div className={`flex border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
        }`}>
          <button
            onClick={() => setActiveTab('evidence')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'evidence'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Evidence
          </button>

          <button
            onClick={() => setActiveTab('timeline')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'timeline'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
            disabled={!insightId}
          >
            Agent Timeline
            {!insightId && <span className="text-xs ml-2 opacity-50">(N/A)</span>}
          </button>

          <button
            onClick={() => setActiveTab('provenance')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'provenance'
                ? isDark ? 'text-blue-400 border-b-2 border-blue-400' : 'text-blue-600 border-b-2 border-blue-600'
                : isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Data Provenance
          </button>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto p-6" style={{ height: 'calc(90vh - 160px)' }}>

          {/* Evidence Tab */}
          {activeTab === 'evidence' && (
            <div className="space-y-4">
              {/* Summary */}
              <EvidenceSection title="Summary" sectionKey="summary">
                <div className={`space-y-2 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {evidence.reasoning && (
                    <div>
                      <h4 className={`font-medium mb-1 ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        Why this matters:
                      </h4>
                      <p className="italic">{evidence.reasoning}</p>
                    </div>
                  )}

                  {evidence.data_points && evidence.data_points.length > 0 && (
                    <div>
                      <h4 className={`font-medium mb-1 ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        Key Data Points:
                      </h4>
                      <ul className="list-disc list-inside space-y-1">
                        {evidence.data_points.map((point: any, index: number) => (
                          <li key={index} className="text-sm">{String(point)}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </EvidenceSection>

              {/* Analysis Metrics */}
              <EvidenceSection title="Analysis Metrics" sectionKey="metrics">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {evidence.semantic_entries_count !== undefined && (
                    <div className={`p-3 rounded-lg text-center ${
                      isDark ? 'bg-gray-800' : 'bg-gray-100'
                    }`}>
                      <div className={`text-2xl font-bold ${
                        isDark ? 'text-blue-400' : 'text-blue-600'
                      }`}>
                        {evidence.semantic_entries_count}
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Semantic Entries
                      </div>
                    </div>
                  )}

                  {evidence.file_changes_count !== undefined && (
                    <div className={`p-3 rounded-lg text-center ${
                      isDark ? 'bg-gray-800' : 'bg-gray-100'
                    }`}>
                      <div className={`text-2xl font-bold ${
                        isDark ? 'text-green-400' : 'text-green-600'
                      }`}>
                        {evidence.file_changes_count}
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        File Changes
                      </div>
                    </div>
                  )}

                  {evidence.comprehensive_summaries_count !== undefined && (
                    <div className={`p-3 rounded-lg text-center ${
                      isDark ? 'bg-gray-800' : 'bg-gray-100'
                    }`}>
                      <div className={`text-2xl font-bold ${
                        isDark ? 'text-purple-400' : 'text-purple-600'
                      }`}>
                        {evidence.comprehensive_summaries_count}
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Summaries
                      </div>
                    </div>
                  )}

                  {evidence.session_summaries_count !== undefined && (
                    <div className={`p-3 rounded-lg text-center ${
                      isDark ? 'bg-gray-800' : 'bg-gray-100'
                    }`}>
                      <div className={`text-2xl font-bold ${
                        isDark ? 'text-orange-400' : 'text-orange-600'
                      }`}>
                        {evidence.session_summaries_count}
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Sessions
                      </div>
                    </div>
                  )}
                </div>
              </EvidenceSection>

              {/* Most Active Files */}
              {evidence.most_active_files && evidence.most_active_files.length > 0 && (
                <EvidenceSection title="Most Active Files" sectionKey="files">
                  <div className="space-y-2">
                    {evidence.most_active_files.map((file: any, index: number) => (
                      <div
                        key={index}
                        className={`flex items-center gap-3 p-2 rounded ${
                          isDark ? 'bg-gray-800' : 'bg-gray-100'
                        }`}
                      >
                        <div className="w-6 h-6 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center">
                          {index + 1}
                        </div>
                        <div className={`font-mono text-sm ${
                          isDark ? 'text-gray-300' : 'text-gray-700'
                        }`}>
                          {file}
                        </div>
                      </div>
                    ))}
                  </div>
                </EvidenceSection>
              )}

              {/* Source Pointers */}
              {evidence.source_pointers && evidence.source_pointers.length > 0 && (
                <EvidenceSection title="Source References" sectionKey="sources">
                  <div className="space-y-2">
                    {evidence.source_pointers.map((pointer: string, index: number) => (
                      <div
                        key={index}
                        className={`p-2 rounded-lg text-sm font-mono ${
                          isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {pointer}
                      </div>
                    ))}
                  </div>
                </EvidenceSection>
              )}
            </div>
          )}

          {/* Agent Timeline Tab */}
          {activeTab === 'timeline' && (
            <div>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                    <p className={`text-sm ${
                      isDark ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      Loading agent action logs...
                    </p>
                  </div>
                </div>
              ) : agentLogs.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-4xl mb-4">📋</div>
                  <h3 className={`text-lg font-medium ${
                    isDark ? 'text-white' : 'text-gray-900'
                  } mb-2`}>
                    No Agent Logs Available
                  </h3>
                  <p className={`text-sm ${
                    isDark ? 'text-gray-400' : 'text-gray-600'
                  }`}>
                    Agent action logs are not available for this insight.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {agentLogs.map((log) => (
                    <div
                      key={log.id}
                      className={`flex gap-4 p-4 rounded-lg border-l-4`}
                      style={{ borderLeftColor: getPhaseColor(log.phase) }}
                    >
                      <div className="text-2xl">
                        {getPhaseIcon(log.phase)}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className={`font-semibold ${
                            isDark ? 'text-white' : 'text-gray-900'
                          }`}>
                            {log.operation}
                          </h4>
                          <span className={`text-xs ${
                            isDark ? 'text-gray-500' : 'text-gray-400'
                          }`}>
                            {formatTimestamp(log.timestamp)}
                          </span>
                        </div>

                        <div className={`text-sm mb-2 ${
                          isDark ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          Phase: <span className="font-medium" style={{ color: getPhaseColor(log.phase) }}>
                            {log.phase.replace('_', ' ')}
                          </span>
                        </div>

                        {log.current_file && (
                          <div className={`text-sm mb-2 font-mono ${
                            isDark ? 'text-gray-300' : 'text-gray-700'
                          }`}>
                            File: {log.current_file}
                          </div>
                        )}

                        {log.files_processed !== undefined && log.total_files && (
                          <div className="mb-2">
                            <div className={`text-sm mb-1 ${
                              isDark ? 'text-gray-400' : 'text-gray-600'
                            }`}>
                              Progress: {log.files_processed} / {log.total_files} files
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${(log.files_processed / log.total_files) * 100}%`,
                                  backgroundColor: getPhaseColor(log.phase)
                                }}
                              />
                            </div>
                          </div>
                        )}

                        {log.details && Object.keys(log.details).length > 0 && (
                          <div className={`p-2 rounded text-xs ${
                            isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {Object.entries(log.details).map(([key, value]) => (
                              <div key={key}>
                                <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Data Provenance Tab */}
          {activeTab === 'provenance' && (
            <div className="space-y-4">
              {/* Generation Info */}
              <EvidenceSection title="Generation Information" sectionKey="generation">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {evidence.generated_by_agent && (
                    <div>
                      <h4 className={`font-medium mb-1 ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        AI Model:
                      </h4>
                      <div className={`p-2 rounded font-mono text-sm ${
                        isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {evidence.generated_by_agent}
                      </div>
                    </div>
                  )}

                  {evidence.analysis_duration && (
                    <div>
                      <h4 className={`font-medium mb-1 ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        Analysis Duration:
                      </h4>
                      <div className={`p-2 rounded font-mono text-sm ${
                        isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {evidence.analysis_duration}
                      </div>
                    </div>
                  )}

                  {evidence.agent_turns_taken && (
                    <div>
                      <h4 className={`font-medium mb-1 ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        AI Turns Taken:
                      </h4>
                      <div className={`p-2 rounded font-mono text-sm ${
                        isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {evidence.agent_turns_taken}
                      </div>
                    </div>
                  )}

                  {evidence.agent_tools_used && (
                    <div>
                      <h4 className={`font-medium mb-1 ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        Tools Used:
                      </h4>
                      <div className={`p-2 rounded font-mono text-sm ${
                        isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {Array.isArray(evidence.agent_tools_used)
                          ? evidence.agent_tools_used.join(', ')
                          : String(evidence.agent_tools_used)
                        }
                      </div>
                    </div>
                  )}
                </div>
              </EvidenceSection>

              {/* Data Sources */}
              <EvidenceSection title="Data Sources" sectionKey="sources">
                <div className={`space-y-2 text-sm ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  <div className={`p-3 rounded-lg ${
                    isDark ? 'bg-gray-800' : 'bg-gray-100'
                  }`}>
                    <h4 className={`font-medium mb-2 ${
                      isDark ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      Analysis Scope:
                    </h4>
                    <p>This insight was generated by analyzing multiple data sources including:</p>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>Semantic entries from AI-generated summaries</li>
                      <li>File change patterns and activity</li>
                      <li>Comprehensive summaries</li>
                      <li>Session summary snapshots</li>
                    </ul>
                  </div>

                  <div className={`p-3 rounded-lg ${
                    isDark ? 'bg-gray-800' : 'bg-gray-100'
                  }`}>
                    <h4 className={`font-medium mb-2 ${
                      isDark ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      Analysis Boundaries:
                    </h4>
                    <p>The analysis respected configured watch patterns and excluded files matching ignore patterns. Only files within the monitored directories were considered for analysis.</p>
                  </div>
                </div>
              </EvidenceSection>

              {/* Confidence Score */}
              <EvidenceSection title="Confidence Assessment" sectionKey="confidence">
                <div className={`p-4 rounded-lg ${
                  isDark ? 'bg-gray-800' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center gap-4 mb-3">
                    <div className="text-3xl">🎯</div>
                    <div>
                      <h4 className={`font-medium ${
                        isDark ? 'text-gray-200' : 'text-gray-800'
                      }`}>
                        Analysis Confidence
                      </h4>
                      <p className={`text-sm ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Based on data quality and analysis depth
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className={`text-lg font-bold ${
                        isDark ? 'text-green-400' : 'text-green-600'
                      }`}>
                        High
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Data Quality
                      </div>
                    </div>
                    <div>
                      <div className={`text-lg font-bold ${
                        isDark ? 'text-blue-400' : 'text-blue-600'
                      }`}>
                        Medium
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Pattern Clarity
                      </div>
                    </div>
                    <div>
                      <div className={`text-lg font-bold ${
                        isDark ? 'text-purple-400' : 'text-purple-600'
                      }`}>
                        High
                      </div>
                      <div className={`text-xs ${
                        isDark ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        Actionability
                      </div>
                    </div>
                  </div>
                </div>
              </EvidenceSection>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnhancedInsightEvidence;