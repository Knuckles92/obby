import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../utils/api';

// Types for insights
interface Insight {
  id: string;
  category: 'action' | 'pattern' | 'relationship' | 'temporal' | 'opportunity';
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  content: string;
  relatedFiles: string[];
  evidence: {
    reasoning?: string;
    data_points?: any[];
  };
  timestamp: string;
  dismissed: boolean;
  archived: boolean;
}

interface InsightsResponse {
  success: boolean;
  data: Insight[];
  metadata: {
    time_range_days: number;
    max_insights: number;
    generated_at: string;
    total_insights: number;
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
  const { currentTheme, isDark } = useTheme();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<number>(7);

  // Load insights
  useEffect(() => {
    loadInsights();
  }, [timeRange]);

  const loadInsights = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.get<InsightsResponse>(`/api/insights?time_range_days=${timeRange}&max_insights=20`);
      
      if (response.success) {
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

  const dismissInsight = async (insightId: string) => {
    try {
      await api.post(`/api/insights/${insightId}/dismiss`);
      setInsights(insights.filter(i => i.id !== insightId));
    } catch (err) {
      console.error('Error dismissing insight:', err);
    }
  };

  const archiveInsight = async (insightId: string) => {
    try {
      await api.post(`/api/insights/${insightId}/archive`);
      setInsights(insights.filter(i => i.id !== insightId));
    } catch (err) {
      console.error('Error archiving insight:', err);
    }
  };

  const filteredInsights = insights.filter(insight => {
    if (filter === 'all') return true;
    if (filter === 'dismissed') return insight.dismissed;
    return insight.category === filter;
  });

  const InsightCard: React.FC<{ insight: Insight }> = ({ insight }) => {
    const category = CATEGORY_CONFIG[insight.category];
    const priority = PRIORITY_CONFIG[insight.priority];
    const [expanded, setExpanded] = useState(false);

    return (
      <div
        className={`relative p-4 rounded-lg border-2 transition-all duration-200 hover:shadow-lg cursor-pointer
          ${priority.borderColor} bg-white dark:bg-gray-800
          ${expanded ? 'col-span-2 row-span-2' : ''}
        `}
        onClick={() => setExpanded(!expanded)}
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
              {insight.relatedFiles.length > 0 && (
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
          onClick={loadInsights}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Refresh Insights
        </button>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-4 items-center">
        {/* Filter */}
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              filter === 'all' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            All ({insights.length})
          </button>
          {Object.entries(CATEGORY_CONFIG).map(([key, config]) => {
            const count = insights.filter(i => i.category === key).length;
            return (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1 rounded-full text-sm transition-colors flex items-center gap-1 ${
                  filter === key 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                }`}
              >
                {config.icon} {config.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Time range */}
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(Number(e.target.value))}
          className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800"
        >
          <option value={3}>Last 3 days</option>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {/* Insights Grid */}
      {filteredInsights.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">🔍</div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No insights found
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {filter === 'all' 
              ? 'Try adjusting the time range or generating new insights.'
              : `No ${CATEGORY_CONFIG[filter as keyof typeof CATEGORY_CONFIG]?.label.toLowerCase()} insights in this time range.`
            }
          </p>
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