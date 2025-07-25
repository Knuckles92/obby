import { Theme } from '../types';

/**
 * Converts a theme object to CSS custom properties
 */
export function themeToCSS(theme: Theme): Record<string, string> {
  const cssVariables: Record<string, string> = {};

  // Colors
  cssVariables['--color-primary'] = theme.colors.primary;
  cssVariables['--color-secondary'] = theme.colors.secondary;
  cssVariables['--color-accent'] = theme.colors.accent;
  cssVariables['--color-background'] = theme.colors.background;
  cssVariables['--color-surface'] = theme.colors.surface;
  cssVariables['--color-overlay'] = theme.colors.overlay;
  
  // Text colors
  cssVariables['--color-text-primary'] = theme.colors.text.primary;
  cssVariables['--color-text-secondary'] = theme.colors.text.secondary;
  cssVariables['--color-text-accent'] = theme.colors.text.accent;
  cssVariables['--color-text-inverse'] = theme.colors.text.inverse;
  
  // Status colors
  cssVariables['--color-success'] = theme.colors.success;
  cssVariables['--color-warning'] = theme.colors.warning;
  cssVariables['--color-error'] = theme.colors.error;
  cssVariables['--color-info'] = theme.colors.info;
  
  // Border and divider colors
  cssVariables['--color-border'] = theme.colors.border;
  cssVariables['--color-divider'] = theme.colors.divider;
  
  // Interactive state colors
  cssVariables['--color-hover'] = theme.colors.hover;
  cssVariables['--color-active'] = theme.colors.active;
  cssVariables['--color-focus'] = theme.colors.focus;
  cssVariables['--color-disabled'] = theme.colors.disabled;

  // Typography
  cssVariables['--font-family-sans'] = theme.typography.fontFamily.sans;
  cssVariables['--font-family-serif'] = theme.typography.fontFamily.serif;
  cssVariables['--font-family-mono'] = theme.typography.fontFamily.mono;
  cssVariables['--font-family-display'] = theme.typography.fontFamily.display;
  
  // Font sizes
  Object.entries(theme.typography.fontSize).forEach(([key, value]) => {
    cssVariables[`--font-size-${key}`] = value;
  });
  
  // Font weights
  Object.entries(theme.typography.fontWeight).forEach(([key, value]) => {
    cssVariables[`--font-weight-${key}`] = value.toString();
  });
  
  // Line heights
  Object.entries(theme.typography.lineHeight).forEach(([key, value]) => {
    cssVariables[`--line-height-${key}`] = value.toString();
  });
  
  // Letter spacing
  Object.entries(theme.typography.letterSpacing).forEach(([key, value]) => {
    cssVariables[`--letter-spacing-${key}`] = value;
  });

  // Spacing
  Object.entries(theme.spacing.borderRadius).forEach(([key, value]) => {
    cssVariables[`--border-radius-${key}`] = value;
  });
  
  Object.entries(theme.spacing.spacing).forEach(([key, value]) => {
    cssVariables[`--spacing-${key}`] = value;
  });
  
  Object.entries(theme.spacing.shadows).forEach(([key, value]) => {
    cssVariables[`--shadow-${key}`] = value;
  });

  // Glassmorphism effects
  cssVariables['--glass-blur'] = theme.effects.glassmorphism.blur;
  cssVariables['--glass-opacity'] = theme.effects.glassmorphism.opacity.toString();
  cssVariables['--glass-border'] = theme.effects.glassmorphism.border;

  // Animation durations
  Object.entries(theme.effects.animation.duration).forEach(([key, value]) => {
    cssVariables[`--duration-${key}`] = value;
  });
  
  // Animation easing
  Object.entries(theme.effects.animation.easing).forEach(([key, value]) => {
    cssVariables[`--easing-${key}`] = value;
  });

  // Special effects
  if (theme.effects.specialEffects.glowIntensity !== undefined) {
    cssVariables['--glow-intensity'] = theme.effects.specialEffects.glowIntensity.toString();
  }
  if (theme.effects.specialEffects.particleCount !== undefined) {
    cssVariables['--particle-count'] = theme.effects.specialEffects.particleCount.toString();
  }
  if (theme.effects.specialEffects.waveSpeed !== undefined) {
    cssVariables['--wave-speed'] = theme.effects.specialEffects.waveSpeed.toString();
  }
  if (theme.effects.specialEffects.pulseRate !== undefined) {
    cssVariables['--pulse-rate'] = theme.effects.specialEffects.pulseRate.toString();
  }
  if (theme.effects.specialEffects.snowflakeCount !== undefined) {
    cssVariables['--snowflake-count'] = theme.effects.specialEffects.snowflakeCount.toString();
  }
  if (theme.effects.specialEffects.dataStreamCount !== undefined) {
    cssVariables['--data-stream-count'] = theme.effects.specialEffects.dataStreamCount.toString();
  }

  return cssVariables;
}

/**
 * Applies CSS custom properties to the document root
 */
export function applyCSSVariables(theme: Theme): void {
  const cssVariables = themeToCSS(theme);
  const root = document.documentElement;
  
  Object.entries(cssVariables).forEach(([property, value]) => {
    root.style.setProperty(property, value);
  });
}

/**
 * Removes all theme CSS custom properties from the document root
 */
export function clearCSSVariables(): void {
  const root = document.documentElement;
  const style = root.style;
  
  // Remove all CSS variables that start with our prefixes
  const prefixes = [
    '--color-',
    '--font-',
    '--border-radius-',
    '--spacing-',
    '--shadow-',
    '--glass-',
    '--duration-',
    '--easing-',
    '--glow-',
    '--particle-',
    '--wave-',
    '--pulse-',
    '--snowflake-',
    '--data-stream-'
  ];
  
  for (let i = style.length - 1; i >= 0; i--) {
    const property = style[i];
    if (prefixes.some(prefix => property.startsWith(prefix))) {
      style.removeProperty(property);
    }
  }
}

/**
 * Generates CSS class names based on theme features
 */
export function getThemeClassNames(theme: Theme): string[] {
  const classNames: string[] = [];
  
  // Add theme ID class
  classNames.push(`theme-${theme.id}`);
  
  // Add category class
  classNames.push(`theme-category-${theme.category}`);
  
  // Add feature classes
  if (theme.features.hasAnimations) classNames.push('theme-has-animations');
  if (theme.features.hasGlassmorphism) classNames.push('theme-has-glassmorphism');
  if (theme.features.hasParticles) classNames.push('theme-has-particles');
  if (theme.features.hasGradients) classNames.push('theme-has-gradients');
  if (theme.features.supportsHighContrast) classNames.push('theme-supports-high-contrast');
  if (theme.features.supportsLargeText) classNames.push('theme-supports-large-text');
  
  // Add accessibility classes
  classNames.push(`theme-contrast-${theme.accessibility.colorContrast}`);
  classNames.push(`theme-motion-${theme.accessibility.motionSafety}`);
  classNames.push(`theme-cognitive-${theme.accessibility.cognitiveLoad}`);
  
  return classNames;
}

/**
 * Updates the document body class list with theme classes
 */
export function applyThemeClasses(theme: Theme): void {
  const body = document.body;
  
  // Remove existing theme classes
  const existingClasses = Array.from(body.classList).filter(
    className => className.startsWith('theme-')
  );
  body.classList.remove(...existingClasses);
  
  // Add new theme classes
  const newClasses = getThemeClassNames(theme);
  body.classList.add(...newClasses);
}

/**
 * Complete theme application - applies both CSS variables and classes
 */
export function applyTheme(theme: Theme): void {
  applyCSSVariables(theme);
  applyThemeClasses(theme);
} 