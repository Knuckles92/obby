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

// File-based interfaces (replaces git-based interfaces)
export interface FileVersion {
  id: string;
  filePath: string;
  contentHash: string;
  lineCount: number;
  timestamp: string;
  changeDescription: string;
  hasContent: boolean;
}

export interface ContentDiff {
  id: string;
  filePath: string;
  changeType: 'created' | 'modified' | 'deleted' | 'moved';
  diffContent: string;
  linesAdded: number;
  linesRemoved: number;
  timestamp: string;
  oldVersionId?: number;
  newVersionId?: number;
}

export interface FileChange {
  id: string;
  filePath: string;
  changeType: 'created' | 'modified' | 'deleted' | 'moved';
  oldContentHash?: string;
  newContentHash?: string;
  timestamp: string;
}

export interface FileMonitoringStatus {
  monitoring_active: boolean;
  tracked_files_count: number;
  recent_versions_count: number;
  recent_changes_count: number;
  database_stats: any;
  last_activity?: string;
  system_type: string;
  version: string;
}

// Pagination interfaces
export interface PaginationMetadata {
  total: number;
  count: number;
  offset: number;
  limit: number;
  hasMore: boolean;
  currentPage: number;
  totalPages: number;
}

export interface PaginatedResponse<T> {
  pagination: PaginationMetadata;
  data?: T[];
}

export interface PaginatedDiffsResponse extends PaginatedResponse<ContentDiff> {
  diffs: ContentDiff[];
}

export interface PaginatedChangesResponse extends PaginatedResponse<FileChange> {
  changes: FileChange[];
}

// (Removed legacy Git interfaces)

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
  monitoringDirectory?: string; // base directory to monitor for changes
  periodicCheckEnabled?: boolean;
  aiUpdateInterval?: number; // AI update frequency in hours
  aiAutoUpdateEnabled?: boolean; // whether AI auto-updates are enabled
  lastAiUpdateTimestamp?: string | null; // when AI was last run
}

export interface SessionSummarySection {
  title: string;
  content: string;
  type: string;
  metadata?: Record<string, any>;
}

export interface SessionSummary {
  content: string;
  lastUpdated: string;
  wordCount: number;
  sections?: SessionSummarySection[];
}

export interface SessionSummarySettings {
  updateFrequency: 'realtime' | 'hourly' | 'daily' | 'weekly' | 'manual';
  summaryLength: 'brief' | 'moderate' | 'detailed';
  writingStyle: 'technical' | 'casual' | 'formal' | 'bullet-points';
  includeMetrics: boolean;
  autoUpdate: boolean;
  maxSections: number;
  focusAreas: string[];
}

export interface ModelsResponse {
  models: Record<string, string>;
  defaultModel: string;
  currentModel: string;
  error?: string;
}

// Theme System Types
export type ThemeCategory = 'professional' | 'creative' | 'accessible' | 'special';

export interface ThemeColors {
  // Core colors
  primary: string;
  secondary: string;
  accent: string;
  
  // Background variants
  background: string;
  surface: string;
  overlay: string;
  
  // Text variants
  text: {
    primary: string;
    secondary: string;
    accent: string;
    inverse: string;
  };
  
  // Status colors
  success: string;
  warning: string;
  error: string;
  info: string;
  
  // Border and divider
  border: string;
  divider: string;
  
  // Interactive states
  hover: string;
  active: string;
  focus: string;
  disabled: string;
}

export interface ThemeTypography {
  fontFamily: {
    sans: string;
    serif: string;
    mono: string;
    display: string;
  };
  fontSize: {
    xs: string;
    sm: string;
    base: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
    '4xl': string;
  };
  fontWeight: {
    light: number;
    normal: number;
    medium: number;
    semibold: number;
    bold: number;
  };
  lineHeight: {
    tight: number;
    normal: number;
    relaxed: number;
  };
  letterSpacing: {
    tight: string;
    normal: string;
    wide: string;
  };
}

export interface ThemeSpacing {
  borderRadius: {
    none: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    full: string;
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
    inner: string;
    glow: string;
  };
}

export interface ThemeEffects {
  // Glassmorphism settings
  glassmorphism: {
    blur: string;
    opacity: number;
    border: string;
  };
  
  // Animation settings
  animation: {
    duration: {
      fast: string;
      normal: string;
      slow: string;
    };
    easing: {
      ease: string;
      easeIn: string;
      easeOut: string;
      easeInOut: string;
    };
  };
  
  // Special effects per theme
  specialEffects: {
    glowIntensity?: number;
    particleCount?: number;
    waveSpeed?: number;
    pulseRate?: number;
    snowflakeCount?: number;
    dataStreamCount?: number;
  };
}

export interface Theme {
  id: string;
  name: string;
  category: ThemeCategory;
  description: string;
  preview: string; // URL or base64 for preview image
  colors: ThemeColors;
  typography: ThemeTypography;
  spacing: ThemeSpacing;
  effects: ThemeEffects;
  
  // Theme-specific features
  features: {
    hasAnimations: boolean;
    hasGlassmorphism: boolean;
    hasParticles: boolean;
    hasGradients: boolean;
    supportsHighContrast: boolean;
    supportsLargeText: boolean;
  };
  
  // Accessibility ratings
  accessibility: {
    colorContrast: 'low' | 'medium' | 'high';
    motionSafety: 'low' | 'medium' | 'high';
    cognitiveLoad: 'low' | 'medium' | 'high';
  };
}

export interface ThemeContextValue {
  currentTheme: Theme;
  setTheme: (themeId: string) => void;
  availableThemes: Theme[];
  themeCategories: Record<ThemeCategory, Theme[]>;
  isLoading: boolean;
  preferences: ThemePreferences;
  updatePreferences: (preferences: Partial<ThemePreferences>) => void;
}

export interface ThemePreferences {
  preferredCategory: ThemeCategory;
  autoSwitchByTime: boolean;
  dayTheme: string;
  nightTheme: string;
  reduceMotion: boolean;
  highContrast: boolean;
  largeText: boolean;
  customCssVariables: Record<string, string>;
}

// Summary Notes interfaces
export interface SummaryNote {
  filename: string;
  timestamp: string;
  title: string;
  preview: string;
  word_count: number;
  created_time: string;
  file_size: number;
  last_modified: string;
}

export interface SummaryPaginationInfo {
  current_page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface SummaryListResponse {
  summaries: SummaryNote[];
  pagination: SummaryPaginationInfo;
}

export interface SummaryContentResponse {
  filename: string;
  content: string;
  timestamp: string;
  title: string;
  word_count: number;
  created_time: string;
  file_size: number;
  last_modified: string;
}

export type SummaryViewMode = 'single' | 'grid';

export interface SummarySearchFilters {
  searchTerm: string;
  sortBy: 'newest' | 'oldest' | 'word_count';
  dateRange?: {
    start: string;
    end: string;
  };
}

// Watch Configuration interfaces
export interface WatchPatternsResponse {
  patterns: string[];
  watchDirectories: string[];
  watchFile: string;
  success: boolean;
}

export interface IgnorePatternsResponse {
  patterns: string[];
  ignoreFile: string;
  success: boolean;
}

export interface WatchConfigResponse {
  success: boolean;
  message: string;
  patterns: string[];
}

export interface PatternValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  pattern: string;
}

export interface WatchConfigReloadResponse {
  success: boolean;
  message: string;
  watchPatterns: string[];
  ignorePatterns: string[];
}

// Bulk delete operation interfaces
export interface BulkDeleteResult {
  filename: string;
  success: boolean;
  message?: string;
  error?: string;
}

export interface BulkDeleteSummary {
  total: number;
  succeeded: number;
  failed: number;
  failed_files: string[];
}

export interface BulkDeleteResponse {
  success: boolean;
  message: string;
  results: BulkDeleteResult[];
  summary: BulkDeleteSummary;
}

export interface BulkDeleteRequest {
  filenames: string[];
}

// Search Results Popup interfaces
// Admin panel interfaces
export type { SystemStats, DatabaseStats } from './admin';

export interface SearchResultsPopupProps {
  isOpen: boolean;
  onClose: () => void;
  searchTerm: string;
  searchResults: SummaryNote[];
  loading: boolean;
  onSelectResult: (filename: string) => void;
}
