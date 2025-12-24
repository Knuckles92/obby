/**
 * useInsights Hook
 *
 * Custom React hook for fetching and managing insights data from the backend.
 * Handles loading states, errors, and caching of results.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { InsightResult } from '../components/insights/InsightCard';

export interface DateRange {
  start: string;
  end: string;
  days?: number;
}

interface UseInsightsOptions {
  layoutName: string;
  dateRange: DateRange;
  enabled?: boolean;
}

interface UseInsightsResult {
  insights: Record<string, InsightResult>;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  availableInsights: any[];
}

/**
 * Hook to fetch and manage insights data
 */
export const useInsights = (options: UseInsightsOptions): UseInsightsResult => {
  const { layoutName, dateRange, enabled = true } = options;

  const [insights, setInsights] = useState<Record<string, InsightResult>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availableInsights, setAvailableInsights] = useState<any[]>([]);

  /**
   * Fetch available insights metadata
   */
  const fetchAvailableInsights = useCallback(async () => {
    try {
      const response = await fetch('/api/insights/available');
      const data = await response.json();

      if (data.success) {
        setAvailableInsights(data.insights);
      } else {
        console.error('Failed to fetch available insights:', data.error);
      }
    } catch (err) {
      console.error('Error fetching available insights:', err);
    }
  }, []);

  /**
   * Fetch insights data
   */
  const fetchInsights = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    setError(null);

    try {
      // First, get the layout configuration
      const configResponse = await fetch(`/api/insights/layout-config?layout=${layoutName}`);
      const configData = await configResponse.json();

      if (!configData.success) {
        throw new Error('Failed to fetch layout configuration');
      }

      const config = configData.config;
      const enabledInsightIds = config.insights
        .filter((i: any) => i.enabled)
        .map((i: any) => i.id);

      if (enabledInsightIds.length === 0) {
        setInsights({});
        setLoading(false);
        return;
      }

      // Build query parameters
      const params = new URLSearchParams({
        insight_ids: enabledInsightIds.join(',')
      });

      // Add date range parameters
      if (dateRange.days !== undefined) {
        params.append('days', String(dateRange.days));
      } else if (dateRange.start && dateRange.end) {
        params.append('start_date', dateRange.start);
        params.append('end_date', dateRange.end);
      }

      // Fetch insights
      const response = await fetch(`/api/insights/calculate?${params.toString()}`);
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to calculate insights');
      }

      setInsights(data.insights);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  }, [layoutName, dateRange, enabled]);

  // Fetch available insights on mount
  useEffect(() => {
    fetchAvailableInsights();
  }, [fetchAvailableInsights]);

  // Fetch insights when dependencies change
  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  return {
    insights,
    loading,
    error,
    refetch: fetchInsights,
    availableInsights
  };
};

/**
 * Hook to fetch and manage layout configuration
 */
export const useLayoutConfig = (layoutName: string) => {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/insights/layout-config?layout=${layoutName}`);
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch layout config');
      }

      setConfig(data.config);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching layout config:', err);
    } finally {
      setLoading(false);
    }
  }, [layoutName]);

  const saveConfig = useCallback(async (newConfig: any) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/insights/layout-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          layout: layoutName,
          config: newConfig
        })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to save layout config');
      }

      setConfig(newConfig);
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error saving layout config:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [layoutName]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return {
    config,
    loading,
    error,
    refetch: fetchConfig,
    saveConfig
  };
};

/**
 * Utility function to parse date range string (e.g., "7d", "30d")
 */
export const parseDateRange = (rangeString: string): DateRange => {
  const match = rangeString.match(/^(\d+)([dDwWmMyY])$/);

  if (!match) {
    // Default to 7 days if parsing fails
    return {
      start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end: new Date().toISOString().split('T')[0],
      days: 7
    };
  }

  const value = parseInt(match[1], 10);
  const unit = match[2].toLowerCase();

  let days = value;
  switch (unit) {
    case 'w':
      days = value * 7;
      break;
    case 'm':
      days = value * 30;
      break;
    case 'y':
      days = value * 365;
      break;
  }

  return {
    start: new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
    days
  };
};

export default useInsights;

/**
 * Semantic Insight types
 */
export interface SemanticInsight {
  id: number;
  type: string;
  title: string;
  summary: string;
  confidence: number;
  priority: number;
  status: string;
  sourceNotes: Array<{
    path: string;
    snippet?: string;
  }>;
  evidence: Record<string, any>;
  actions: string[];
  createdAt: string;
  viewedAt?: string;
  userAction?: string;
}

export interface SemanticInsightsResponse {
  success: boolean;
  insights: SemanticInsight[];
  meta: {
    total: number;
    limit: number;
    offset: number;
    byType: Record<string, number>;
    byStatus: Record<string, number>;
  };
}

interface UseSemanticInsightsOptions {
  type?: string;
  status?: string;
  limit?: number;
  enabled?: boolean;
}

interface UseSemanticInsightsResult {
  insights: SemanticInsight[];
  loading: boolean;
  error: string | null;
  meta: SemanticInsightsResponse['meta'] | null;
  refetch: () => void;
  performAction: (insightId: number, action: string) => Promise<boolean>;
  triggerProcessing: () => Promise<void>;
}

/**
 * Hook to fetch and manage semantic insights
 */
export const useSemanticInsights = (options: UseSemanticInsightsOptions = {}): UseSemanticInsightsResult => {
  const { type, status, limit = 50, enabled = true } = options;

  const [insights, setInsights] = useState<SemanticInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<SemanticInsightsResponse['meta'] | null>(null);

  /**
   * Fetch semantic insights
   */
  const fetchInsights = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (type) params.append('type', type);
      if (status) params.append('status', status);
      params.append('limit', String(limit));

      const response = await fetch(`/api/semantic-insights?${params.toString()}`);
      const data: SemanticInsightsResponse = await response.json();

      if (!data.success) {
        throw new Error('Failed to fetch semantic insights');
      }

      setInsights(data.insights);
      setMeta(data.meta);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching semantic insights:', err);
    } finally {
      setLoading(false);
    }
  }, [type, status, limit, enabled]);

  /**
   * Perform an action on an insight
   */
  const performAction = useCallback(async (insightId: number, action: string): Promise<boolean> => {
    // Keep track of original insights for rollback
    const originalInsights = [...insights];

    // Optimistically update the status if possible
    setInsights(prevInsights => prevInsights.map(insight => {
      if (insight.id === insightId) {
        let newStatus = insight.status;
        let newActions = [...insight.actions];

        if (action === 'pin') {
          newStatus = 'pinned';
          newActions = newActions.filter(a => a !== 'pin');
          if (!newActions.includes('unpin')) newActions.push('unpin');
        } else if (action === 'unpin') {
          newStatus = 'viewed';
          newActions = newActions.filter(a => a !== 'unpin');
          if (!newActions.includes('pin')) newActions.push('pin');
        } else if (action === 'dismiss') {
          newStatus = 'dismissed';
        } else if (action === 'mark_done') {
          newStatus = 'actioned';
        } else if (action === 'restore') {
          newStatus = 'new';
        }

        return {
          ...insight,
          status: newStatus,
          actions: newActions
        };
      }
      return insight;
    }));

    try {
      const response = await fetch(`/api/semantic-insights/${insightId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
      });

      const data = await response.json();

      if (data.success) {
        // Silently refresh the list after action to ensure consistency
        // But don't set loading to true to avoid flicker
        try {
          const params = new URLSearchParams();
          if (type) params.append('type', type);
          if (status) params.append('status', status);
          params.append('limit', String(limit));

          const refreshResponse = await fetch(`/api/semantic-insights?${params.toString()}`);
          const refreshData: SemanticInsightsResponse = await refreshResponse.json();

          if (refreshData.success) {
            setInsights(refreshData.insights);
            setMeta(refreshData.meta);
          }
        } catch (refreshErr) {
          console.error('Silent refresh failed:', refreshErr);
        }
        return true;
      }

      // Rollback on failure
      setInsights(originalInsights);
      console.error('Action failed:', data.error);
      return false;
    } catch (err) {
      // Rollback on error
      setInsights(originalInsights);
      console.error('Error performing action:', err);
      return false;
    }
  }, [insights, type, status, limit, fetchInsights]);

  /**
   * Trigger semantic processing
   */
  const triggerProcessing = useCallback(async () => {
    try {
      const response = await fetch('/api/semantic-insights/trigger', {
        method: 'POST'
      });

      const data = await response.json();

      if (data.success) {
        // Refresh insights after processing
        await fetchInsights();
      } else {
        console.error('Processing trigger failed:', data.error);
      }
    } catch (err) {
      console.error('Error triggering processing:', err);
    }
  }, [fetchInsights]);

  // Fetch insights on mount and when dependencies change
  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  return {
    insights,
    loading,
    error,
    meta,
    refetch: fetchInsights,
    performAction,
    triggerProcessing
  };
};

/**
 * Hook to fetch suggested actions for a todo insight
 */
export interface SuggestedAction {
  text: string;
  description: string;
}

interface UseSuggestedActionsResult {
  actions: SuggestedAction[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useSuggestedActions = (insightId: number, enabled: boolean = true): UseSuggestedActionsResult => {
  const [actions, setActions] = useState<SuggestedAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchActions = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/semantic-insights/${insightId}/suggested-actions`);
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch suggested actions');
      }

      setActions(data.actions || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching suggested actions:', err);
      setActions([]); // Clear actions on error
    } finally {
      setLoading(false);
    }
  }, [insightId, enabled]);

  useEffect(() => {
    if (enabled) {
      fetchActions();
    }
  }, [fetchActions, enabled]);

  return {
    actions,
    loading,
    error,
    refetch: fetchActions
  };
};

/**
 * Agent action type for ActivityTimeline
 */
export type AgentActionType = 'progress' | 'tool_call' | 'tool_result' | 'warning' | 'error' | 'assistant_thinking';

export interface AgentAction {
  id: string;
  type: AgentActionType;
  label: string;
  detail?: string;
  timestamp: string;
  sessionId?: string;
}

/**
 * Hook to execute an action and connect to SSE for progress updates
 */
interface UseActionExecutionResult {
  actions: AgentAction[];
  loading: boolean;
  error: string | null;
  execute: (insightId: number, actionText: string) => Promise<string | null>; // Returns execution_id or null
  disconnect: () => void;
}

export const useActionExecution = (): UseActionExecutionResult => {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
    execute,
    disconnect
  };
};
