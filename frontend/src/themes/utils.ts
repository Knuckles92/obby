import { Theme, ThemeCategory } from '../types';
import { themes } from './index';

/**
 * Get a theme by category, with optional fallback
 */
export function getThemeByCategory(
  category: ThemeCategory, 
  fallbackTheme?: Theme
): Theme {
  const categoryThemes = themes.filter(theme => theme.category === category);
  return categoryThemes[0] || fallbackTheme || themes[0];
}

/**
 * Find themes that match specific criteria
 */
export function findThemes(criteria: {
  hasAnimations?: boolean;
  hasGlassmorphism?: boolean;
  hasParticles?: boolean;
  hasGradients?: boolean;
  supportsHighContrast?: boolean;
  supportsLargeText?: boolean;
  colorContrast?: 'low' | 'medium' | 'high';
  motionSafety?: 'low' | 'medium' | 'high';
  cognitiveLoad?: 'low' | 'medium' | 'high';
  categories?: ThemeCategory[];
}): Theme[] {
  return themes.filter(theme => {
    // Check feature criteria
    if (criteria.hasAnimations !== undefined && theme.features.hasAnimations !== criteria.hasAnimations) {
      return false;
    }
    if (criteria.hasGlassmorphism !== undefined && theme.features.hasGlassmorphism !== criteria.hasGlassmorphism) {
      return false;
    }
    if (criteria.hasParticles !== undefined && theme.features.hasParticles !== criteria.hasParticles) {
      return false;
    }
    if (criteria.hasGradients !== undefined && theme.features.hasGradients !== criteria.hasGradients) {
      return false;
    }
    if (criteria.supportsHighContrast !== undefined && theme.features.supportsHighContrast !== criteria.supportsHighContrast) {
      return false;
    }
    if (criteria.supportsLargeText !== undefined && theme.features.supportsLargeText !== criteria.supportsLargeText) {
      return false;
    }

    // Check accessibility criteria
    if (criteria.colorContrast !== undefined && theme.accessibility.colorContrast !== criteria.colorContrast) {
      return false;
    }
    if (criteria.motionSafety !== undefined && theme.accessibility.motionSafety !== criteria.motionSafety) {
      return false;
    }
    if (criteria.cognitiveLoad !== undefined && theme.accessibility.cognitiveLoad !== criteria.cognitiveLoad) {
      return false;
    }

    // Check category criteria
    if (criteria.categories !== undefined && !criteria.categories.includes(theme.category)) {
      return false;
    }

    return true;
  });
}

/**
 * Get recommended themes based on user preferences
 */
export function getRecommendedThemes(preferences: {
  preferredCategories?: ThemeCategory[];
  needsHighContrast?: boolean;
  needsLargeText?: boolean;
  reducedMotion?: boolean;
  allowComplexAnimations?: boolean;
}): Theme[] {
  const criteria: Parameters<typeof findThemes>[0] = {};

  if (preferences.needsHighContrast) {
    criteria.supportsHighContrast = true;
    criteria.colorContrast = 'high';
  }

  if (preferences.needsLargeText) {
    criteria.supportsLargeText = true;
  }

  if (preferences.reducedMotion) {
    criteria.motionSafety = 'high';
    criteria.hasAnimations = false;
  }

  if (!preferences.allowComplexAnimations) {
    criteria.cognitiveLoad = 'low';
  }

  if (preferences.preferredCategories) {
    criteria.categories = preferences.preferredCategories;
  }

  return findThemes(criteria);
}

/**
 * Calculate theme similarity score
 */
export function calculateThemeSimilarity(theme1: Theme, theme2: Theme): number {
  let score = 0;
  const maxScore = 10;

  // Category similarity (30%)
  if (theme1.category === theme2.category) {
    score += 3;
  }

  // Feature similarity (40%)
  const features = ['hasAnimations', 'hasGlassmorphism', 'hasParticles', 'hasGradients'] as const;
  const matchingFeatures = features.filter(feature => 
    theme1.features[feature] === theme2.features[feature]
  ).length;
  score += (matchingFeatures / features.length) * 4;

  // Accessibility similarity (30%)
  const accessibilityProps = ['colorContrast', 'motionSafety', 'cognitiveLoad'] as const;
  const matchingAccessibility = accessibilityProps.filter(prop =>
    theme1.accessibility[prop] === theme2.accessibility[prop]
  ).length;
  score += (matchingAccessibility / accessibilityProps.length) * 3;

  return score / maxScore;
}

/**
 * Get similar themes to a given theme
 */
export function getSimilarThemes(targetTheme: Theme, count: number = 3): Theme[] {
  const otherThemes = themes.filter(theme => theme.id !== targetTheme.id);
  
  const themesWithScores = otherThemes.map(theme => ({
    theme,
    similarity: calculateThemeSimilarity(targetTheme, theme)
  }));

  return themesWithScores
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, count)
    .map(item => item.theme);
}

/**
 * Validate theme object structure
 */
export function validateTheme(theme: any): theme is Theme {
  const requiredProps = ['id', 'name', 'category', 'description', 'colors', 'typography', 'spacing', 'effects', 'features', 'accessibility'];
  
  for (const prop of requiredProps) {
    if (!(prop in theme)) {
      return false;
    }
  }

  // Validate colors structure
  const requiredColors = ['primary', 'secondary', 'accent', 'background', 'surface', 'text'];
  for (const color of requiredColors) {
    if (!(color in theme.colors)) {
      return false;
    }
  }

  // Validate text colors
  const requiredTextColors = ['primary', 'secondary', 'accent', 'inverse'];
  for (const textColor of requiredTextColors) {
    if (!(textColor in theme.colors.text)) {
      return false;
    }
  }

  return true;
}

/**
 * Create a custom theme variant
 */
export function createThemeVariant(
  baseTheme: Theme, 
  overrides: Partial<Theme>,
  variantId: string
): Theme {
  return {
    ...baseTheme,
    ...overrides,
    id: variantId,
    colors: {
      ...baseTheme.colors,
      ...overrides.colors,
      text: {
        ...baseTheme.colors.text,
        ...overrides.colors?.text
      }
    },
    typography: {
      ...baseTheme.typography,
      ...overrides.typography,
      fontFamily: {
        ...baseTheme.typography.fontFamily,
        ...overrides.typography?.fontFamily
      },
      fontSize: {
        ...baseTheme.typography.fontSize,
        ...overrides.typography?.fontSize
      },
      fontWeight: {
        ...baseTheme.typography.fontWeight,
        ...overrides.typography?.fontWeight
      },
      lineHeight: {
        ...baseTheme.typography.lineHeight,
        ...overrides.typography?.lineHeight
      },
      letterSpacing: {
        ...baseTheme.typography.letterSpacing,
        ...overrides.typography?.letterSpacing
      }
    },
    spacing: {
      ...baseTheme.spacing,
      ...overrides.spacing,
      borderRadius: {
        ...baseTheme.spacing.borderRadius,
        ...overrides.spacing?.borderRadius
      },
      spacing: {
        ...baseTheme.spacing.spacing,
        ...overrides.spacing?.spacing
      },
      shadows: {
        ...baseTheme.spacing.shadows,
        ...overrides.spacing?.shadows
      }
    },
    effects: {
      ...baseTheme.effects,
      ...overrides.effects,
      glassmorphism: {
        ...baseTheme.effects.glassmorphism,
        ...overrides.effects?.glassmorphism
      },
      animation: {
        ...baseTheme.effects.animation,
        ...overrides.effects?.animation,
        duration: {
          ...baseTheme.effects.animation.duration,
          ...overrides.effects?.animation?.duration
        },
        easing: {
          ...baseTheme.effects.animation.easing,
          ...overrides.effects?.animation?.easing
        }
      },
      specialEffects: {
        ...baseTheme.effects.specialEffects,
        ...overrides.effects?.specialEffects
      }
    },
    features: {
      ...baseTheme.features,
      ...overrides.features
    },
    accessibility: {
      ...baseTheme.accessibility,
      ...overrides.accessibility
    }
  };
}

/**
 * Generate theme preview CSS for thumbnails
 */
export function generateThemePreviewCSS(theme: Theme): string {
  return `
    background: linear-gradient(135deg, ${theme.colors.background} 0%, ${theme.colors.surface} 100%);
    color: ${theme.colors.text.primary};
    border: 1px solid ${theme.colors.border};
    border-radius: ${theme.spacing.borderRadius.md};
    box-shadow: ${theme.spacing.shadows.sm};
  `;
}

/**
 * Check if theme supports dark mode
 */
export function isDarkTheme(theme: Theme): boolean {
  // Simple heuristic: check if background is darker than text
  const bg = theme.colors.background;
  const text = theme.colors.text.primary;
  
  // Convert hex to luminance (simplified)
  const getLuminance = (hex: string): number => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = (rgb >> 16) & 0xff;
    const g = (rgb >> 8) & 0xff;
    const b = (rgb >> 0) & 0xff;
    return 0.299 * r + 0.587 * g + 0.114 * b;
  };
  
  return getLuminance(bg) < getLuminance(text);
}

/**
 * Get complementary themes (light/dark pairs)
 */
export function getComplementaryTheme(theme: Theme): Theme | null {
  const isDark = isDarkTheme(theme);
  
  // Find themes with opposite darkness but similar category
  const candidates = themes.filter(t => 
    t.id !== theme.id && 
    isDarkTheme(t) !== isDark &&
    t.category === theme.category
  );
  
  if (candidates.length === 0) {
    // Fallback: find any theme with opposite darkness
    return themes.find(t => t.id !== theme.id && isDarkTheme(t) !== isDark) || null;
  }
  
  return candidates[0];
}

/**
 * Theme performance optimizer
 */
export function optimizeThemeForPerformance(theme: Theme): Theme {
  const optimized = { ...theme };
  
  // Disable heavy animations for low-end devices
  if (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4) {
    optimized.features.hasAnimations = false;
    optimized.features.hasParticles = false;
    optimized.effects.specialEffects = {};
  }
  
  // Reduce blur for devices that don't support backdrop-filter well
  if (!CSS.supports('backdrop-filter: blur(10px)')) {
    optimized.effects.glassmorphism.blur = '0px';
    optimized.effects.glassmorphism.opacity = 1;
  }
  
  return optimized;
} 