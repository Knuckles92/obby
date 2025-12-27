/**
 * ActivityMetricsSection - Displays activity metrics insight cards
 *
 * Extracted from MasonryLayout to be reusable in the Metrics page.
 * Shows file activity and development metrics using insight cards.
 */

import React from 'react';
import { AlertCircle } from 'lucide-react';
import InsightCard from '../insights/InsightCard';
import { useInsights } from '../../hooks/useInsights';

interface ActivityMetricsSectionProps {
  dateRange: {
    start: string;
    end: string;
    days?: number;
  };
  onOpenNote?: (path: string, insightId?: number) => void;
  onRefetchReady?: (refetch: () => void) => void;
}

export default function ActivityMetricsSection({ dateRange, onOpenNote, onRefetchReady }: ActivityMetricsSectionProps) {
  const { insights, loading, error, refetch } = useInsights({
    layoutName: 'masonry',
    dateRange
  });

  // Expose refetch function to parent if callback provided
  React.useEffect(() => {
    if (onRefetchReady) {
      onRefetchReady(refetch);
    }
  }, [onRefetchReady, refetch]);

  // Convert insights object to sorted array
  const insightArray = Object.values(insights).sort((a, b) => {
    // Sort by position if available in config, otherwise maintain order
    return 0;
  });

  return (
    <div>
      {/* Activity Metrics Header */}
      <div className="mb-4">
        <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
          Activity Metrics
        </h2>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          File activity and development metrics
        </p>
      </div>

      {/* Loading State */}
      {loading && insightArray.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle size={32} className="animate-pulse mx-auto mb-4" style={{ color: 'var(--color-primary)' }} />
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Loading metrics...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div
          className="p-4 rounded-lg flex items-start gap-3 mb-6"
          style={{
            backgroundColor: 'var(--color-error)20',
            border: '1px solid var(--color-error)',
            color: 'var(--color-error)'
          }}
        >
          <AlertCircle size={20} />
          <div>
            <p className="font-semibold">Error Loading Metrics</p>
            <p className="text-sm mt-1">{error}</p>
            <button
              onClick={refetch}
              className="mt-2 px-3 py-1 rounded text-sm"
              style={{
                backgroundColor: 'var(--color-error)',
                color: 'white'
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Insights Grid */}
      {insightArray.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {insightArray.map((insight) => (
            <InsightCard
              key={insight.metadata.id}
              insight={insight}
              size="medium"
              onOpenNote={onOpenNote}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && insightArray.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle size={48} className="mx-auto mb-4" style={{ color: 'var(--color-text-secondary)' }} />
            <p className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
              No Metrics Available
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              No data found for the selected time range.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

