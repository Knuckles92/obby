import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { api } from '../../utils/api';
import EnhancedInsightEvidence from './EnhancedInsightEvidence';

// Types for agent action logs
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

interface EnhancedInsightEvidenceWithLoadingProps {
  insight: any;
  onClose: () => void;
}

const EnhancedInsightEvidenceWithLoading: React.FC<EnhancedInsightEvidenceWithLoadingProps> = ({
  insight,
  onClose
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentLogs, setAgentLogs] = useState<AgentActionLog[]>([]);

  // Load agent logs when component mounts
  useEffect(() => {
    if (insight?.id) {
      loadAgentLogs(insight.id);
    }
  }, [insight?.id]);

  const loadAgentLogs = async (insightId: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/api/insights/${insightId}/agent-logs`);

      if (response.success && response.data) {
        setAgentLogs(response.data);
      } else {
        setError('Failed to load agent logs');
      }
    } catch (err) {
      console.error('Failed to load agent logs:', err);
      setError('Error loading agent logs');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Loading agent action logs...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center max-w-md">
          <div className="text-red-600 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0M3 12a9 9 0 1 0 18 0 9 9 0 0 1-18 0z" />
            </svg>
          </div>
          <h3 className={`text-lg font-medium mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Error Loading Data
          </h3>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'} mb-4`}>
            {error}
          </p>
          <button
            onClick={() => loadAgentLogs(insight.id)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              isDark
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            }`}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <EnhancedInsightEvidence
      evidence={insight?.evidence || {}}
      insightId={insight?.id}
      agentLogs={agentLogs}
      onClose={onClose}
    />
  );
};

export default EnhancedInsightEvidenceWithLoading;