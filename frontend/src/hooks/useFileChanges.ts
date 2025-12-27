/**
 * useFileChanges Hook
 *
 * Hook for fetching and caching file changes with pagination support.
 * Uses useApiCache internally for stale-while-revalidate caching.
 */

import { useState, useCallback, useRef } from 'react';
import { useApiCache, invalidateCacheNamespace } from './useApiCache';
import type { FileChange, PaginatedChangesResponse, PaginationMetadata } from '../types';
import { apiFetch } from '../utils/api';

const CACHE_NAMESPACE = 'fileChanges';
const DEFAULT_LIMIT = 50;

interface UseFileChangesOptions {
  limit?: number;
  enabled?: boolean;
}

interface UseFileChangesResult {
  changes: FileChange[];
  pagination: PaginationMetadata | null;
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  refetch: (skipCache?: boolean) => void;
  loadMore: () => Promise<void>;
  invalidate: () => void;
}

/**
 * Invalidate all file changes cache entries
 * Exported for use in SSE handlers
 */
export function invalidateFileChangesCache(): void {
  invalidateCacheNamespace(CACHE_NAMESPACE);
}

/**
 * Fetch file changes from the API
 */
async function fetchChangesFromApi(limit: number): Promise<PaginatedChangesResponse> {
  const response = await apiFetch(`/api/files/changes?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch changes: ${response.status}`);
  }
  return response.json();
}

/**
 * Hook to fetch and manage file changes with caching
 */
export function useFileChanges(options: UseFileChangesOptions = {}): UseFileChangesResult {
  const { limit = DEFAULT_LIMIT, enabled = true } = options;

  // Use the generic cache hook for initial data
  const cacheKey = `changes-${limit}`;
  const {
    data: cachedData,
    loading: cacheLoading,
    error: cacheError,
    refetch,
    invalidate: invalidateCache
  } = useApiCache<PaginatedChangesResponse>(CACHE_NAMESPACE, {
    cacheKey,
    fetcher: () => fetchChangesFromApi(limit),
    enabled
  });

  // Local state for accumulated changes (for pagination)
  const [additionalChanges, setAdditionalChanges] = useState<FileChange[]>([]);
  const [currentPagination, setCurrentPagination] = useState<PaginationMetadata | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreInProgressRef = useRef(false);

  // Combine cached data with additional paginated data
  const changes = cachedData?.changes
    ? [...cachedData.changes, ...additionalChanges]
    : additionalChanges;

  // Use current pagination if we've loaded more, otherwise use cached pagination
  const pagination = currentPagination || cachedData?.pagination || null;

  /**
   * Load more changes (pagination)
   */
  const loadMore = useCallback(async () => {
    if (!pagination?.hasMore || loadMoreInProgressRef.current || loadingMore) {
      return;
    }

    loadMoreInProgressRef.current = true;
    setLoadingMore(true);

    try {
      const offset = pagination.offset + pagination.limit;
      const response = await apiFetch(`/api/files/changes?limit=${limit}&offset=${offset}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch more changes: ${response.status}`);
      }

      const responseData: PaginatedChangesResponse = await response.json();

      // Append new changes to additional changes
      setAdditionalChanges(prev => [...prev, ...(responseData.changes || [])]);
      setCurrentPagination(responseData.pagination);
    } catch (error) {
      console.error('[useFileChanges] Error loading more changes:', error);
    } finally {
      setLoadingMore(false);
      loadMoreInProgressRef.current = false;
    }
  }, [pagination, limit, loadingMore]);

  /**
   * Invalidate cache and reset pagination state
   */
  const invalidate = useCallback(() => {
    setAdditionalChanges([]);
    setCurrentPagination(null);
    invalidateCache();
  }, [invalidateCache]);

  /**
   * Refetch with cache option, resetting pagination
   */
  const handleRefetch = useCallback((skipCache?: boolean) => {
    setAdditionalChanges([]);
    setCurrentPagination(null);
    refetch(skipCache);
  }, [refetch]);

  return {
    changes,
    pagination,
    loading: cacheLoading,
    loadingMore,
    error: cacheError,
    refetch: handleRefetch,
    loadMore,
    invalidate
  };
}

export default useFileChanges;
