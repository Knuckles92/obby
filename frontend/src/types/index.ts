export interface FileEvent {
  id: string;
  type: 'created' | 'modified' | 'deleted' | 'moved';
  path: string;
  timestamp: string;
  size?: number;
}

export interface DiffEntry {
  id: string;
  filePath: string;
  timestamp: string;
  content: string;
  size?: number;
  fullPath?: string;
  summary?: string;
}

export interface MonitoringStatus {
  isActive: boolean;
  watchedPaths: string[];
  totalFiles: number;
  eventsToday: number;
}

export interface ConfigSettings {
  checkInterval: number;
  openaiApiKey: string;
  aiModel: string;
  ignorePatterns: string[];
  periodicCheckEnabled?: boolean;
}

export interface SearchResult {
  id: string;
  timestamp: string;
  summary: string;
  topics: string[];
  keywords: string[];
  impact: string;
  relevance_score: number;
}

export interface SemanticMetadata {
  topics: Record<string, number>;
  keywords: Record<string, number>;
  totalEntries: number;
}

export interface LivingNoteSection {
  title: string;
  content: string;
  type: string;
  metadata?: Record<string, any>;
}

export interface LivingNote {
  content: string;
  lastUpdated: string;
  wordCount: number;
  metadata?: SemanticMetadata;
  sections?: LivingNoteSection[];
}

export interface SearchFilters {
  query?: string;
  topics?: string[];
  keywords?: string[];
  dateFrom?: string;
  dateTo?: string;
  minRelevance?: number;
  limit?: number;
  offset?: number;
  impact?: string[];
  sortBy?: string;
}

export interface ModelsResponse {
  models: Record<string, string>;
  defaultModel: string;
  currentModel: string;
  error?: string;
}