/**
 * useMonitoringStatus Hook
 *
 * Hook for fetching and caching file monitoring status.
 * Uses useApiCache internally for stale-while-revalidate caching.
 */

import { useCallback } from 'react';
import { useApiCache, invalidateCacheNamespace } from './useApiCache';
import type { FileMonitoringStatus } from '../types';
import { apiFetch } from '../utils/api';

const CACHE_NAMESPACE = 'monitoringStatus';
const CACHE_KEY = 'status';

interface UseMonitoringStatusResult {
  status: FileMonitoringStatus | null;
  loading: boolean;
  error: string | null;
  refetch: (skipCache?: boolean) => void;
  invalidate: () => void;
}

/**
 * Invalidate monitoring status cache
 * Exported for use in SSE handlers
 */
export function invalidateMonitoringStatusCache(): void {
  invalidateCacheNamespace(CACHE_NAMESPACE);
}

/**
 * Fetch monitoring status from the API
 */
async function fetchStatusFromApi(): Promise<FileMonitoringStatus | null> {
  const response = await apiFetch('/api/files/monitoring-status');
  if (!response.ok) {
    // Return null for non-ok responses (monitoring might be disabled)
    return null;
  }
  return response.json();
}

/**
 * Hook to fetch and manage file monitoring status with caching
 */
export function useMonitoringStatus(): UseMonitoringStatusResult {
  const {
    data: status,
    loading,
    error,
    refetch,
    invalidate: invalidateCache
  } = useApiCache<FileMonitoringStatus | null>(CACHE_NAMESPACE, {
    cacheKey: CACHE_KEY,
    fetcher: fetchStatusFromApi
  });

  /**
   * Invalidate cache
   */
  const invalidate = useCallback(() => {
    invalidateCache();
  }, [invalidateCache]);

  return {
    status,
    loading,
    error,
    refetch,
    invalidate
  };
}

export default useMonitoringStatus;
