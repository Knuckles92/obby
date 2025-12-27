/**
 * useApiCache Hook
 *
 * A generic, reusable hook for caching API responses with stale-while-revalidate pattern.
 * Follows the same patterns as useSemanticInsights.ts for consistency.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { CacheEntry, UseApiCacheOptions, UseApiCacheResult } from './types';

// Default cache TTL: 30 seconds
const DEFAULT_CACHE_TTL = 30 * 1000;

// Module-level cache registry - survives component unmounts
const cacheRegistry = new Map<string, Map<string, CacheEntry<any>>>();

/**
 * Get or create a cache namespace
 */
function getCache<T>(namespace: string): Map<string, CacheEntry<T>> {
  if (!cacheRegistry.has(namespace)) {
    cacheRegistry.set(namespace, new Map());
  }
  return cacheRegistry.get(namespace) as Map<string, CacheEntry<T>>;
}

/**
 * Get cached data if still valid
 */
function getCached<T>(namespace: string, key: string): T | null {
  const cache = getCache<T>(namespace);
  const entry = cache.get(key);
  if (entry && Date.now() < entry.expires) {
    return entry.data;
  }
  return null;
}

/**
 * Set cached data with expiration
 */
function setCached<T>(namespace: string, key: string, data: T, ttl: number): void {
  const cache = getCache<T>(namespace);
  cache.set(key, {
    data,
    expires: Date.now() + ttl
  });
}

/**
 * Invalidate a specific cache entry
 */
function invalidateCacheEntry(namespace: string, key: string): void {
  const cache = getCache(namespace);
  cache.delete(key);
}

/**
 * Invalidate all entries in a namespace
 */
export function invalidateCacheNamespace(namespace: string): void {
  const cache = cacheRegistry.get(namespace);
  if (cache) {
    cache.clear();
  }
}

/**
 * Mark a cache entry as stale (set expiry to now)
 * This triggers background revalidation on next access
 */
function markStale(namespace: string, key: string): void {
  const cache = getCache(namespace);
  const entry = cache.get(key);
  if (entry) {
    entry.expires = Date.now();
  }
}

/**
 * Generic API caching hook with stale-while-revalidate pattern
 */
export function useApiCache<T>(
  namespace: string,
  options: UseApiCacheOptions<T>
): UseApiCacheResult<T> {
  const { cacheKey, fetcher, ttl = DEFAULT_CACHE_TTL, enabled = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);
  const fetchInProgressRef = useRef(false);
  const mountedRef = useRef(true);

  /**
   * Fetch data with stale-while-revalidate caching
   */
  const fetchData = useCallback(async (skipCache: boolean = false) => {
    if (!enabled) return;

    // Check cache first (stale-while-revalidate)
    if (!skipCache) {
      const cached = getCached<T>(namespace, cacheKey);
      if (cached) {
        // Return cached data immediately
        setData(cached);
        setLoading(false);
        setIsStale(false);

        // Revalidate in background (but don't duplicate requests)
        if (!fetchInProgressRef.current) {
          fetchInProgressRef.current = true;
          setIsStale(true);

          // Background revalidate after a short delay
          setTimeout(async () => {
            try {
              const freshData = await fetcher();
              if (mountedRef.current) {
                setCached(namespace, cacheKey, freshData, ttl);
                // Only update if data changed
                if (JSON.stringify(freshData) !== JSON.stringify(cached)) {
                  setData(freshData);
                }
                setIsStale(false);
              }
            } catch (err) {
              console.error(`[useApiCache:${namespace}] Background revalidation failed:`, err);
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
      const freshData = await fetcher();
      if (mountedRef.current) {
        // Cache the response
        setCached(namespace, cacheKey, freshData, ttl);
        setData(freshData);
      }
    } catch (err) {
      if (mountedRef.current) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(errorMessage);
        console.error(`[useApiCache:${namespace}] Error fetching data:`, err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
        setIsStale(false);
      }
      fetchInProgressRef.current = false;
    }
  }, [namespace, cacheKey, fetcher, ttl, enabled]);

  /**
   * Invalidate this specific cache entry
   */
  const invalidate = useCallback(() => {
    invalidateCacheEntry(namespace, cacheKey);
    // Trigger a refetch
    fetchData(true);
  }, [namespace, cacheKey, fetchData]);

  // Fetch data on mount and when dependencies change
  useEffect(() => {
    mountedRef.current = true;
    fetchData();

    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    isStale,
    refetch: fetchData,
    invalidate
  };
}

export default useApiCache;
