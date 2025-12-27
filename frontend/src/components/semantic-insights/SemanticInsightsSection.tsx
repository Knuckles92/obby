/**
 * SemanticInsightsSection - Section displaying AI-powered semantic insights
 *
 * Shows stale todos, orphan mentions, and other semantic insights
 * with actions and processing controls.
 */

import React, { useState, useMemo } from 'react';
import { Sparkles, RefreshCw, ChevronDown, ChevronUp, AlertCircle, Trash2, FilePlus } from 'lucide-react';
import SemanticInsightCard from './SemanticInsightCard';
import { useSemanticInsights, useBatchSuggestedActions, type SemanticInsight } from '../../hooks/useInsights';

interface SemanticInsightsSectionProps {
  onOpenNote?: (notePath: string, insightId?: number) => void;
}

export default function SemanticInsightsSection({ onOpenNote }: SemanticInsightsSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [displayLimit, setDisplayLimit] = useState(6);

  // Individual loading states for each button
  const [isClearingInsights, setIsClearingInsights] = useState(false);
  const [isIncrementalScanning, setIsIncrementalScanning] = useState(false);
  const [isFullScanning, setIsFullScanning] = useState(false);

  const {
    insights,
    loading,
    error,
    meta,
    refetch,
    performAction,
    triggerProcessing,
    clearInsights,
    triggerIncrementalProcessing
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

  const newCount = meta?.byStatus?.new || 0;

  // Check if any operation is in progress
  const isAnyProcessing = isClearingInsights || isIncrementalScanning || isFullScanning;

  const handleClearInsights = async () => {
    setIsClearingInsights(true);
    await clearInsights();
    setIsClearingInsights(false);
  };

  const handleIncrementalScan = async () => {
    setIsIncrementalScanning(true);
    await triggerIncrementalProcessing();
    setIsIncrementalScanning(false);
  };

  const handleFullScan = async () => {
    setIsFullScanning(true);
    await triggerProcessing();
    setIsFullScanning(false);
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

        {/* Actions - Button Group */}
        <div className="flex items-center gap-2">
          <select
            value={displayLimit}
            onChange={(e) => setDisplayLimit(Number(e.target.value))}
            className="px-2 py-1.5 text-sm rounded-lg"
            style={{
              backgroundColor: 'var(--color-surface)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)'
            }}
          >
            <option value={6}>6 items</option>
            <option value={12}>12 items</option>
            <option value={18}>18 items</option>
            <option value={24}>24 items</option>
          </select>

          {/* Clear Insights Button */}
          <div className="relative group">
            <button
              onClick={handleClearInsights}
              disabled={isAnyProcessing || visibleInsights.length === 0}
              className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--color-error)',
                color: 'var(--color-text-inverse)',
                border: 'none'
              }}
            >
              <Trash2 size={14} className={isClearingInsights ? 'animate-pulse' : ''} />
              {isClearingInsights ? 'Clearing...' : 'Clear'}
            </button>
            <div className="absolute right-0 bottom-full mb-2 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
              <div
                className="text-xs rounded-lg px-3 py-2 shadow-xl max-w-xs break-words whitespace-normal"
                style={{
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-text-primary)',
                  border: '1px solid var(--color-border)'
                }}
              >
                <div className="font-semibold mb-1">Clear Insights</div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  Remove all non-pinned insights. Pinned insights will be preserved.
                </div>
              </div>
            </div>
          </div>

          {/* Scan for New Notes Button */}
          <div className="relative group">
            <button
              onClick={handleIncrementalScan}
              disabled={isAnyProcessing}
              className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--color-success)',
                color: 'var(--color-text-inverse)',
                border: 'none'
              }}
            >
              <FilePlus size={14} className={isIncrementalScanning ? 'animate-spin' : ''} />
              {isIncrementalScanning ? 'Scanning...' : 'Scan New'}
            </button>
            <div className="absolute right-0 bottom-full mb-2 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
              <div
                className="text-xs rounded-lg px-3 py-2 shadow-xl max-w-xs break-words whitespace-normal"
                style={{
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-text-primary)',
                  border: '1px solid var(--color-border)'
                }}
              >
                <div className="font-semibold mb-1">Scan for New Notes</div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  Process only notes that have changed since last scan. Existing insights are preserved.
                </div>
              </div>
            </div>
          </div>

          {/* Full Scan Button */}
          <div className="relative group">
            <button
              onClick={handleFullScan}
              disabled={isAnyProcessing}
              className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)',
                border: 'none'
              }}
            >
              <RefreshCw size={14} className={isFullScanning ? 'animate-spin' : ''} />
              {isFullScanning ? 'Scanning...' : 'Full Scan'}
            </button>
            <div className="absolute right-0 bottom-full mb-2 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
              <div
                className="text-xs rounded-lg px-3 py-2 shadow-xl max-w-xs break-words whitespace-normal"
                style={{
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-text-primary)',
                  border: '1px solid var(--color-border)'
                }}
              >
                <div className="font-semibold mb-1">Full Scan & Replace</div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  Scan all changed notes and replace all non-pinned insights with fresh analysis.
                </div>
              </div>
            </div>
          </div>
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
            onClick={handleFullScan}
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
