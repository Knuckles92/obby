import React, { useState, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

// Types for provenance data
interface ProvenanceData {
  insight_id: string;
  agent_session_id: string;
  generated_by_agent: string;
  agent_files_explored: string[];
  agent_tools_used: string[];
  agent_turns_taken: number;
  agent_duration_ms: number;
  analysis_timestamp: string;
  evidence_payload: {
    semantic_entries_count: number;
    file_changes_count: number;
    comprehensive_summaries_count: number;
    session_summaries_count: number;
    most_active_files: string[];
    search_patterns: string[];
    analysis_boundaries: {
      watch_patterns: string[];
      ignore_patterns: string[];
      scope_description: string;
    };
  };
}

interface EnhancedProvenanceDisplayProps {
  provenance: ProvenanceData;
  compact?: boolean;
  showFullAnalysis?: boolean;
}

const EnhancedProvenanceDisplay: React.FC<EnhancedProvenanceDisplayProps> = ({
  provenance,
  compact = false,
  showFullAnalysis = true
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(compact ? [] : ['summary', 'files'])
  );
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Process files explored data
  const filesAnalysis = useMemo(() => {
    const files = provenance.agent_files_explored || [];
    const fileExtensions = files.reduce((acc, file) => {
      const ext = file.split('.').pop()?.toLowerCase() || 'unknown';
      acc[ext] = (acc[ext] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const directories = files.reduce((acc, file) => {
      const dir = file.split('/').slice(0, -1).join('/') || 'root';
      acc[dir] = (acc[dir] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalFiles: files.length,
      uniqueFiles: [...new Set(files)],
      fileExtensions,
      directories,
      mostChangedFiles: provenance.evidence_payload?.most_active_files || []
    };
  }, [provenance.agent_files_explored, provenance.evidence_payload]);

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const iconMap: Record<string, string> = {
      js: '🟨',
      jsx: '🟨',
      ts: '🔷',
      tsx: '🔷',
      py: '🐍',
      json: '📄',
      md: '📝',
      yml: '📋',
      yaml: '📋',
      sql: '🗃️',
      html: '🌐',
      css: '🎨',
      vue: '💚',
      sh: '⚡',
      dockerfile: '🐳'
    };
    return iconMap[ext || ''] || '📄';
  };

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

  const ProvenanceSection: React.FC<{
    title: string;
    children: React.ReactNode;
    sectionKey: string;
    icon?: string;
  }> = ({ title, children, sectionKey, icon }) => (
    <div className={`border rounded-lg overflow-hidden ${
      isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
    }`}>
      <button
        onClick={() => toggleSection(sectionKey)}
        className={`w-full px-4 py-3 flex items-center justify-between text-left transition-colors ${
          isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50'
        }`}
      >
        <div className="flex items-center gap-2">
          {icon && <span>{icon}</span>}
          <span className={`font-medium ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>
            {title}
          </span>
        </div>
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

  if (compact) {
    return (
      <div className={`p-4 rounded-lg border ${
        isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
      }`}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="text-center">
            <div className={`text-2xl font-bold ${
              isDark ? 'text-blue-400' : 'text-blue-600'
            }`}>
              {filesAnalysis.totalFiles}
            </div>
            <div className={`text-xs ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              Files Analyzed
            </div>
          </div>

          <div className="text-center">
            <div className={`text-2xl font-bold ${
              isDark ? 'text-green-400' : 'text-green-600'
            }`}>
              {provenance.agent_turns_taken || 0}
            </div>
            <div className={`text-xs ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              AI Turns
            </div>
          </div>

          <div className="text-center">
            <div className={`text-2xl font-bold ${
              isDark ? 'text-purple-400' : 'text-purple-600'
            }`}>
              {formatDuration(provenance.agent_duration_ms || 0)}
            </div>
            <div className={`text-xs ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              Duration
            </div>
          </div>

          <div className="text-center">
            <div className={`text-2xl font-bold ${
              isDark ? 'text-orange-400' : 'text-orange-600'
            }`}>
              {provenance.generated_by_agent}
            </div>
            <div className={`text-xs ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              AI Model
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Generation Summary */}
      <ProvenanceSection title="Generation Summary" sectionKey="summary" icon="🎯">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className={`p-4 rounded-lg ${
            isDark ? 'bg-gray-800' : 'bg-gray-100'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🤖</span>
              <span className={`font-medium ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                AI Model
              </span>
            </div>
            <div className={`font-mono text-sm ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              {provenance.generated_by_agent}
            </div>
          </div>

          <div className={`p-4 rounded-lg ${
            isDark ? 'bg-gray-800' : 'bg-gray-100'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">⏱️</span>
              <span className={`font-medium ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Duration
              </span>
            </div>
            <div className={`font-mono text-sm ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              {formatDuration(provenance.agent_duration_ms || 0)}
            </div>
          </div>

          <div className={`p-4 rounded-lg ${
            isDark ? 'bg-gray-800' : 'bg-gray-100'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔄</span>
              <span className={`font-medium ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                AI Turns
              </span>
            </div>
            <div className={`font-mono text-sm ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              {provenance.agent_turns_taken || 0} turns
            </div>
          </div>

          <div className={`p-4 rounded-lg ${
            isDark ? 'bg-gray-800' : 'bg-gray-100'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🆔</span>
              <span className={`font-medium ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Session ID
              </span>
            </div>
            <div className={`font-mono text-xs ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              {provenance.agent_session_id}
            </div>
          </div>
        </div>

        <div className={`mt-4 p-3 rounded-lg ${
          isDark ? 'bg-gray-800' : 'bg-gray-100'
        }`}>
          <div className={`text-sm ${
            isDark ? 'text-gray-400' : 'text-gray-600'
          }`}>
            Analysis completed at {formatTimestamp(provenance.analysis_timestamp)}
          </div>
        </div>
      </ProvenanceSection>

      {/* Files Analysis */}
      <ProvenanceSection title="Files Analysis" sectionKey="files" icon="📁">
        <div className="space-y-4">
          {/* File stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${
                isDark ? 'text-blue-400' : 'text-blue-600'
              }`}>
                {filesAnalysis.totalFiles}
              </div>
              <div className={`text-xs ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                Total Files
              </div>
            </div>

            <div className="text-center">
              <div className={`text-2xl font-bold ${
                isDark ? 'text-green-400' : 'text-green-600'
              }`}>
                {Object.keys(filesAnalysis.fileExtensions).length}
              </div>
              <div className={`text-xs ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                File Types
              </div>
            </div>

            <div className="text-center">
              <div className={`text-2xl font-bold ${
                isDark ? 'text-purple-400' : 'text-purple-600'
              }`}>
                {Object.keys(filesAnalysis.directories).length}
              </div>
              <div className={`text-xs ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                Directories
              </div>
            </div>

            <div className="text-center">
              <div className={`text-2xl font-bold ${
                isDark ? 'text-orange-400' : 'text-orange-600'
              }`}>
                {filesAnalysis.mostChangedFiles.length}
              </div>
              <div className={`text-xs ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                Most Active
              </div>
            </div>
          </div>

          {/* File extensions breakdown */}
          <div>
            <h4 className={`font-medium mb-2 ${
              isDark ? 'text-gray-200' : 'text-gray-800'
            }`}>
              File Types
            </h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(filesAnalysis.fileExtensions).map(([ext, count]) => (
                <div
                  key={ext}
                  className={`px-3 py-1 rounded-full text-sm ${
                    isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  {getFileIcon(`file.${ext}`)} {ext.toUpperCase()}: {count}
                </div>
              ))}
            </div>
          </div>

          {/* Most active files */}
          {filesAnalysis.mostChangedFiles.length > 0 && (
            <div>
              <h4 className={`font-medium mb-2 ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Most Active Files
              </h4>
              <div className="space-y-2">
                {filesAnalysis.mostChangedFiles.map((file, index) => (
                  <div
                    key={file}
                    className={`flex items-center gap-3 p-2 rounded cursor-pointer ${
                      isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
                    }`}
                    onClick={() => setSelectedFile(selectedFile === file ? null : file)}
                  >
                    <div className="w-6 h-6 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center">
                      {index + 1}
                    </div>
                    <span className="text-lg">{getFileIcon(file)}</span>
                    <div className={`font-mono text-sm flex-1 ${
                      isDark ? 'text-gray-300' : 'text-gray-700'
                    }`}>
                      {file}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Selected file details */}
          {selectedFile && (
            <div className={`p-4 rounded-lg border ${
              isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <h4 className={`font-medium ${
                  isDark ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  File Details: {selectedFile}
                </h4>
                <button
                  onClick={() => setSelectedFile(null)}
                  className={`p-1 rounded ${
                    isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
                  }`}
                >
                  ✕
                </button>
              </div>
              <div className={`text-sm ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                <p>This file was actively analyzed during the AI session.</p>
                <p>The AI examined its content, structure, and relationships with other files.</p>
              </div>
            </div>
          )}
        </div>
      </ProvenanceSection>

      {/* Tools and Methods */}
      <ProvenanceSection title="AI Tools & Methods" sectionKey="tools" icon="🔧">
        <div className="space-y-4">
          <div>
            <h4 className={`font-medium mb-2 ${
              isDark ? 'text-gray-200' : 'text-gray-800'
            }`}>
              Tools Used
            </h4>
            <div className="flex flex-wrap gap-2">
              {(provenance.agent_tools_used || []).map((tool) => (
                <div
                  key={tool}
                  className={`px-3 py-1 rounded-lg text-sm font-mono ${
                    isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {tool}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className={`font-medium mb-2 ${
              isDark ? 'text-gray-200' : 'text-gray-800'
            }`}>
              Analysis Approach
            </h4>
            <div className={`p-3 rounded-lg ${
              isDark ? 'bg-gray-800' : 'bg-gray-100'
            }`}>
              <ul className={`space-y-1 text-sm ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                <li>• Autonomous file exploration using Read, Grep, and Glob tools</li>
                <li>• Pattern recognition across multiple data sources</li>
                <li>• Contextual analysis of file relationships</li>
                <li>• Evidence-based insight generation</li>
              </ul>
            </div>
          </div>
        </div>
      </ProvenanceSection>

      {/* Analysis Scope */}
      <ProvenanceSection title="Analysis Scope" sectionKey="scope" icon="🎯">
        <div className="space-y-4">
          <div>
            <h4 className={`font-medium mb-2 ${
              isDark ? 'text-gray-200' : 'text-gray-800'
            }`}>
              Data Sources Analyzed
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className={`p-3 rounded-lg ${
                isDark ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <div className={`font-medium mb-1 ${
                  isDark ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  Semantic Entries
                </div>
                <div className={`text-2xl font-bold ${
                  isDark ? 'text-blue-400' : 'text-blue-600'
                }`}>
                  {provenance.evidence_payload?.semantic_entries_count || 0}
                </div>
              </div>

              <div className={`p-3 rounded-lg ${
                isDark ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <div className={`font-medium mb-1 ${
                  isDark ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  File Changes
                </div>
                <div className={`text-2xl font-bold ${
                  isDark ? 'text-green-400' : 'text-green-600'
                }`}>
                  {provenance.evidence_payload?.file_changes_count || 0}
                </div>
              </div>

              <div className={`p-3 rounded-lg ${
                isDark ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <div className={`font-medium mb-1 ${
                  isDark ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  Comprehensive Summaries
                </div>
                <div className={`text-2xl font-bold ${
                  isDark ? 'text-purple-400' : 'text-purple-600'
                }`}>
                  {provenance.evidence_payload?.comprehensive_summaries_count || 0}
                </div>
              </div>

              <div className={`p-3 rounded-lg ${
                isDark ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <div className={`font-medium mb-1 ${
                  isDark ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  Session Summaries
                </div>
                <div className={`text-2xl font-bold ${
                  isDark ? 'text-orange-400' : 'text-orange-600'
                }`}>
                  {provenance.evidence_payload?.session_summaries_count || 0}
                </div>
              </div>
            </div>
          </div>

          {/* Analysis boundaries */}
          {provenance.evidence_payload?.analysis_boundaries && (
            <div>
              <h4 className={`font-medium mb-2 ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Analysis Boundaries
              </h4>
              <div className={`p-3 rounded-lg ${
                isDark ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <p className={`text-sm mb-2 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {provenance.evidence_payload.analysis_boundaries.scope_description}
                </p>

                {provenance.evidence_payload.analysis_boundaries.watch_patterns?.length > 0 && (
                  <div className="mb-2">
                    <div className={`font-medium text-sm mb-1 ${
                      isDark ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      Watch Patterns:
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {provenance.evidence_payload.analysis_boundaries.watch_patterns.map((pattern, index) => (
                        <span
                          key={index}
                          className={`px-2 py-1 rounded text-xs font-mono ${
                            isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-700'
                          }`}
                        >
                          {pattern}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {provenance.evidence_payload.analysis_boundaries.ignore_patterns?.length > 0 && (
                  <div>
                    <div className={`font-medium text-sm mb-1 ${
                      isDark ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      Ignore Patterns:
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {provenance.evidence_payload.analysis_boundaries.ignore_patterns.map((pattern, index) => (
                        <span
                          key={index}
                          className={`px-2 py-1 rounded text-xs font-mono ${
                            isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {pattern}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </ProvenanceSection>

      {/* Quality Indicators */}
      {showFullAnalysis && (
        <ProvenanceSection title="Quality Indicators" sectionKey="quality" icon="📊">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`p-4 rounded-lg text-center ${
              isDark ? 'bg-gray-800' : 'bg-gray-100'
            }`}>
              <div className="text-3xl mb-2">🎯</div>
              <div className={`font-medium mb-1 ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Data Quality
              </div>
              <div className={`text-lg font-bold ${
                isDark ? 'text-green-400' : 'text-green-600'
              }`}>
                High
              </div>
              <div className={`text-xs mt-1 ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                Comprehensive data from multiple sources
              </div>
            </div>

            <div className={`p-4 rounded-lg text-center ${
              isDark ? 'bg-gray-800' : 'bg-gray-100'
            }`}>
              <div className="text-3xl mb-2">🔍</div>
              <div className={`font-medium mb-1 ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Analysis Depth
              </div>
              <div className={`text-lg font-bold ${
                isDark ? 'text-blue-400' : 'text-blue-600'
              }`}>
                Thorough
              </div>
              <div className={`text-xs mt-1 ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {provenance.agent_turns_taken} AI interaction turns
              </div>
            </div>

            <div className={`p-4 rounded-lg text-center ${
              isDark ? 'bg-gray-800' : 'bg-gray-100'
            }`}>
              <div className="text-3xl mb-2">⚡</div>
              <div className={`font-medium mb-1 ${
                isDark ? 'text-gray-200' : 'text-gray-800'
              }`}>
                Performance
              </div>
              <div className={`text-lg font-bold ${
                isDark ? 'text-purple-400' : 'text-purple-600'
              }`}>
                Efficient
              </div>
              <div className={`text-xs mt-1 ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                {formatDuration(provenance.agent_duration_ms || 0)} total time
              </div>
            </div>
          </div>
        </ProvenanceSection>
      )}
    </div>
  );
};

export default EnhancedProvenanceDisplay;