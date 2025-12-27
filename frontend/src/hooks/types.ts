/**
 * Shared types for hooks
 */

export interface DateRange {
  start: string;
  end: string;
  days?: number;
}

/**
 * Insight category types
 */
export type InsightCategory = 'immediate_action' | 'trend' | 'recommendation' | 'observation';

/**
 * Context-specific action (replaces generic suggested actions)
 */
export interface ContextSpecificAction {
  text: string;
  rationale: string;
  actionType: 'complete' | 'modify' | 'archive' | 'expand' | 'delegate';
}

/**
 * Context awareness metadata
 */
export interface ContextAwareness {
  recencyScore?: number;
  projectContext?: string[];
  relevanceFactors?: string[];
}

/**
 * Semantic Insight types
 */
export interface SemanticInsight {
  id: number;
  type: string;
  title: string;
  summary: string;
  reasoning?: string;  // NEW: Explains WHY this insight matters
  category?: InsightCategory;  // NEW: immediate_action, trend, recommendation, observation
  confidence: number;
  priority: number;
  status: string;
  sourceNotes: Array<{
    path: string;
    snippet?: string;
  }>;
  evidence: Record<string, any>;
  contextAwareness?: ContextAwareness;  // NEW: recency, project context, relevance
  contextSpecificActions?: ContextSpecificAction[];  // NEW: Specific actions with rationale
  actions: string[];
  createdAt: string;
  viewedAt?: string;
  userAction?: string;
}

export interface SemanticInsightsResponse {
  success: boolean;
  insights: SemanticInsight[];
  meta: {
    total: number;
    limit: number;
    offset: number;
    byType: Record<string, number>;
    byStatus: Record<string, number>;
  };
}

/**
 * Suggested action types
 */
export interface SuggestedAction {
  text: string;
  description: string;
}

/**
 * Agent action type for ActivityTimeline
 */
export type AgentActionType = 'progress' | 'tool_call' | 'tool_result' | 'warning' | 'error' | 'assistant_thinking';

export interface AgentAction {
  id: string;
  type: AgentActionType;
  label: string;
  detail?: string;
  timestamp: string;
  sessionId?: string;
}

/**
 * Cache entry type for stale-while-revalidate pattern
 */
export interface CacheEntry<T> {
  data: T;
  expires: number;
}

/**
 * Options for the useApiCache hook
 */
export interface UseApiCacheOptions<T> {
  cacheKey: string;
  fetcher: () => Promise<T>;
  ttl?: number;
  enabled?: boolean;
}

/**
 * Result from the useApiCache hook
 */
export interface UseApiCacheResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  isStale: boolean;
  refetch: (skipCache?: boolean) => void;
  invalidate: () => void;
}
