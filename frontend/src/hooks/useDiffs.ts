/**
 * useDiffs Hook
 *
 * Hook for fetching and caching content diffs with pagination support.
 * Uses useApiCache internally for stale-while-revalidate caching.
 */

import { useState, useCallback, useRef } from 'react';
import { useApiCache, invalidateCacheNamespace } from './useApiCache';
import type { ContentDiff, PaginatedDiffsResponse, PaginationMetadata } from '../types';
import { apiFetch } from '../utils/api';

const CACHE_NAMESPACE = 'diffs';
const DEFAULT_LIMIT = 50;

interface UseDiffsOptions {
  limit?: number;
  enabled?: boolean;
}

interface UseDiffsResult {
  diffs: ContentDiff[];
  pagination: PaginationMetadata | null;
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  refetch: (skipCache?: boolean) => void;
  loadMore: () => Promise<void>;
  invalidate: () => void;
}

/**
 * Invalidate all diffs cache entries
 * Exported for use in SSE handlers
 */
export function invalidateDiffsCache(): void {
  invalidateCacheNamespace(CACHE_NAMESPACE);
}

/**
 * Fetch diffs from the API
 */
async function fetchDiffsFromApi(limit: number): Promise<PaginatedDiffsResponse> {
  const response = await apiFetch(`/api/files/diffs?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch diffs: ${response.status}`);
  }
  return response.json();
}

/**
 * Hook to fetch and manage content diffs with caching
 */
export function useDiffs(options: UseDiffsOptions = {}): UseDiffsResult {
  const { limit = DEFAULT_LIMIT, enabled = true } = options;

  // Use the generic cache hook for initial data
  const cacheKey = `diffs-${limit}`;
  const {
    data: cachedData,
    loading: cacheLoading,
    error: cacheError,
    refetch,
    invalidate: invalidateCache
  } = useApiCache<PaginatedDiffsResponse>(CACHE_NAMESPACE, {
    cacheKey,
    fetcher: () => fetchDiffsFromApi(limit),
    enabled
  });

  // Local state for accumulated diffs (for pagination)
  const [additionalDiffs, setAdditionalDiffs] = useState<ContentDiff[]>([]);
  const [currentPagination, setCurrentPagination] = useState<PaginationMetadata | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreInProgressRef = useRef(false);

  // Combine cached data with additional paginated data
  const diffs = cachedData?.diffs
    ? [...cachedData.diffs, ...additionalDiffs]
    : additionalDiffs;

  // Use current pagination if we've loaded more, otherwise use cached pagination
  const pagination = currentPagination || cachedData?.pagination || null;

  /**
   * Load more diffs (pagination)
   */
  const loadMore = useCallback(async () => {
    if (!pagination?.hasMore || loadMoreInProgressRef.current || loadingMore) {
      return;
    }

    loadMoreInProgressRef.current = true;
    setLoadingMore(true);

    try {
      const offset = pagination.offset + pagination.limit;
      const response = await apiFetch(`/api/files/diffs?limit=${limit}&offset=${offset}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch more diffs: ${response.status}`);
      }

      const responseData: PaginatedDiffsResponse = await response.json();

      // Append new diffs to additional diffs
      setAdditionalDiffs(prev => [...prev, ...(responseData.diffs || [])]);
      setCurrentPagination(responseData.pagination);
    } catch (error) {
      console.error('[useDiffs] Error loading more diffs:', error);
    } finally {
      setLoadingMore(false);
      loadMoreInProgressRef.current = false;
    }
  }, [pagination, limit, loadingMore]);

  /**
   * Invalidate cache and reset pagination state
   */
  const invalidate = useCallback(() => {
    setAdditionalDiffs([]);
    setCurrentPagination(null);
    invalidateCache();
  }, [invalidateCache]);

  /**
   * Refetch with cache option, resetting pagination
   */
  const handleRefetch = useCallback((skipCache?: boolean) => {
    setAdditionalDiffs([]);
    setCurrentPagination(null);
    refetch(skipCache);
  }, [refetch]);

  return {
    diffs,
    pagination,
    loading: cacheLoading,
    loadingMore,
    error: cacheError,
    refetch: handleRefetch,
    loadMore,
    invalidate
  };
}

export default useDiffs;
