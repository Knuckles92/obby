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
  sections?: LivingNoteSection[];
}

export interface LivingNoteSettings {
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