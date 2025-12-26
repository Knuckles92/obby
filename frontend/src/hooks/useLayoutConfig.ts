/**
 * useLayoutConfig Hook
 *
 * Hook to fetch and manage layout configuration
 */

import { useState, useEffect, useCallback } from 'react';

interface UseLayoutConfigResult {
  config: any;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  saveConfig: (newConfig: any) => Promise<boolean>;
}

export const useLayoutConfig = (layoutName: string): UseLayoutConfigResult => {
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

export default useLayoutConfig;
