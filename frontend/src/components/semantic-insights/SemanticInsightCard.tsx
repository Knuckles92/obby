/**
 * SemanticInsightCard - Displays individual semantic insights with actions
 *
 * Shows AI-generated insights like stale todos and orphan mentions
 * with action buttons for dismiss, pin, mark done, etc.
 */

import React, { useState } from 'react';
import {
  Clock,
  UserX,
  Link2,
  X,
  Pin,
  CheckCircle,
  ExternalLink,
  RotateCcw,
  Sparkles,
  Lightbulb,
  HelpCircle,
  AlertCircle,
  TrendingUp,
  MessageSquare
} from 'lucide-react';
import type { SemanticInsight, SuggestedAction, ContextSpecificAction } from '../../hooks/useInsights';
import ActionSelectionModal from './ActionSelectionModal';
import SuggestedActionButton from './SuggestedActionButton';

interface SemanticInsightCardProps {
  insight: SemanticInsight;
  onAction: (insightId: number, action: string) => Promise<boolean>;
  onOpenNote?: (notePath: string, insightId?: number) => void;
  /** Pre-fetched suggested actions from batch request */
  suggestedActions?: SuggestedAction[];
}

// Map insight types to icons and colors
const typeConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  stale_todo: {
    icon: Clock,
    color: 'var(--color-amber, #f59e0b)',
    label: 'Stale Todo'
  },
  active_todos: {
    icon: CheckCircle,
    color: 'var(--color-blue, #3b82f6)',
    label: 'Active Todo'
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

// Map insight categories to icons and colors
const categoryConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  immediate_action: {
    icon: AlertCircle,
    color: 'var(--color-error, #ef4444)',
    label: 'Needs Attention'
  },
  trend: {
    icon: TrendingUp,
    color: 'var(--color-blue, #3b82f6)',
    label: 'Trend'
  },
  recommendation: {
    icon: Lightbulb,
    color: 'var(--color-amber, #f59e0b)',
    label: 'Recommendation'
  },
  observation: {
    icon: MessageSquare,
    color: 'var(--color-text-secondary)',
    label: 'Observation'
  }
};

export default function SemanticInsightCard({
  insight,
  onAction,
  onOpenNote,
  suggestedActions = []
}: SemanticInsightCardProps) {
  const [selectedAction, setSelectedAction] = useState<{ text: string; description: string } | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const config = typeConfig[insight.type] || {
    icon: Sparkles,
    color: 'var(--color-primary)',
    label: insight.type
  };
  const Icon = config.icon;

  // Check if this is a todo-type insight (for showing suggested actions)
  const isTodoType = insight.type === 'stale_todo' || insight.type === 'active_todos';

  const handleAction = async (action: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await onAction(insight.id, action);
  };

  const handleOpenNote = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (insight.sourceNotes.length > 0 && onOpenNote) {
      onOpenNote(insight.sourceNotes[0].path, insight.id);
    }
  };

  const handleSuggestedActionClick = (action: { text: string; description: string }, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedAction(action);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedAction(null);
  };

  const handleRemoveInsight = async () => {
    await onAction(insight.id, 'mark_done');
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
      className={`rounded-lg p-4 transition-all hover:shadow-md ${insight.status === 'pinned' ? 'ring-2' : ''
        }`}
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: insight.status === 'pinned' ? `0 0 0 2px ${config.color}` : undefined
      }}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 sm:gap-3 mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div
            className="p-2 rounded-lg flex-shrink-0"
            style={{ backgroundColor: `${config.color}20` }}
          >
            <Icon size={18} style={{ color: config.color }} />
          </div>
          {insight.status === 'new' && (
            <span
              className="text-xs px-2 py-0.5 rounded-full flex-shrink-0 whitespace-nowrap"
              style={{
                backgroundColor: 'var(--color-primary)',
                color: 'white'
              }}
            >
              New
            </span>
          )}
          {insight.status === 'pinned' && (
            <Pin size={14} style={{ color: config.color }} className="flex-shrink-0" />
          )}
          <h3
            className="font-semibold flex-1 min-w-0"
            style={{ 
              color: 'var(--color-text-primary)',
              wordBreak: 'normal',
              overflowWrap: 'break-word',
              hyphens: 'auto'
            }}
          >
            {insight.title}
          </h3>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-1 flex-shrink-0 self-start sm:self-auto">
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

      {/* Category Badge for immediate_action */}
      {insight.category === 'immediate_action' && (
        <div
          className="flex items-center gap-1 mb-2 px-2 py-1 rounded-md w-fit"
          style={{ backgroundColor: `${categoryConfig.immediate_action.color}15` }}
        >
          <AlertCircle size={12} style={{ color: categoryConfig.immediate_action.color }} />
          <span
            className="text-xs font-medium"
            style={{ color: categoryConfig.immediate_action.color }}
          >
            Needs Attention
          </span>
        </div>
      )}

      {/* Summary */}
      <p
        className="text-sm mb-3"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        {insight.summary}
      </p>

      {/* Reasoning Section - Why This Matters */}
      {insight.reasoning && (
        <div
          className="mb-3 p-3 rounded-lg"
          style={{ backgroundColor: 'var(--color-background)' }}
        >
          <div className="flex items-center gap-1 mb-1">
            <HelpCircle size={12} style={{ color: 'var(--color-primary)' }} />
            <span
              className="text-xs font-medium"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Why this matters
            </span>
          </div>
          <p
            className="text-sm"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {insight.reasoning}
          </p>
        </div>
      )}

      {/* Context-Specific Actions (new AI-generated actions with rationale) */}
      {insight.contextSpecificActions && insight.contextSpecificActions.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-1 mb-2">
            <Lightbulb size={12} style={{ color: 'var(--color-primary)' }} />
            <span
              className="text-xs font-medium"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Suggested Next Steps
            </span>
          </div>
          <div className="space-y-2">
            {insight.contextSpecificActions.map((action, index) => (
              <button
                key={index}
                type="button"
                onClick={(e) => handleSuggestedActionClick({ text: action.text, description: action.rationale }, e)}
                className="w-full text-left p-2 rounded-lg transition-colors hover:opacity-90"
                style={{
                  backgroundColor: `${config.color}10`,
                  border: `1px solid ${config.color}30`
                }}
              >
                <div
                  className="font-medium text-sm"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {action.text}
                </div>
                {action.rationale && (
                  <div
                    className="text-xs mt-1"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {action.rationale}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Legacy Suggested Actions (fallback for old insights) */}
      {isTodoType && suggestedActions.length > 0 && (!insight.contextSpecificActions || insight.contextSpecificActions.length === 0) && (
        <div className="mb-3">
          <div className="flex items-center gap-1 mb-2">
            <Lightbulb size={12} style={{ color: 'var(--color-text-secondary)' }} />
            <span
              className="text-xs font-medium"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Suggested Actions
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestedActions.map((action, index) => (
              <SuggestedActionButton
                key={index}
                action={action}
                color={config.color}
                onClick={handleSuggestedActionClick}
              />
            ))}
          </div>
        </div>
      )}

      {/* Action Selection Modal */}
      {selectedAction && (
        <ActionSelectionModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          insightId={insight.id}
          actionText={selectedAction.text}
          actionDescription={selectedAction.description}
          onRemoveInsight={handleRemoveInsight}
        />
      )}

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
