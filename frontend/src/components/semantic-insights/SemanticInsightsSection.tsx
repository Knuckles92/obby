/**
 * SemanticInsightsSection - Section displaying AI-powered semantic insights
 *
 * Shows stale todos, orphan mentions, and other semantic insights
 * with actions and processing controls.
 */

import React, { useMemo } from 'react';
import { Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import SemanticInsightCard from './SemanticInsightCard';
import { useSemanticInsights, useBatchSuggestedActions } from '../../hooks/useInsights';

interface SemanticInsightsSectionProps {
  onOpenNote?: (notePath: string, insightId?: number) => void;
  displayLimit: number;
  onClearInsights: () => Promise<void>;
  onIncrementalScan: () => Promise<void>;
  onFullScan: () => Promise<void>;
  isClearingInsights: boolean;
  isIncrementalScanning: boolean;
  isFullScanning: boolean;
  isAnyProcessing: boolean;
  visibleInsightsCount: number;
  onRefetch: () => Promise<void>;
}

export default function SemanticInsightsSection({ 
  onOpenNote,
  displayLimit,
  onClearInsights,
  onIncrementalScan,
  onFullScan,
  isClearingInsights,
  isIncrementalScanning,
  isFullScanning,
  isAnyProcessing,
  visibleInsightsCount,
  onRefetch
}: SemanticInsightsSectionProps) {
  const {
    insights,
    loading,
    error,
    meta,
    performAction
  } = useSemanticInsights({ status: undefined, limit: displayLimit });

  // Filter to only show new, viewed, and pinned insights
  const visibleInsights = insights.filter(
    i => ['new', 'viewed', 'pinned'].includes(i.status)
  );

  // Collect IDs of todo-type insights for batch suggested actions fetch
  const todoInsightIds = useMemo(() => {
    return visibleInsights
      .filter(i => i.type === 'stale_todo' || i.type === 'active_todos')
      .map(i => i.id);
  }, [visibleInsights]);

  // Batch fetch suggested actions for all todo insights at once
  const { actionsMap: suggestedActionsMap } = useBatchSuggestedActions(
    todoInsightIds,
    todoInsightIds.length > 0
  );

  const handleAction = async (insightId: number, action: string) => {
    const result = await performAction(insightId, action);
    await onRefetch();
    return result;
  };

  return (
    <div className="mb-8">

      {/* Error State */}
      {error && (
        <div
          className="p-4 rounded-lg flex items-start gap-3 mb-4"
          style={{
            backgroundColor: 'var(--color-error)20',
            border: '1px solid var(--color-error)',
            color: 'var(--color-error)'
          }}
        >
          <AlertCircle size={20} />
          <div>
            <p className="font-semibold">Error Loading Insights</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && visibleInsights.length === 0 && (
        <div
          className="p-6 rounded-lg text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)'
          }}
        >
          <RefreshCw
            size={24}
            className="animate-spin mx-auto mb-2"
            style={{ color: 'var(--color-primary)' }}
          />
          <p style={{ color: 'var(--color-text-secondary)' }}>
            Loading semantic insights...
          </p>
        </div>
      )}

      {/* Insights Grid */}
      {visibleInsights.length > 0 && (
        <div 
          className="grid gap-4"
          style={{
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))'
          }}
        >
          {visibleInsights.map((insight) => (
            <SemanticInsightCard
              key={insight.id}
              insight={insight}
              onAction={handleAction}
              onOpenNote={onOpenNote}
              suggestedActions={suggestedActionsMap[insight.id]}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && visibleInsights.length === 0 && (
        <div
          className="p-8 rounded-lg text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)'
          }}
        >
          <Sparkles
            size={32}
            className="mx-auto mb-3"
            style={{ color: 'var(--color-text-secondary)' }}
          />
          <p
            className="font-semibold mb-1"
            style={{ color: 'var(--color-text-primary)' }}
          >
            No Semantic Insights Yet
          </p>
          <p
            className="text-sm mb-4"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Click "Analyze Notes" to scan your vault for stale todos, orphaned mentions, and more.
          </p>
          <button
            onClick={onFullScan}
            disabled={isAnyProcessing}
            className="px-4 py-2 rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-primary)',
              color: 'var(--color-text-inverse)'
            }}
          >
            {isFullScanning ? 'Analyzing...' : 'Analyze Notes'}
          </button>
        </div>
      )}

      {/* Stats Footer */}
      {meta && (meta.byType && Object.keys(meta.byType).length > 0) && (
        <div
          className="mt-4 pt-4 flex items-center gap-4 text-xs"
          style={{
            borderTop: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)'
          }}
        >
          {Object.entries(meta.byType).map(([type, count]) => (
            <span key={type}>
              {type.replace('_', ' ')}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
