/**
 * SemanticInsightCard - Displays individual semantic insights with actions
 *
 * Shows AI-generated insights like stale todos and orphan mentions
 * with action buttons for dismiss, pin, mark done, etc.
 */

import React from 'react';
import {
  Clock,
  UserX,
  Link2,
  X,
  Pin,
  CheckCircle,
  ExternalLink,
  RotateCcw,
  Sparkles
} from 'lucide-react';
import type { SemanticInsight } from '../../hooks/useInsights';

interface SemanticInsightCardProps {
  insight: SemanticInsight;
  onAction: (insightId: number, action: string) => Promise<boolean>;
  onOpenNote?: (notePath: string) => void;
}

// Map insight types to icons and colors
const typeConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  stale_todo: {
    icon: Clock,
    color: 'var(--color-amber, #f59e0b)',
    label: 'Stale Todo'
  },
  orphan_mention: {
    icon: UserX,
    color: 'var(--color-rose, #f43f5e)',
    label: 'Orphan Mention'
  },
  connection: {
    icon: Link2,
    color: 'var(--color-blue, #3b82f6)',
    label: 'Connection'
  },
  theme: {
    icon: Sparkles,
    color: 'var(--color-purple, #8b5cf6)',
    label: 'Theme'
  }
};

export default function SemanticInsightCard({
  insight,
  onAction,
  onOpenNote
}: SemanticInsightCardProps) {
  const config = typeConfig[insight.type] || {
    icon: Sparkles,
    color: 'var(--color-primary)',
    label: insight.type
  };
  const Icon = config.icon;

  const handleAction = async (action: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await onAction(insight.id, action);
  };

  const handleOpenNote = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (insight.sourceNotes.length > 0 && onOpenNote) {
      onOpenNote(insight.sourceNotes[0].path);
    }
  };

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  return (
    <div
      className={`rounded-lg p-4 transition-all hover:shadow-md ${
        insight.status === 'pinned' ? 'ring-2' : ''
      }`}
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        ringColor: insight.status === 'pinned' ? config.color : undefined
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div
            className="p-2 rounded-lg"
            style={{ backgroundColor: `${config.color}20` }}
          >
            <Icon size={18} style={{ color: config.color }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{
                  backgroundColor: `${config.color}20`,
                  color: config.color
                }}
              >
                {config.label}
              </span>
              {insight.status === 'new' && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: 'white'
                  }}
                >
                  New
                </span>
              )}
              {insight.status === 'pinned' && (
                <Pin size={12} style={{ color: config.color }} />
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-1">
          {insight.actions.includes('pin') && (
            <button
              type="button"
              onClick={(e) => handleAction('pin', e)}
              className="p-1.5 rounded-lg hover:bg-opacity-10 transition-colors"
              style={{ color: 'var(--color-text-secondary)' }}
              title="Pin"
            >
              <Pin size={14} />
            </button>
          )}
          {insight.actions.includes('unpin') && (
            <button
              type="button"
              onClick={(e) => handleAction('unpin', e)}
              className="p-1.5 rounded-lg hover:bg-opacity-10 transition-colors"
              style={{ color: config.color }}
              title="Unpin"
            >
              <Pin size={14} />
            </button>
          )}
          {insight.actions.includes('dismiss') && (
            <button
              type="button"
              onClick={(e) => handleAction('dismiss', e)}
              className="p-1.5 rounded-lg hover:bg-opacity-10 transition-colors"
              style={{ color: 'var(--color-text-secondary)' }}
              title="Dismiss"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Title */}
      <h3
        className="font-semibold mb-2"
        style={{ color: 'var(--color-text-primary)' }}
      >
        {insight.title}
      </h3>

      {/* Summary */}
      <p
        className="text-sm mb-3"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        {insight.summary}
      </p>

      {/* Source Note Preview */}
      {insight.sourceNotes.length > 0 && (
        <div
          className="p-2 rounded text-xs mb-3 cursor-pointer hover:opacity-80 transition-opacity"
          style={{
            backgroundColor: 'var(--color-background)',
            border: '1px solid var(--color-border)'
          }}
          onClick={handleOpenNote}
        >
          <div className="flex items-center gap-1 mb-1">
            <ExternalLink size={10} style={{ color: 'var(--color-text-secondary)' }} />
            <span style={{ color: 'var(--color-text-secondary)' }}>
              {insight.sourceNotes[0].path}
            </span>
          </div>
          {insight.sourceNotes[0].snippet && (
            <p
              className="truncate"
              style={{ color: 'var(--color-text-primary)' }}
            >
              {insight.sourceNotes[0].snippet}
            </p>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span
          className="text-xs"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {formatRelativeTime(insight.createdAt)}
        </span>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {insight.actions.includes('mark_done') && (
            <button
              type="button"
              onClick={(e) => handleAction('mark_done', e)}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors"
              style={{
                backgroundColor: 'var(--color-success)20',
                color: 'var(--color-success)'
              }}
            >
              <CheckCircle size={12} />
              Done
            </button>
          )}
          {insight.actions.includes('restore') && (
            <button
              type="button"
              onClick={(e) => handleAction('restore', e)}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors"
              style={{
                backgroundColor: 'var(--color-primary)20',
                color: 'var(--color-primary)'
              }}
            >
              <RotateCcw size={12} />
              Restore
            </button>
          )}
          {insight.actions.includes('open_note') && onOpenNote && (
            <button
              type="button"
              onClick={handleOpenNote}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors"
              style={{
                backgroundColor: 'var(--color-surface-hover)',
                color: 'var(--color-text-primary)'
              }}
            >
              <ExternalLink size={12} />
              Open
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
