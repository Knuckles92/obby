/**
 * Unit tests for API utilities
 *
 * Tests the API helper functions that handle HTTP requests
 * to the backend server.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiFetch, apiRequest, triggerSessionSummaryUpdate } from '../../utils/api';

describe('API Utilities', () => {
  beforeEach(() => {
    // Reset fetch mock before each test
    global.fetch = vi.fn();
  });

  describe('apiFetch', () => {
    it('should throw error if endpoint does not start with /api', async () => {
      await expect(apiFetch('/wrong')).rejects.toThrow('API endpoints must start with /api');
    });

    it('should call fetch with correct URL', async () => {
      const mockResponse = new Response(JSON.stringify({}), { status: 200 });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      await apiFetch('/api/test');

      expect(global.fetch).toHaveBeenCalledWith('/api/test', undefined);
    });

    it('should pass options to fetch', async () => {
      const mockResponse = new Response(JSON.stringify({}), { status: 200 });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      const options = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
      await apiFetch('/api/test', options);

      expect(global.fetch).toHaveBeenCalledWith('/api/test', options);
    });
  });

  describe('apiRequest', () => {
    it('should parse JSON response on success', async () => {
      const mockData = { result: 'success' };
      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      const result = await apiRequest('/api/test');

      expect(result).toEqual(mockData);
    });

    it('should throw error on HTTP error response', async () => {
      const mockResponse = new Response(JSON.stringify({ error: 'Not found' }), {
        status: 404,
        statusText: 'Not Found'
      });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      await expect(apiRequest('/api/notfound')).rejects.toThrow('Not found');
    });

    it('should handle errors without JSON body', async () => {
      const mockResponse = new Response('', {
        status: 500,
        statusText: 'Internal Server Error'
      });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      await expect(apiRequest('/api/error')).rejects.toThrow('HTTP 500');
    });

    it('should return typed response', async () => {
      interface TestResponse {
        id: number;
        name: string;
      }

      const mockData: TestResponse = { id: 1, name: 'test' };
      const mockResponse = new Response(JSON.stringify(mockData), { status: 200 });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      const result = await apiRequest<TestResponse>('/api/test');

      expect(result.id).toBe(1);
      expect(result.name).toBe('test');
    });
  });

  describe('triggerSessionSummaryUpdate', () => {
    it('should send POST request with async parameters', async () => {
      const mockData = { success: true, updated: true };
      const mockResponse = new Response(JSON.stringify(mockData), { status: 200 });
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      const result = await triggerSessionSummaryUpdate(true);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/session-summary/update',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"async":true')
        })
      );
      expect(result.success).toBe(true);
    });
  });

  describe('Error handling', () => {
    it('should extract error message from response', async () => {
      const mockResponse = new Response(
        JSON.stringify({ message: 'Custom error message' }),
        { status: 400 }
      );
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      await expect(apiRequest('/api/test')).rejects.toThrow('Custom error message');
    });

    it('should extract error from details field', async () => {
      const mockResponse = new Response(
        JSON.stringify({ details: 'Detailed error' }),
        { status: 400 }
      );
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      await expect(apiRequest('/api/test')).rejects.toThrow('Detailed error');
    });

    it('should fall back to HTTP status text', async () => {
      const mockResponse = new Response(
        JSON.stringify({}),
        { status: 400, statusText: 'Bad Request' }
      );
      (global.fetch as any) = vi.fn().mockResolvedValue(mockResponse);

      await expect(apiRequest('/api/test')).rejects.toThrow('HTTP 400');
    });
  });
});
