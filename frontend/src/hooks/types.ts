/**
 * Shared types for hooks
 */

export interface DateRange {
  start: string;
  end: string;
  days?: number;
}

/**
 * Semantic Insight types
 */
export interface SemanticInsight {
  id: number;
  type: string;
  title: string;
  summary: string;
  confidence: number;
  priority: number;
  status: string;
  sourceNotes: Array<{
    path: string;
    snippet?: string;
  }>;
  evidence: Record<string, any>;
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
