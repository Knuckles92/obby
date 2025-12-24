import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Zap, MessageSquare, ArrowRight, Loader2, CheckCircle2, Trash2 } from 'lucide-react';
import BaseModal from '../BaseModal';
import ActivityTimeline from '../ActivityTimeline';
import { useActionExecution } from '../../hooks/useInsights';

interface ActionSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  insightId: number;
  actionText: string;
  actionDescription?: string;
  onRemoveInsight?: () => Promise<void>;
}

export default function ActionSelectionModal({
  isOpen,
  onClose,
  insightId,
  actionText,
  actionDescription,
  onRemoveInsight
}: ActionSelectionModalProps) {
  const navigate = useNavigate();
  const [executionMode, setExecutionMode] = useState<'idle' | 'executing' | 'completed'>('idle');
  const [timelineExpanded, setTimelineExpanded] = useState(true);
  const [isRemoving, setIsRemoving] = useState(false);
  const { actions, error, execute, disconnect } = useActionExecution();

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setExecutionMode('idle');
      disconnect();
    }
  }, [isOpen, disconnect]);

  // Monitor for completion
  useEffect(() => {
    if (executionMode === 'executing') {
      const completed = actions.some(a =>
        a.type === 'progress' &&
        a.label.toLowerCase().includes('completed')
      );

      if (completed) {
        setExecutionMode('completed');
      }
    }
  }, [actions, executionMode]);

  const handleCompleteInPopup = async () => {
    setExecutionMode('executing');
    const executionId = await execute(insightId, actionText);

    if (!executionId) {
      setExecutionMode('idle');
      return;
    }
  };

  const handleBringToChat = () => {
    onClose();
    navigate('/chat', { state: { initialMessage: actionText } });
  };

  const handleClose = () => {
    if (executionMode === 'executing') {
      if (window.confirm('Action execution is in progress. Close anyway?')) {
        disconnect();
        setExecutionMode('idle');
        onClose();
      }
    } else {
      disconnect();
      setExecutionMode('idle');
      onClose();
    }
  };

  const handleRemoveInsight = async () => {
    if (onRemoveInsight) {
      setIsRemoving(true);
      await onRemoveInsight();
      setIsRemoving(false);
    }
    handleClose();
  };

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Execute suggested action"
      maxWidth="max-w-xl"
    >
      <div className="flex flex-col h-full overflow-hidden">
        <div className="p-6 space-y-6">
          {/* Action Header / Preview */}
          <div className="relative overflow-hidden p-5 rounded-2xl bg-gradient-to-br from-primary/10 via-background to-background border border-border/50 shadow-sm">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Zap size={64} className="text-primary" />
            </div>
            <div className="relative z-10">
              <div className="text-[10px] font-bold uppercase tracking-wider text-primary mb-2 opacity-80">
                Suggested Action
              </div>
              <p className="text-lg font-semibold leading-snug tracking-tight text-text-primary">
                {actionText}
              </p>
              {actionDescription && (
                <p className="mt-2 text-sm text-text-secondary leading-relaxed">
                  {actionDescription}
                </p>
              )}
            </div>
          </div>

          {/* Options Section */}
          {executionMode === 'idle' && (
            <div className="space-y-3">
              <button
                onClick={handleCompleteInPopup}
                className="group w-full flex items-center gap-4 p-4 rounded-xl transition-all duration-200 border border-border hover:border-primary/50 hover:bg-primary/5 bg-surface shadow-sm hover:shadow-md text-left"
              >
                <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform duration-200">
                  <Zap size={24} />
                </div>
                <div className="flex-grow">
                  <div className="font-bold text-text-primary group-hover:text-primary transition-colors">
                    Complete in popup
                  </div>
                  <div className="text-xs text-text-secondary">
                    AI executes automatically with real-time feedback
                  </div>
                </div>
                <ArrowRight size={18} className="text-text-secondary group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </button>

              <button
                onClick={handleBringToChat}
                className="group w-full flex items-center gap-4 p-4 rounded-xl transition-all duration-200 border border-border hover:border-primary/50 hover:bg-primary/5 bg-surface shadow-sm hover:shadow-md text-left"
              >
                <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform duration-200">
                  <MessageSquare size={24} />
                </div>
                <div className="flex-grow">
                  <div className="font-bold text-text-primary group-hover:text-primary transition-colors">
                    Bring to chat
                  </div>
                  <div className="text-xs text-text-secondary">
                    Collaborate with the AI in the main chat interface
                  </div>
                </div>
                <ArrowRight size={18} className="text-text-secondary group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </button>
            </div>
          )}

          {/* Execution Progress */}
          {(executionMode === 'executing' || executionMode === 'completed') && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {executionMode === 'executing' ? (
                    <Loader2 size={16} className="text-primary animate-spin" />
                  ) : (
                    <CheckCircle2 size={16} style={{ color: 'var(--color-success)' }} />
                  )}
                  <h3 className="text-sm font-bold text-text-primary uppercase tracking-wide">
                    {executionMode === 'executing' ? 'Executing Action...' : 'Action Completed'}
                  </h3>
                </div>
                {executionMode === 'completed' && (
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--color-success)1a',
                      color: 'var(--color-success)',
                      border: '1px solid var(--color-success)33'
                    }}
                  >
                    FINISHED
                  </span>
                )}
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/20 text-error text-xs flex gap-2 items-center">
                  <X size={14} />
                  {error}
                </div>
              )}

              <div className="rounded-xl border border-border bg-background/50 overflow-hidden">
                <ActivityTimeline
                  actions={actions}
                  isExpanded={timelineExpanded}
                  onToggle={() => setTimelineExpanded(!timelineExpanded)}
                  maxHeight="320px"
                />
              </div>

              {executionMode === 'completed' && (
                <div className="pt-6 space-y-4">
                  <p className="text-sm text-text-secondary text-center">
                    Would you like to remove this insight?
                  </p>
                  <div className="flex justify-center gap-3">
                    <button
                      onClick={handleClose}
                      className="px-5 py-2.5 rounded-xl border border-border bg-surface text-text-primary font-medium text-sm hover:bg-surface-hover transition-all"
                    >
                      Keep Insight
                    </button>
                    <button
                      onClick={handleRemoveInsight}
                      disabled={isRemoving}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-white font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{
                        backgroundColor: 'var(--color-success)',
                        boxShadow: '0 10px 15px -3px var(--color-success)33'
                      }}
                    >
                      {isRemoving ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                      Remove Insight
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </BaseModal>
  );
}

