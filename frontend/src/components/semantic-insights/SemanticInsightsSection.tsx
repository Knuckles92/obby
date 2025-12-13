/**
 * SemanticInsightsSection - Section displaying AI-powered semantic insights
 *
 * Shows stale todos, orphan mentions, and other semantic insights
 * with actions and processing controls.
 */

import React, { useState } from 'react';
import { Sparkles, RefreshCw, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import SemanticInsightCard from './SemanticInsightCard';
import { useSemanticInsights, type SemanticInsight } from '../../hooks/useInsights';

interface SemanticInsightsSectionProps {
  onOpenNote?: (notePath: string) => void;
}

export default function SemanticInsightsSection({ onOpenNote }: SemanticInsightsSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);

  const {
    insights,
    loading,
    error,
    meta,
    refetch,
    performAction,
    triggerProcessing
  } = useSemanticInsights({ status: undefined }); // Get all non-dismissed insights

  // Filter to only show new, viewed, and pinned insights
  const visibleInsights = insights.filter(
    i => ['new', 'viewed', 'pinned'].includes(i.status)
  );

  const newCount = meta?.byStatus?.new || 0;

  const handleTriggerProcessing = async () => {
    setIsProcessing(true);
    await triggerProcessing();
    setIsProcessing(false);
  };

  const handleAction = async (insightId: number, action: string) => {
    return await performAction(insightId, action);
  };

  if (!isExpanded) {
    return (
      <div
        className="mb-6 p-4 rounded-lg cursor-pointer transition-colors hover:opacity-90"
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)'
        }}
        onClick={() => setIsExpanded(true)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Sparkles size={20} style={{ color: 'var(--color-primary)' }} />
            <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Semantic Insights
            </span>
            {newCount > 0 && (
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  backgroundColor: 'var(--color-primary)',
                  color: 'white'
                }}
              >
                {newCount} new
              </span>
            )}
          </div>
          <ChevronDown size={20} style={{ color: 'var(--color-text-secondary)' }} />
        </div>
      </div>
    );
  }

  return (
    <div className="mb-8">
      {/* Section Header */}
      <div className="flex items-center justify-between mb-4">
        <div
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => setIsExpanded(false)}
        >
          <Sparkles size={24} style={{ color: 'var(--color-primary)' }} />
          <div>
            <div className="flex items-center gap-2">
              <h2
                className="text-xl font-bold"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Semantic Insights
              </h2>
              {newCount > 0 && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: 'white'
                  }}
                >
                  {newCount} new
                </span>
              )}
            </div>
            <p
              className="text-sm"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              AI-powered insights from your notes
            </p>
          </div>
          <ChevronUp size={20} style={{ color: 'var(--color-text-secondary)' }} />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerProcessing}
            disabled={isProcessing}
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-surface)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)'
            }}
          >
            <RefreshCw size={14} className={isProcessing ? 'animate-spin' : ''} />
            {isProcessing ? 'Processing...' : 'Analyze Notes'}
          </button>
          <button
            onClick={refetch}
            disabled={loading}
            className="p-2 rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)'
            }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

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
      {!loading && visibleInsights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleInsights.map((insight) => (
            <SemanticInsightCard
              key={insight.id}
              insight={insight}
              onAction={handleAction}
              onOpenNote={onOpenNote}
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
            onClick={handleTriggerProcessing}
            disabled={isProcessing}
            className="px-4 py-2 rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-primary)',
              color: 'white'
            }}
          >
            {isProcessing ? 'Analyzing...' : 'Analyze Notes'}
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
