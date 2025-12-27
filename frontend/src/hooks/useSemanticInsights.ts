/**
 * useSemanticInsights Hook
 *
 * Hook to fetch and manage semantic insights with stale-while-revalidate caching.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { SemanticInsight, SemanticInsightsResponse, CacheEntry } from './types';

// ========================================
// INSIGHTS CACHE (Stale-While-Revalidate)
// ========================================

const INSIGHTS_CACHE_TTL = 30 * 1000; // 30 seconds
const insightsCache = new Map<string, CacheEntry<SemanticInsightsResponse>>();

function getInsightsCacheKey(type?: string, status?: string, limit?: number): string {
  return JSON.stringify({ type, status, limit });
}

function getCachedInsights(key: string): SemanticInsightsResponse | null {
  const entry = insightsCache.get(key);
  if (entry && Date.now() < entry.expires) {
    return entry.data;
  }
  return null;
}

function setCachedInsights(key: string, data: SemanticInsightsResponse): void {
  insightsCache.set(key, {
    data,
    expires: Date.now() + INSIGHTS_CACHE_TTL
  });
}

export function invalidateInsightsCache(): void {
  insightsCache.clear();
}

// ========================================
// HOOK
// ========================================

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
  clearInsights: () => Promise<void>;
  triggerIncrementalProcessing: () => Promise<void>;
}

/**
 * Hook to fetch and manage semantic insights
 * Uses stale-while-revalidate caching pattern for better performance
 */
export const useSemanticInsights = (options: UseSemanticInsightsOptions = {}): UseSemanticInsightsResult => {
  const { type, status, limit = 50, enabled = true } = options;

  const [insights, setInsights] = useState<SemanticInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<SemanticInsightsResponse['meta'] | null>(null);
  const fetchInProgressRef = useRef(false);

  /**
   * Fetch semantic insights with stale-while-revalidate caching
   */
  const fetchInsights = useCallback(async (skipCache: boolean = false) => {
    if (!enabled) return;

    const cacheKey = getInsightsCacheKey(type, status, limit);

    // Check cache first (stale-while-revalidate)
    if (!skipCache) {
      const cached = getCachedInsights(cacheKey);
      if (cached) {
        // Return cached data immediately
        setInsights(cached.insights);
        setMeta(cached.meta);
        setLoading(false);

        // Revalidate in background (but don't duplicate requests)
        if (!fetchInProgressRef.current) {
          fetchInProgressRef.current = true;
          // Background revalidate after a short delay
          setTimeout(async () => {
            try {
              const params = new URLSearchParams();
              if (type) params.append('type', type);
              if (status) params.append('status', status);
              params.append('limit', String(limit));

              const response = await fetch(`/api/semantic-insights?${params.toString()}`);
              const data: SemanticInsightsResponse = await response.json();

              if (data.success) {
                setCachedInsights(cacheKey, data);
                // Only update if data changed
                if (JSON.stringify(data.insights) !== JSON.stringify(cached.insights)) {
                  setInsights(data.insights);
                  setMeta(data.meta);
                }
              }
            } catch (err) {
              console.error('Background revalidation failed:', err);
            } finally {
              fetchInProgressRef.current = false;
            }
          }, 100);
        }
        return;
      }
    }

    // No cache or skip cache - fetch fresh data
    if (fetchInProgressRef.current) return;
    fetchInProgressRef.current = true;

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

      // Cache the response
      setCachedInsights(cacheKey, data);

      setInsights(data.insights);
      setMeta(data.meta);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching semantic insights:', err);
    } finally {
      setLoading(false);
      fetchInProgressRef.current = false;
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
        // Invalidate cache since data changed
        invalidateInsightsCache();

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
            // Update cache with fresh data
            const cacheKey = getInsightsCacheKey(type, status, limit);
            setCachedInsights(cacheKey, refreshData);
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
  }, [insights, type, status, limit]);

  /**
   * Trigger semantic processing (full scan - replaces non-pinned insights)
   */
  const triggerProcessing = useCallback(async () => {
    try {
      const response = await fetch('/api/semantic-insights/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ mode: 'replace' })
      });

      const data = await response.json();

      if (data.success) {
        // Invalidate cache and refresh insights after processing
        invalidateInsightsCache();
        await fetchInsights(true); // Skip cache to get fresh data
      } else {
        console.error('Processing trigger failed:', data.error);
      }
    } catch (err) {
      console.error('Error triggering processing:', err);
    }
  }, [fetchInsights]);

  /**
   * Clear all non-pinned insights
   */
  const clearInsights = useCallback(async () => {
    try {
      const response = await fetch('/api/semantic-insights/clear', {
        method: 'POST'
      });

      const data = await response.json();

      if (data.success) {
        // Invalidate cache and refresh insights after clearing
        invalidateInsightsCache();
        await fetchInsights(true); // Skip cache to get fresh data
      } else {
        console.error('Clear insights failed:', data.error);
      }
    } catch (err) {
      console.error('Error clearing insights:', err);
    }
  }, [fetchInsights]);

  /**
   * Trigger incremental processing (keep existing insights)
   */
  const triggerIncrementalProcessing = useCallback(async () => {
    try {
      const response = await fetch('/api/semantic-insights/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ mode: 'incremental' })
      });

      const data = await response.json();

      if (data.success) {
        // Invalidate cache and refresh insights after processing
        invalidateInsightsCache();
        await fetchInsights(true); // Skip cache to get fresh data
      } else {
        console.error('Incremental processing failed:', data.error);
      }
    } catch (err) {
      console.error('Error triggering incremental processing:', err);
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
    triggerProcessing,
    clearInsights,
    triggerIncrementalProcessing
  };
};

export default useSemanticInsights;
