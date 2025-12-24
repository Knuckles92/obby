/**
 * ActionSelectionModal - Modal for selecting how to execute a suggested action
 *
 * Shows two options:
 * 1. Complete in popup - Auto-executes with ActivityTimeline
 * 2. Bring to chat - Navigates to chat with pre-filled message
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Zap, MessageSquare } from 'lucide-react';
import BaseModal from '../BaseModal';
import ActivityTimeline from '../ActivityTimeline';
import { useActionExecution, type AgentAction } from '../../hooks/useInsights';

interface ActionSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  insightId: number;
  actionText: string;
  actionDescription?: string;
}

export default function ActionSelectionModal({
  isOpen,
  onClose,
  insightId,
  actionText,
  actionDescription
}: ActionSelectionModalProps) {
  const navigate = useNavigate();
  const [executionMode, setExecutionMode] = useState<'idle' | 'executing' | 'completed'>('idle');
  const [timelineExpanded, setTimelineExpanded] = useState(true);
  const { actions, loading, error, execute, disconnect } = useActionExecution();

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setExecutionMode('idle');
      disconnect();
    }
  }, [isOpen, disconnect]);

  const handleCompleteInPopup = async () => {
    setExecutionMode('executing');
    const executionId = await execute(insightId, actionText);
    
    if (!executionId) {
      setExecutionMode('idle');
      return;
    }

    // Monitor for completion via useEffect
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
  };

  const handleBringToChat = () => {
    onClose();
    navigate('/chat', { state: { initialMessage: actionText } });
  };

  const handleClose = () => {
    if (executionMode === 'executing') {
      // Ask for confirmation if execution is in progress
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

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Execute Action"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-4">
        {/* Action Preview */}
        <div
          className="p-3 rounded-lg"
          style={{
            backgroundColor: 'var(--color-background)',
            border: '1px solid var(--color-border)'
          }}
        >
          <p
            className="text-sm font-medium mb-1"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {actionText}
          </p>
          {actionDescription && (
            <p
              className="text-xs"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {actionDescription}
            </p>
          )}
        </div>

        {/* Options (only show if not executing) */}
        {executionMode === 'idle' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button
              onClick={handleCompleteInPopup}
              className="flex flex-col items-center gap-2 p-4 rounded-lg transition-all hover:shadow-md"
              style={{
                backgroundColor: 'var(--color-surface)',
                border: '2px solid var(--color-border)',
                color: 'var(--color-text-primary)'
              }}
            >
              <div
                className="p-3 rounded-full"
                style={{ backgroundColor: 'var(--color-primary)20' }}
              >
                <Zap size={24} style={{ color: 'var(--color-primary)' }} />
              </div>
              <div className="text-center">
                <div className="font-semibold mb-1">Complete in popup</div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  AI executes automatically with progress shown here
                </div>
              </div>
            </button>

            <button
              onClick={handleBringToChat}
              className="flex flex-col items-center gap-2 p-4 rounded-lg transition-all hover:shadow-md"
              style={{
                backgroundColor: 'var(--color-surface)',
                border: '2px solid var(--color-border)',
                color: 'var(--color-text-primary)'
              }}
            >
              <div
                className="p-3 rounded-full"
                style={{ backgroundColor: 'var(--color-primary)20' }}
              >
                <MessageSquare size={24} style={{ color: 'var(--color-primary)' }} />
              </div>
              <div className="text-center">
                <div className="font-semibold mb-1">Bring to chat</div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  Open chat with this action pre-filled
                </div>
              </div>
            </button>
          </div>
        )}

        {/* Activity Timeline (show when executing or completed) */}
        {(executionMode === 'executing' || executionMode === 'completed') && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3
                className="text-sm font-semibold"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Execution Progress
              </h3>
              {executionMode === 'completed' && (
                <span
                  className="text-xs px-2 py-1 rounded-full"
                  style={{
                    backgroundColor: 'var(--color-success)20',
                    color: 'var(--color-success)'
                  }}
                >
                  Completed
                </span>
              )}
            </div>

            {error && (
              <div
                className="p-3 rounded-lg text-sm"
                style={{
                  backgroundColor: 'var(--color-error)20',
                  border: '1px solid var(--color-error)',
                  color: 'var(--color-error)'
                }}
              >
                {error}
              </div>
            )}

            <ActivityTimeline
              actions={actions}
              isExpanded={timelineExpanded}
              onToggle={() => setTimelineExpanded(!timelineExpanded)}
              maxHeight="300px"
            />

            {executionMode === 'completed' && (
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: 'white'
                  }}
                >
                  Close
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </BaseModal>
  );
}

