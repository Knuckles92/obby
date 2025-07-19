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
  watchPaths: string[];
  ignorePatterns: string[];
}

export interface LivingNote {
  content: string;
  lastUpdated: string;
  wordCount: number;
}

export interface ModelsResponse {
  models: Record<string, string>;
  defaultModel: string;
  currentModel: string;
  error?: string;
}