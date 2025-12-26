/**
 * useActionExecution Hook
 *
 * Hook to execute an action and connect to SSE for progress updates.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { AgentAction, AgentActionType } from './types';

interface UseActionExecutionResult {
  actions: AgentAction[];
  loading: boolean;
  error: string | null;
  result: string | null;  // The final result text from the completed action
  execute: (insightId: number, actionText: string) => Promise<string | null>; // Returns execution_id or null
  disconnect: () => void;
}

export const useActionExecution = (): UseActionExecutionResult => {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const executionIdRef = useRef<string | null>(null);

  const recordAction = useCallback((
    type: AgentActionType,
    label: string,
    detail: string | null = null,
    executionId?: string
  ) => {
    const action: AgentAction = {
      id: `${Date.now()}-${Math.random()}`,
      type,
      label,
      detail: detail || undefined,
      timestamp: new Date().toISOString(),
      sessionId: executionId
    };
    setActions(prev => [...prev, action]);
  }, []);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    executionIdRef.current = null;
    setLoading(false);
  }, []);

  const execute = useCallback(async (insightId: number, actionText: string): Promise<string | null> => {
    // Clear previous state
    setActions([]);
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      // Start execution
      const response = await fetch(`/api/semantic-insights/${insightId}/execute-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action_text: actionText })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to start action execution');
      }

      const executionId = data.execution_id;
      executionIdRef.current = executionId;

      // Connect to SSE for progress updates
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(`/api/semantic-insights/execute-action/${executionId}/progress`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        recordAction('progress', 'Connected to action execution progress', null, executionId);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventType = data.type;

          if (!eventType || eventType === 'keepalive') {
            return;
          }

          if (eventType === 'connected') {
            recordAction('progress', data.message || 'Connected', null, executionId);
            return;
          }

          let actionType: AgentActionType = 'progress';
          if (eventType === 'tool_call') {
            actionType = 'tool_call';
          } else if (eventType === 'tool_result') {
            actionType = 'tool_result';
          } else if (eventType === 'error') {
            actionType = 'error';
            setError(data.message || 'An error occurred');
          } else if (eventType === 'warning') {
            actionType = 'warning';
          } else if (eventType === 'completed') {
            actionType = 'progress';
            setLoading(false);
            // Capture the result for display
            if (data.result) {
              setResult(data.result);
            }
          } else if (eventType === 'started' || eventType === 'progress') {
            actionType = 'progress';
          }

          const detail = data.result || data.tool || data.message || null;
          const label = data.message || eventType;
          recordAction(actionType, label, detail, executionId);
        } catch (eventError) {
          console.error('Error parsing action progress SSE message:', eventError);
          recordAction('warning', 'Failed to parse update', String(eventError), executionId);
        }
      };

      eventSource.onerror = (err) => {
        console.error('Action execution SSE connection error:', err);
        recordAction('warning', 'Connection interrupted', null, executionId);
        if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
          disconnect();
        }
      };

      return executionId;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      setLoading(false);
      console.error('Error executing action:', err);
      return null;
    }
  }, [recordAction, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    actions,
    loading,
    error,
    result,
    execute,
    disconnect
  };
};

export default useActionExecution;
