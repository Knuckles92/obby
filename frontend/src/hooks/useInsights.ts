/**
 * useInsights Hook
 *
 * Custom React hook for fetching and managing insights data from the backend.
 * Handles loading states, errors, and caching of results.
 */

import { useState, useEffect, useCallback } from 'react';
import type { InsightResult } from '../components/insights/InsightCard';

// Re-export types for backward compatibility
export type { DateRange, SemanticInsight, SemanticInsightsResponse, SuggestedAction, AgentAction, AgentActionType, ContextSpecificAction, InsightCategory, ContextAwareness } from './types';

// Re-export hooks for backward compatibility
export { useLayoutConfig } from './useLayoutConfig';
export { useSemanticInsights, invalidateInsightsCache } from './useSemanticInsights';
export { useSuggestedActions, useBatchSuggestedActions } from './useSuggestedActions';
export { useActionExecution } from './useActionExecution';

// Import DateRange type for local use
import type { DateRange } from './types';

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
