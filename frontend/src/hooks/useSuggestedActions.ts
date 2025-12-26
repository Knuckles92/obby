/**
 * useSuggestedActions Hooks
 *
 * Hooks for fetching suggested actions for insights (single and batch).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { SuggestedAction, CacheEntry } from './types';

// ========================================
// SUGGESTED ACTIONS CACHE
// ========================================

const SUGGESTED_ACTIONS_CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const suggestedActionsCache = new Map<number, CacheEntry<SuggestedAction[]>>();

function getCachedSuggestedActions(insightId: number): SuggestedAction[] | null {
  const entry = suggestedActionsCache.get(insightId);
  if (entry && Date.now() < entry.expires) {
    return entry.data;
  }
  return null;
}

function setCachedSuggestedActions(insightId: number, actions: SuggestedAction[]): void {
  suggestedActionsCache.set(insightId, {
    data: actions,
    expires: Date.now() + SUGGESTED_ACTIONS_CACHE_TTL
  });
}

// ========================================
// SINGLE SUGGESTED ACTIONS HOOK
// ========================================

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

// ========================================
// BATCH SUGGESTED ACTIONS HOOK
// ========================================

interface BatchSuggestedActionsResponse {
  success: boolean;
  results: Record<number, {
    actions: SuggestedAction[];
    cached?: boolean;
    error?: string;
  }>;
}

interface UseBatchSuggestedActionsResult {
  actionsMap: Record<number, SuggestedAction[]>;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook to fetch suggested actions for multiple insights in a single batch request.
 * Significantly reduces N+1 API calls when displaying multiple todo insights.
 */
export const useBatchSuggestedActions = (
  insightIds: number[],
  enabled: boolean = true
): UseBatchSuggestedActionsResult => {
  const [actionsMap, setActionsMap] = useState<Record<number, SuggestedAction[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchInProgressRef = useRef(false);

  const fetchBatchActions = useCallback(async () => {
    if (!enabled || insightIds.length === 0) return;
    if (fetchInProgressRef.current) return;

    // Check which insight IDs need fetching (not in cache)
    const uncachedIds: number[] = [];
    const cachedResults: Record<number, SuggestedAction[]> = {};

    for (const id of insightIds) {
      const cached = getCachedSuggestedActions(id);
      if (cached) {
        cachedResults[id] = cached;
      } else {
        uncachedIds.push(id);
      }
    }

    // If all are cached, just return cached results
    if (uncachedIds.length === 0) {
      setActionsMap(cachedResults);
      setLoading(false);
      return;
    }

    // Set loading only if we need to fetch
    setLoading(true);
    setError(null);
    fetchInProgressRef.current = true;

    try {
      const response = await fetch('/api/semantic-insights/batch-suggested-actions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ insight_ids: uncachedIds })
      });

      const data: BatchSuggestedActionsResponse = await response.json();

      if (!data.success) {
        throw new Error('Failed to fetch batch suggested actions');
      }

      // Merge cached and fresh results
      const mergedResults = { ...cachedResults };
      for (const [idStr, result] of Object.entries(data.results)) {
        const id = parseInt(idStr, 10);
        if (result.actions && result.actions.length > 0) {
          mergedResults[id] = result.actions;
          // Cache the fetched actions
          setCachedSuggestedActions(id, result.actions);
        } else {
          mergedResults[id] = [];
        }
      }

      setActionsMap(mergedResults);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching batch suggested actions:', err);
      // Still set cached results even on error
      setActionsMap(cachedResults);
    } finally {
      setLoading(false);
      fetchInProgressRef.current = false;
    }
  }, [insightIds, enabled]);

  // Fetch when insight IDs change
  useEffect(() => {
    if (enabled && insightIds.length > 0) {
      fetchBatchActions();
    }
  }, [fetchBatchActions, enabled, insightIds.length]);

  return {
    actionsMap,
    loading,
    error,
    refetch: fetchBatchActions
  };
};

export default useSuggestedActions;
