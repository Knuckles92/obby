import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../utils/api';
import InsightFilters from '../components/insights/InsightFilters';
import InsightEvidence from '../components/insights/InsightEvidence';

// Types for insights
interface Insight {
  id: string;
  category: 'action' | 'pattern' | 'relationship' | 'temporal' | 'opportunity' | 'quality' | 'velocity' | 'risk' | 'documentation' | 'follow-ups';
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  content: string;
  relatedFiles: string[];
  evidence?: {
    reasoning?: string;
    data_points?: any[];
    source_pointers?: string[];
    generated_by_agent?: string;
    semantic_entries_count?: number;
    file_changes_count?: number;
    comprehensive_summaries_count?: number;
    session_summaries_count?: number;
    most_active_files?: string[];
  };
  timestamp: string;
  dismissed: boolean;
  archived: boolean;
  sourceSection?: string;
  sourcePointers?: string[];
  generatedByAgent?: string;
}

interface InsightsResponse {
  success: boolean;
  data: Insight[];
  metadata: {
    time_range_days: number;
    max_insights: number;
    generated_at: string;
    total_insights: number;
    filters?: {
      category?: string;
      priority?: string;
      sourceSection?: string;
      include_dismissed?: boolean;
    };
  };
}

// Category configuration
const CATEGORY_CONFIG = {
  action: {
    label: 'Action Items',
    icon: '✅',
    color: '#3b82f6',
    bgColor: '#dbeafe'
  },
  pattern: {
    label: 'Patterns',
    icon: '🔄', 
    color: '#8b5cf6',
    bgColor: '#ede9fe'
  },
  relationship: {
    label: 'Connections',
    icon: '🔗',
    color: '#ec4899',
    bgColor: '#fce7f3'
  },
  temporal: {
    label: 'Timing',
    icon: '⏰',
    color: '#f59e0b',
    bgColor: '#fef3c7'
  },
  opportunity: {
    label: 'Opportunities',
    icon: '💡',
    color: '#10b981',
    bgColor: '#d1fae5'
  },
  quality: {
    label: 'Quality',
    icon: '🔍',
    color: '#ef4444',
    bgColor: '#fecaca'
  },
  velocity: {
    label: 'Velocity',
    icon: '🚀',
    color: '#f97316',
    bgColor: '#fef3c7'
  },
  risk: {
    label: 'Risk',
    icon: '⚠️',
    color: '#ef4444',
    bgColor: '#fecaca'
  },
  documentation: {
    label: 'Documentation',
    icon: '📚',
    color: '#06b6d4',
    bgColor: '#e0e7f5'
  },
  'follow-ups': {
    label: 'Follow-ups',
    icon: '📋',
    color: '#8b5cf6',
    bgColor: '#dbeafe'
  }
};

// Priority configuration
const PRIORITY_CONFIG = {
  critical: { label: 'Critical', color: '#ef4444', borderColor: '#dc2626' },
  high: { label: 'High', color: '#f97316', borderColor: '#ea580c' },
  medium: { label: 'Medium', color: '#eab308', borderColor: '#ca8a04' },
  low: { label: 'Low', color: '#22c55e', borderColor: '#16a34a' }
};

const Insights: React.FC = () => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<number>(7);
  const [includeDismissed, setIncludeDismissed] = useState(false);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);

  // Load insights
  useEffect(() => {
    loadInsights();
  }, [timeRange, filter, includeDismissed]);

  const loadInsights = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        time_range_days: timeRange.toString(),
        max_insights: '20',
        include_dismissed: includeDismissed.toString()
      });
      
      if (filter !== 'all') {
        params.set('category', filter);
      }
      
      const response = await api.get<InsightsResponse>(
        `/api/insights/?${params.toString()}`
      );
      
      if (response.success && response.data) {
        setInsights(response.data);
      } else {
        setError('Failed to load insights');
      }
    } catch (err) {
      console.error('Error loading insights:', err);
      setError('Failed to load insights');
    } finally {
      setLoading(false);
    }
  };

  const generateInsights = async () => {
    try {
      setGenerating(true);
      setError(null);
      
      const params = new URLSearchParams({
        time_range_days: timeRange.toString(),
        max_insights: '20'
      });
      
      const response = await api.post<InsightsResponse>(
        `/api/insights/refresh?${params.toString()}`
      );
      
      if (response.success && response.data) {
        setInsights(response.data);
      } else {
        setError('Failed to generate insights');
      }
    } catch (err) {
      console.error('Error generating insights:', err);
      setError('Failed to generate insights');
    } finally {
      setGenerating(false);
      // Reload insights to ensure we have the latest data
      await loadInsights();
    }
  };

  const dismissInsight = async (insightId: string) => {
    try {
      await api.post(`/api/insights/${insightId}/dismiss`);
      setInsights(insights.filter(i => i.id !== insightId));
      if (selectedInsight?.id === insightId) {
        setSelectedInsight(null);
      }
    } catch (err) {
      console.error('Error dismissing insight:', err);
    }
  };

  const archiveInsight = async (insightId: string) => {
    try {
      await api.post(`/api/insights/${insightId}/archive`);
      setInsights(insights.filter(i => i.id !== insightId));
      if (selectedInsight?.id === insightId) {
        setSelectedInsight(null);
      }
    } catch (err) {
      console.error('Error archiving insight:', err);
    }
  };

  const filteredInsights = insights.filter(insight => {
    // Filter by dismissal/archive status
    if (filter === 'dismissed') return insight.dismissed;
    if (filter === 'archived') return insight.archived;

    // Exclude dismissed insights unless explicitly included
    if (!includeDismissed && insight.dismissed) return false;

    // Filter by category if not 'all'
    if (filter !== 'all' && filter !== 'dismissed' && filter !== 'archived') {
      if (insight.category !== filter) return false;
    }

    return true;
  });

  const InsightCard: React.FC<{ insight: Insight }> = ({ insight }) => {
    const category = CATEGORY_CONFIG[insight.category];
    const priority = PRIORITY_CONFIG[insight.priority];
    const [expanded, setExpanded] = useState(false);

    return (
      <div
        className={`relative p-4 rounded-lg border-2 transition-all duration-200 hover:shadow-lg cursor-pointer
          bg-white dark:bg-gray-800
          ${expanded ? 'col-span-2 row-span-2' : ''}
        `}
        style={{ borderColor: priority.borderColor }}
        onClick={() => {
          setExpanded(!expanded);
          if (!expanded) {
            setSelectedInsight(insight);
          }
        }}
      >
        {/* Priority indicator */}
        <div className={`absolute top-2 right-2 w-3 h-3 rounded-full ${priority.color}`} />
        
        {/* Category header */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">{category.icon}</span>
          <span 
            className="text-xs font-medium px-2 py-1 rounded-full"
            style={{ 
              backgroundColor: category.bgColor,
              color: category.color 
            }}
          >
            {category.label}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {priority.label}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
          {insight.title}
        </h3>

        {/* Content */}
        <div className="text-sm text-gray-600 dark:text-gray-300">
          {expanded ? (
            <div className="space-y-3">
              <p>{insight.content}</p>
              
              {/* Related files */}
              {insight.relatedFiles && insight.relatedFiles.length > 0 && (
                <div className="mt-3">
                  <h4 className="font-medium text-xs text-gray-700 dark:text-gray-400 mb-1">
                    Related Files:
                  </h4>
                  <div className="flex flex-wrap gap-1">
                    {insight.relatedFiles.map((file, idx) => (
                      <span 
                        key={idx}
                        className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded"
                      >
                        {file.split('/').pop()}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence */}
              {insight.evidence?.reasoning && (
                <div className="mt-3">
                  <h4 className="font-medium text-xs text-gray-700 dark:text-gray-400 mb-1">
                    Why this matters:
                  </h4>
                  <p className="text-xs italic text-gray-600 dark:text-gray-400">
                    {insight.evidence.reasoning}
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    dismissInsight(insight.id);
                  }}
                  className="text-xs px-3 py-1 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-800"
                >
                  Dismiss
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    archiveInsight(insight.id);
                  }}
                  className="text-xs px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
                >
                  Archive
                </button>
              </div>
            </div>
          ) : (
            <p className="line-clamp-3">{insight.content}</p>
          )}
        </div>

        {/* Timestamp */}
        <div className="text-xs text-gray-400 dark:text-gray-500 mt-2">
          {new Date(insight.timestamp).toLocaleString()}
          {insight.generatedByAgent && ` • Generated by ${insight.generatedByAgent}`}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Analyzing patterns and generating insights...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-700 dark:text-red-300">{error}</p>
        <button 
          onClick={loadInsights}
          className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Insights
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Contextual observations powered by Claude Agent SDK
          </p>
        </div>
        <button
          onClick={generateInsights}
          disabled={generating || loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {generating ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Generating...</span>
            </>
          ) : (
            <span>Generate Insights</span>
          )}
        </button>
      </div>

      {/* Filters Component */}
      <InsightFilters
        filter={filter}
        setFilter={setFilter}
        timeRange={timeRange}
        setTimeRange={setTimeRange}
        includeDismissed={includeDismissed}
        setIncludeDismissed={setIncludeDismissed}
        insights={insights}
        categoryConfig={CATEGORY_CONFIG}
      />

      {/* Selected Insight Evidence */}
      {selectedInsight && (
        <InsightEvidence
          evidence={selectedInsight.evidence || {}}
          onClose={() => setSelectedInsight(null)}
        />
      )}

      {/* Insights Grid */}
      {filteredInsights.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">🔍</div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No insights found
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {filter === 'all' 
              ? 'No insights found. Click "Generate Insights" to create new insights using AI analysis.'
              : `No ${CATEGORY_CONFIG[filter as keyof typeof CATEGORY_CONFIG]?.label.toLowerCase()} insights in this time range.`
            }
          </p>
          {filter === 'all' && (
            <button
              onClick={generateInsights}
              disabled={generating || loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 mx-auto"
            >
              {generating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Generating...</span>
                </>
              ) : (
                <span>Generate Insights</span>
              )}
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-auto">
          {filteredInsights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </div>
  );
};

export default Insights;