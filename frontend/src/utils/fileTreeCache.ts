/**
 * File Tree Cache Utility
 * Manages localStorage caching for the file tree to improve performance
 */

const CACHE_KEY = 'obby_file_tree_cache';
const CACHE_VERSION = '1.0';

export interface FileTreeCacheData {
  tree: any;
  timestamp: string;
  version: string;
}

/**
 * Get cached file tree from localStorage
 * @returns Cached tree data or null if not found or invalid
 */
export function getCachedFileTree(): FileTreeCacheData | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) {
      return null;
    }

    const data: FileTreeCacheData = JSON.parse(cached);

    // Validate cache version
    if (data.version !== CACHE_VERSION) {
      console.log('[File Tree Cache] Version mismatch, invalidating cache');
      clearFileTreeCache();
      return null;
    }

    // Validate cache structure
    if (!data.tree || !data.timestamp) {
      console.log('[File Tree Cache] Invalid cache structure, clearing');
      clearFileTreeCache();
      return null;
    }

    console.log('[File Tree Cache] Retrieved from localStorage:', data.timestamp);
    return data;
  } catch (error) {
    console.error('[File Tree Cache] Error reading cache:', error);
    clearFileTreeCache();
    return null;
  }
}

/**
 * Save file tree to localStorage cache
 * @param tree The file tree data to cache
 * @param timestamp The timestamp from the server response
 */
export function setCachedFileTree(tree: any, timestamp: string): void {
  try {
    const cacheData: FileTreeCacheData = {
      tree,
      timestamp,
      version: CACHE_VERSION
    };

    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
    console.log('[File Tree Cache] Saved to localStorage:', timestamp);
  } catch (error) {
    console.error('[File Tree Cache] Error saving cache:', error);
    // If storage is full or unavailable, clear the cache
    clearFileTreeCache();
  }
}

/**
 * Clear the file tree cache from localStorage
 */
export function clearFileTreeCache(): void {
  try {
    localStorage.removeItem(CACHE_KEY);
    console.log('[File Tree Cache] Cleared from localStorage');
  } catch (error) {
    console.error('[File Tree Cache] Error clearing cache:', error);
  }
}

/**
 * Check if cache exists
 * @returns true if cache exists in localStorage
 */
export function hasCachedFileTree(): boolean {
  try {
    return localStorage.getItem(CACHE_KEY) !== null;
  } catch (error) {
    return false;
  }
}
