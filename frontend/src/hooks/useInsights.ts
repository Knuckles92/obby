/**
 * useInsights Hook
 *
 * Custom React hook for fetching and managing insights data from the backend.
 * Handles loading states, errors, and caching of results.
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import type { InsightResult } from '../components/insights/InsightCard';
import { useApiCache } from './useApiCache';

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
  refetch: (skipCache?: boolean) => void;
  availableInsights: any[];
}

/**
 * Hook to fetch and manage insights data
 */
export const useInsights = (options: UseInsightsOptions): UseInsightsResult => {
  const { layoutName, dateRange, enabled = true } = options;

  const [availableInsights, setAvailableInsights] = useState<any[]>([]);

  /**
   * Fetch available insights metadata
   * Note: This is relatively static and could also be cached, but it's fast
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
   * Main fetcher function passed to useApiCache
   */
  const insightsFetcher = useCallback(async () => {
    // 1. Get the layout configuration
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
      return {};
    }

    // 2. Build query parameters
    const params = new URLSearchParams({
      insight_ids: enabledInsightIds.join(',')
    });

    if (dateRange.days !== undefined) {
      params.append('days', String(dateRange.days));
    } else if (dateRange.start && dateRange.end) {
      params.append('start_date', dateRange.start);
      params.append('end_date', dateRange.end);
    }

    // 3. Fetch insights calculation
    const response = await fetch(`/api/insights/calculate?${params.toString()}`);
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to calculate insights');
    }

    return data.insights as Record<string, InsightResult>;
  }, [layoutName, dateRange]);

  // Create a stable cache key based on dependencies
  const cacheKey = useMemo(() => {
    return JSON.stringify({ layoutName, dateRange });
  }, [layoutName, dateRange]);

  // Use the generic API cache hook
  const {
    data: insightsData,
    loading,
    error,
    refetch
  } = useApiCache<Record<string, InsightResult>>('insights', {
    cacheKey,
    fetcher: insightsFetcher,
    enabled,
    ttl: 60 * 1000 // 1 minute cache for activity metrics
  });

  // Also fetch available insights on mount
  useEffect(() => {
    if (enabled) {
      fetchAvailableInsights();
    }
  }, [enabled, fetchAvailableInsights]);

  return {
    insights: insightsData || {},
    loading,
    error,
    refetch,
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

