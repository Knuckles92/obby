import { Theme, ThemeCategory } from '../types';

// Base typography configuration used across themes
const baseTypography = {
  fontFamily: {
    sans: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
    serif: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
    mono: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
    display: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif'
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem'
  },
  fontWeight: {
    light: 300,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700
  },
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.75
  },
  letterSpacing: {
    tight: '-0.025em',
    normal: '0em',
    wide: '0.025em'
  }
};

// Base spacing configuration
const baseSpacing = {
  borderRadius: {
    none: '0',
    sm: '0.125rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px'
  },
  spacing: {
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem'
  },
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    glow: '0 0 20px rgb(59 130 246 / 0.5)'
  }
};

// PROFESSIONAL THEMES
const corporateTheme: Theme = {
  id: 'corporate',
  name: 'Corporate',
  category: 'professional' as ThemeCategory,
  description: 'Clean, professional design perfect for business environments',
  preview: '/themes/corporate-preview.jpg',
  colors: {
    primary: '#1e40af',
    secondary: '#64748b',
    accent: '#3b82f6',
    background: '#ffffff',
    surface: '#f8fafc',
    overlay: '#ffffff',
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
      accent: '#1e40af',
      inverse: '#ffffff'
    },
    success: '#059669',
    warning: '#d97706',
    error: '#dc2626',
    info: '#0284c7',
    border: '#e2e8f0',
    divider: '#f1f5f9',
    hover: '#f1f5f9',
    active: '#e2e8f0',
    focus: '#3b82f6',
    disabled: '#9ca3af'
  },
  typography: baseTypography,
  spacing: baseSpacing,
  effects: {
    glassmorphism: {
      blur: '10px',
      opacity: 0.95,
      border: '1px solid rgba(255, 255, 255, 0.2)'
    },
    animation: {
      duration: {
        fast: '150ms',
        normal: '300ms',
        slow: '500ms'
      },
      easing: {
        ease: 'ease',
        easeIn: 'ease-in',
        easeOut: 'ease-out',
        easeInOut: 'ease-in-out'
      }
    },
    specialEffects: {}
  },
  features: {
    hasAnimations: false,
    hasGlassmorphism: true,
    hasParticles: false,
    hasGradients: false,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'high',
    cognitiveLoad: 'low'
  }
};

const minimalTheme: Theme = {
  id: 'minimal',
  name: 'Minimal',
  category: 'professional' as ThemeCategory,
  description: 'Ultra-clean design with maximum focus on content',
  preview: '/themes/minimal-preview.jpg',
  colors: {
    primary: '#000000',
    secondary: '#666666',
    accent: '#333333',
    background: '#ffffff',
    surface: '#fafafa',
    overlay: '#ffffff',
    text: {
      primary: '#000000',
      secondary: '#666666',
      accent: '#000000',
      inverse: '#ffffff'
    },
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    border: '#e5e5e5',
    divider: '#f5f5f5',
    hover: '#f5f5f5',
    active: '#e5e5e5',
    focus: '#000000',
    disabled: '#a3a3a3'
  },
  typography: {
    ...baseTypography,
    fontFamily: {
      ...baseTypography.fontFamily,
      sans: '"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif'
    }
  },
  spacing: {
    ...baseSpacing,
    shadows: {
      sm: '0 1px 2px 0 rgb(0 0 0 / 0.02)',
      md: '0 2px 4px 0 rgb(0 0 0 / 0.04)',
      lg: '0 4px 8px 0 rgb(0 0 0 / 0.06)',
      xl: '0 8px 16px 0 rgb(0 0 0 / 0.08)',
      inner: 'inset 0 1px 2px 0 rgb(0 0 0 / 0.02)',
      glow: 'none'
    }
  },
  effects: {
    glassmorphism: {
      blur: '0px',
      opacity: 1,
      border: '1px solid #e5e5e5'
    },
    animation: {
      duration: {
        fast: '100ms',
        normal: '200ms',
        slow: '300ms'
      },
      easing: {
        ease: 'ease',
        easeIn: 'ease-in',
        easeOut: 'ease-out',
        easeInOut: 'ease-in-out'
      }
    },
    specialEffects: {}
  },
  features: {
    hasAnimations: false,
    hasGlassmorphism: false,
    hasParticles: false,
    hasGradients: false,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'high',
    cognitiveLoad: 'low'
  }
};

const classicTheme: Theme = {
  id: 'classic',
  name: 'Classic',
  category: 'professional' as ThemeCategory,
  description: 'Timeless design with traditional elements and warm tones',
  preview: '/themes/classic-preview.jpg',
  colors: {
    primary: '#8b5a3c',
    secondary: '#6b5b73',
    accent: '#c69c6d',
    background: '#faf7f2',
    surface: '#f5f1e8',
    overlay: '#ffffff',
    text: {
      primary: '#2d2926',
      secondary: '#5d5753',
      accent: '#8b5a3c',
      inverse: '#faf7f2'
    },
    success: '#6d8b3c',
    warning: '#c69c3c',
    error: '#c65d3c',
    info: '#5a7d8b',
    border: '#e1d7c6',
    divider: '#ede4d3',
    hover: '#ede4d3',
    active: '#e1d7c6',
    focus: '#8b5a3c',
    disabled: '#9e9691'
  },
  typography: {
    ...baseTypography,
    fontFamily: {
      ...baseTypography.fontFamily,
      serif: '"Crimson Text", ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
      display: '"Crimson Text", ui-serif, Georgia, Cambria, "Times New Roman", Times, serif'
    }
  },
  spacing: baseSpacing,
  effects: {
    glassmorphism: {
      blur: '8px',
      opacity: 0.9,
      border: '1px solid rgba(139, 90, 60, 0.2)'
    },
    animation: {
      duration: {
        fast: '200ms',
        normal: '400ms',
        slow: '600ms'
      },
      easing: {
        ease: 'ease',
        easeIn: 'ease-in',
        easeOut: 'ease-out',
        easeInOut: 'ease-in-out'
      }
    },
    specialEffects: {}
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: false,
    hasGradients: true,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'medium',
    motionSafety: 'medium',
    cognitiveLoad: 'low'
  }
};

// CREATIVE THEMES
const cyberpunkTheme: Theme = {
  id: 'cyberpunk',
  name: 'Cyberpunk',
  category: 'creative' as ThemeCategory,
  description: 'Futuristic neon aesthetic with high-tech visual effects',
  preview: '/themes/cyberpunk-preview.jpg',
  colors: {
    primary: '#00ff41',
    secondary: '#ff0080',
    accent: '#00d4ff',
    background: '#0a0a0a',
    surface: '#1a1a2e',
    overlay: 'rgba(26, 26, 46, 0.95)',
    text: {
      primary: '#00ff41',
      secondary: '#8cc8ff',
      accent: '#ff0080',
      inverse: '#0a0a0a'
    },
    success: '#00ff41',
    warning: '#ffaa00',
    error: '#ff0080',
    info: '#00d4ff',
    border: '#16213e',
    divider: '#0f3460',
    hover: '#16213e',
    active: '#0f3460',
    focus: '#00ff41',
    disabled: '#4a5568'
  },
  typography: {
    ...baseTypography,
    fontFamily: {
      ...baseTypography.fontFamily,
      sans: '"Orbitron", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
      mono: '"Fira Code", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
      display: '"Orbitron", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace'
    }
  },
  spacing: {
    ...baseSpacing,
    shadows: {
      sm: '0 0 10px rgba(0, 255, 65, 0.3)',
      md: '0 0 20px rgba(0, 255, 65, 0.4)',
      lg: '0 0 30px rgba(0, 255, 65, 0.5)',
      xl: '0 0 40px rgba(0, 255, 65, 0.6)',
      inner: 'inset 0 0 10px rgba(0, 255, 65, 0.2)',
      glow: '0 0 30px rgba(0, 255, 65, 0.8)'
    }
  },
  effects: {
    glassmorphism: {
      blur: '15px',
      opacity: 0.1,
      border: '1px solid rgba(0, 255, 65, 0.3)'
    },
    animation: {
      duration: {
        fast: '100ms',
        normal: '300ms',
        slow: '800ms'
      },
      easing: {
        ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
        easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
        easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
        easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)'
      }
    },
    specialEffects: {
      glowIntensity: 80,
      dataStreamCount: 12,
      pulseRate: 2
    }
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: true,
    hasGradients: true,
    supportsHighContrast: false,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'low',
    motionSafety: 'low',
    cognitiveLoad: 'high'
  }
};

const forestTheme: Theme = {
  id: 'forest',
  name: 'Forest',
  category: 'creative' as ThemeCategory,
  description: 'Nature-inspired design with organic textures and calming greens',
  preview: '/themes/forest-preview.jpg',
  colors: {
    primary: '#16a34a',
    secondary: '#059669',
    accent: '#65a30d',
    background: '#f0f7f0',
    surface: '#e6f3e6',
    overlay: 'rgba(240, 247, 240, 0.95)',
    text: {
      primary: '#1f2937',
      secondary: '#374151',
      accent: '#16a34a',
      inverse: '#f0f7f0'
    },
    success: '#16a34a',
    warning: '#ca8a04',
    error: '#dc2626',
    info: '#0284c7',
    border: '#bbd6bb',
    divider: '#d0e6d0',
    hover: '#d0e6d0',
    active: '#bbd6bb',
    focus: '#16a34a',
    disabled: '#9ca3af'
  },
  typography: {
    ...baseTypography,
    fontFamily: {
      ...baseTypography.fontFamily,
      sans: '"Nunito", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif'
    }
  },
  spacing: {
    ...baseSpacing,
    borderRadius: {
      none: '0',
      sm: '0.25rem',
      md: '0.5rem',
      lg: '0.75rem',
      xl: '1rem',
      full: '9999px'
    },
    shadows: {
      sm: '0 2px 4px 0 rgba(22, 163, 74, 0.1)',
      md: '0 4px 6px -1px rgba(22, 163, 74, 0.15), 0 2px 4px -2px rgba(22, 163, 74, 0.1)',
      lg: '0 10px 15px -3px rgba(22, 163, 74, 0.2), 0 4px 6px -4px rgba(22, 163, 74, 0.1)',
      xl: '0 20px 25px -5px rgba(22, 163, 74, 0.25), 0 8px 10px -6px rgba(22, 163, 74, 0.1)',
      inner: 'inset 0 2px 4px 0 rgba(22, 163, 74, 0.05)',
      glow: '0 0 20px rgba(22, 163, 74, 0.4)'
    }
  },
  effects: {
    glassmorphism: {
      blur: '12px',
      opacity: 0.85,
      border: '1px solid rgba(22, 163, 74, 0.2)'
    },
    animation: {
      duration: {
        fast: '200ms',
        normal: '500ms',
        slow: '1000ms'
      },
      easing: {
        ease: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        easeIn: 'cubic-bezier(0.55, 0.085, 0.68, 0.53)',
        easeOut: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        easeInOut: 'cubic-bezier(0.645, 0.045, 0.355, 1)'
      }
    },
    specialEffects: {
      particleCount: 20,
      waveSpeed: 0.5
    }
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: true,
    hasGradients: true,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'medium',
    cognitiveLoad: 'medium'
  }
};

const oceanTheme: Theme = {
  id: 'ocean',
  name: 'Ocean',
  category: 'creative' as ThemeCategory,
  description: 'Deep blue aquatic theme with fluid animations and wave effects',
  preview: '/themes/ocean-preview.jpg',
  colors: {
    primary: '#0ea5e9',
    secondary: '#0284c7',
    accent: '#06b6d4',
    background: '#f0f9ff',
    surface: '#e0f2fe',
    overlay: 'rgba(240, 249, 255, 0.9)',
    text: {
      primary: '#0c4a6e',
      secondary: '#075985',
      accent: '#0ea5e9',
      inverse: '#f0f9ff'
    },
    success: '#059669',
    warning: '#d97706',
    error: '#dc2626',
    info: '#0ea5e9',
    border: '#7dd3fc',
    divider: '#bae6fd',
    hover: '#bae6fd',
    active: '#7dd3fc',
    focus: '#0ea5e9',
    disabled: '#94a3b8'
  },
  typography: baseTypography,
  spacing: {
    ...baseSpacing,
    shadows: {
      sm: '0 2px 4px 0 rgba(14, 165, 233, 0.1)',
      md: '0 4px 6px -1px rgba(14, 165, 233, 0.15), 0 2px 4px -2px rgba(14, 165, 233, 0.1)',
      lg: '0 10px 15px -3px rgba(14, 165, 233, 0.2), 0 4px 6px -4px rgba(14, 165, 233, 0.1)',
      xl: '0 20px 25px -5px rgba(14, 165, 233, 0.25), 0 8px 10px -6px rgba(14, 165, 233, 0.1)',
      inner: 'inset 0 2px 4px 0 rgba(14, 165, 233, 0.05)',
      glow: '0 0 25px rgba(14, 165, 233, 0.5)'
    }
  },
  effects: {
    glassmorphism: {
      blur: '15px',
      opacity: 0.7,
      border: '1px solid rgba(14, 165, 233, 0.3)'
    },
    animation: {
      duration: {
        fast: '300ms',
        normal: '600ms',
        slow: '1200ms'
      },
      easing: {
        ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
        easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
        easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
        easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)'
      }
    },
    specialEffects: {
      waveSpeed: 1.5,
      particleCount: 15
    }
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: true,
    hasGradients: true,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'medium',
    cognitiveLoad: 'medium'
  }
};

// ACCESSIBLE THEMES
const highContrastTheme: Theme = {
  id: 'high-contrast',
  name: 'High Contrast',
  category: 'accessible' as ThemeCategory,
  description: 'Maximum contrast design for improved visibility and readability',
  preview: '/themes/high-contrast-preview.jpg',
  colors: {
    primary: '#000000',
    secondary: '#333333',
    accent: '#ffffff',
    background: '#ffffff',
    surface: '#f8f8f8',
    overlay: '#ffffff',
    text: {
      primary: '#000000',
      secondary: '#000000',
      accent: '#ffffff',
      inverse: '#ffffff'
    },
    success: '#008000',
    warning: '#ff8000',
    error: '#ff0000',
    info: '#0000ff',
    border: '#000000',
    divider: '#000000',
    hover: '#f0f0f0',
    active: '#e0e0e0',
    focus: '#ff0000',
    disabled: '#808080'
  },
  typography: {
    ...baseTypography,
    fontWeight: {
      light: 400,
      normal: 500,
      medium: 600,
      semibold: 700,
      bold: 800
    }
  },
  spacing: {
    ...baseSpacing,
    shadows: {
      sm: '0 2px 4px 0 rgb(0 0 0 / 0.3)',
      md: '0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
      lg: '0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.3)',
      xl: '0 20px 25px -5px rgb(0 0 0 / 0.6), 0 8px 10px -6px rgb(0 0 0 / 0.3)',
      inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.2)',
      glow: 'none'
    }
  },
  effects: {
    glassmorphism: {
      blur: '0px',
      opacity: 1,
      border: '2px solid #000000'
    },
    animation: {
      duration: {
        fast: '0ms',
        normal: '0ms',
        slow: '0ms'
      },
      easing: {
        ease: 'ease',
        easeIn: 'ease-in',
        easeOut: 'ease-out',
        easeInOut: 'ease-in-out'
      }
    },
    specialEffects: {}
  },
  features: {
    hasAnimations: false,
    hasGlassmorphism: false,
    hasParticles: false,
    hasGradients: false,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'high',
    cognitiveLoad: 'low'
  }
};

const largeTextTheme: Theme = {
  id: 'large-text',
  name: 'Large Text',
  category: 'accessible' as ThemeCategory,
  description: 'Enhanced readability with larger fonts and generous spacing',
  preview: '/themes/large-text-preview.jpg',
  colors: {
    primary: '#1e40af',
    secondary: '#64748b',
    accent: '#3b82f6',
    background: '#ffffff',
    surface: '#f8fafc',
    overlay: '#ffffff',
    text: {
      primary: '#1e293b',
      secondary: '#475569',
      accent: '#1e40af',
      inverse: '#ffffff'
    },
    success: '#059669',
    warning: '#d97706',
    error: '#dc2626',
    info: '#0284c7',
    border: '#cbd5e1',
    divider: '#e2e8f0',
    hover: '#f1f5f9',
    active: '#e2e8f0',
    focus: '#3b82f6',
    disabled: '#94a3b8'
  },
  typography: {
    ...baseTypography,
    fontSize: {
      xs: '1rem',
      sm: '1.125rem',
      base: '1.25rem',
      lg: '1.5rem',
      xl: '1.75rem',
      '2xl': '2rem',
      '3xl': '2.5rem',
      '4xl': '3rem'
    },
    lineHeight: {
      tight: 1.4,
      normal: 1.6,
      relaxed: 1.8
    }
  },
  spacing: {
    ...baseSpacing,
    spacing: {
      xs: '0.75rem',
      sm: '1rem',
      md: '1.5rem',
      lg: '2rem',
      xl: '3rem',
      '2xl': '4rem',
      '3xl': '5rem'
    }
  },
  effects: {
    glassmorphism: {
      blur: '8px',
      opacity: 0.95,
      border: '1px solid rgba(59, 130, 246, 0.2)'
    },
    animation: {
      duration: {
        fast: '200ms',
        normal: '400ms',
        slow: '600ms'
      },
      easing: {
        ease: 'ease',
        easeIn: 'ease-in',
        easeOut: 'ease-out',
        easeInOut: 'ease-in-out'
      }
    },
    specialEffects: {}
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: false,
    hasGradients: false,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'high',
    cognitiveLoad: 'low'
  }
};

// SPECIAL THEMES
const vintageTheme: Theme = {
  id: 'vintage',
  name: 'Vintage',
  category: 'special' as ThemeCategory,
  description: 'Retro design with warm sepia tones and nostalgic elements',
  preview: '/themes/vintage-preview.jpg',
  colors: {
    primary: '#8b4513',
    secondary: '#a0522d',
    accent: '#cd853f',
    background: '#fdf6e3',
    surface: '#f5ebdc',
    overlay: 'rgba(253, 246, 227, 0.95)',
    text: {
      primary: '#3c2414',
      secondary: '#5d4037',
      accent: '#8b4513',
      inverse: '#fdf6e3'
    },
    success: '#6b8e23',
    warning: '#ff8c00',
    error: '#b22222',
    info: '#4682b4',
    border: '#deb887',
    divider: '#e6d3a3',
    hover: '#e6d3a3',
    active: '#deb887',
    focus: '#8b4513',
    disabled: '#a0a0a0'
  },
  typography: {
    ...baseTypography,
    fontFamily: {
      ...baseTypography.fontFamily,
      serif: '"Playfair Display", ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
      display: '"Playfair Display", ui-serif, Georgia, Cambria, "Times New Roman", Times, serif'
    }
  },
  spacing: {
    ...baseSpacing,
    borderRadius: {
      none: '0',
      sm: '0.125rem',
      md: '0.25rem',
      lg: '0.375rem',
      xl: '0.5rem',
      full: '9999px'
    },
    shadows: {
      sm: '0 1px 3px 0 rgba(139, 69, 19, 0.2)',
      md: '0 4px 6px -1px rgba(139, 69, 19, 0.25), 0 2px 4px -2px rgba(139, 69, 19, 0.15)',
      lg: '0 10px 15px -3px rgba(139, 69, 19, 0.3), 0 4px 6px -4px rgba(139, 69, 19, 0.15)',
      xl: '0 20px 25px -5px rgba(139, 69, 19, 0.35), 0 8px 10px -6px rgba(139, 69, 19, 0.15)',
      inner: 'inset 0 2px 4px 0 rgba(139, 69, 19, 0.1)',
      glow: '0 0 15px rgba(205, 133, 63, 0.4)'
    }
  },
  effects: {
    glassmorphism: {
      blur: '6px',
      opacity: 0.8,
      border: '1px solid rgba(139, 69, 19, 0.3)'
    },
    animation: {
      duration: {
        fast: '250ms',
        normal: '500ms',
        slow: '750ms'
      },
      easing: {
        ease: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        easeIn: 'cubic-bezier(0.55, 0.085, 0.68, 0.53)',
        easeOut: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        easeInOut: 'cubic-bezier(0.645, 0.045, 0.355, 1)'
      }
    },
    specialEffects: {}
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: false,
    hasGradients: true,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'medium',
    motionSafety: 'medium',
    cognitiveLoad: 'low'
  }
};

const neonTheme: Theme = {
  id: 'neon',
  name: 'Neon',
  category: 'special' as ThemeCategory,
  description: 'Vibrant neon lights theme with electric glow effects',
  preview: '/themes/neon-preview.jpg',
  colors: {
    primary: '#ff00ff',
    secondary: '#00ffff',
    accent: '#ffff00',
    background: '#000011',
    surface: '#1a1a2e',
    overlay: 'rgba(26, 26, 46, 0.9)',
    text: {
      primary: '#ff00ff',
      secondary: '#00ffff',
      accent: '#ffff00',
      inverse: '#000011'
    },
    success: '#00ff00',
    warning: '#ffaa00',
    error: '#ff0040',
    info: '#00aaff',
    border: '#ff00ff',
    divider: '#00ffff',
    hover: '#330066',
    active: '#660099',
    focus: '#ffff00',
    disabled: '#666666'
  },
  typography: {
    ...baseTypography,
    fontFamily: {
      ...baseTypography.fontFamily,
      sans: '"Audiowide", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
      display: '"Audiowide", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif'
    }
  },
  spacing: {
    ...baseSpacing,
    shadows: {
      sm: '0 0 10px currentColor',
      md: '0 0 20px currentColor, 0 0 30px currentColor',
      lg: '0 0 30px currentColor, 0 0 60px currentColor',
      xl: '0 0 40px currentColor, 0 0 70px currentColor, 0 0 100px currentColor',
      inner: 'inset 0 0 10px currentColor',
      glow: '0 0 50px currentColor, 0 0 100px currentColor'
    }
  },
  effects: {
    glassmorphism: {
      blur: '20px',
      opacity: 0.1,
      border: '1px solid rgba(255, 0, 255, 0.5)'
    },
    animation: {
      duration: {
        fast: '150ms',
        normal: '400ms',
        slow: '1000ms'
      },
      easing: {
        ease: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        easeIn: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        easeOut: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        easeInOut: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
      }
    },
    specialEffects: {
      glowIntensity: 100,
      pulseRate: 3
    }
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: true,
    hasGradients: true,
    supportsHighContrast: false,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'low',
    motionSafety: 'low',
    cognitiveLoad: 'high'
  }
};

const winterTheme: Theme = {
  id: 'winter',
  name: 'Winter',
  category: 'special' as ThemeCategory,
  description: 'Cool winter theme with icy blues and snowflake animations',
  preview: '/themes/winter-preview.jpg',
  colors: {
    primary: '#1e3a8a',
    secondary: '#1e40af',
    accent: '#3b82f6',
    background: '#f8fafc',
    surface: '#f1f5f9',
    overlay: 'rgba(248, 250, 252, 0.95)',
    text: {
      primary: '#1e293b',
      secondary: '#475569',
      accent: '#1e3a8a',
      inverse: '#f8fafc'
    },
    success: '#059669',
    warning: '#d97706',
    error: '#dc2626',
    info: '#0284c7',
    border: '#cbd5e1',
    divider: '#e2e8f0',
    hover: '#e2e8f0',
    active: '#cbd5e1',
    focus: '#3b82f6',
    disabled: '#94a3b8'
  },
  typography: baseTypography,
  spacing: {
    ...baseSpacing,
    shadows: {
      sm: '0 1px 3px 0 rgba(30, 58, 138, 0.1)',
      md: '0 4px 6px -1px rgba(30, 58, 138, 0.15), 0 2px 4px -2px rgba(30, 58, 138, 0.1)',
      lg: '0 10px 15px -3px rgba(30, 58, 138, 0.2), 0 4px 6px -4px rgba(30, 58, 138, 0.1)',
      xl: '0 20px 25px -5px rgba(30, 58, 138, 0.25), 0 8px 10px -6px rgba(30, 58, 138, 0.1)',
      inner: 'inset 0 2px 4px 0 rgba(30, 58, 138, 0.05)',
      glow: '0 0 20px rgba(59, 130, 246, 0.3)'
    }
  },
  effects: {
    glassmorphism: {
      blur: '12px',
      opacity: 0.8,
      border: '1px solid rgba(59, 130, 246, 0.2)'
    },
    animation: {
      duration: {
        fast: '300ms',
        normal: '600ms',
        slow: '1200ms'
      },
      easing: {
        ease: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        easeIn: 'cubic-bezier(0.55, 0.085, 0.68, 0.53)',
        easeOut: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        easeInOut: 'cubic-bezier(0.645, 0.045, 0.355, 1)'
      }
    },
    specialEffects: {
      snowflakeCount: 50,
      waveSpeed: 0.3
    }
  },
  features: {
    hasAnimations: true,
    hasGlassmorphism: true,
    hasParticles: true,
    hasGradients: true,
    supportsHighContrast: true,
    supportsLargeText: true
  },
  accessibility: {
    colorContrast: 'high',
    motionSafety: 'medium',
    cognitiveLoad: 'medium'
  }
};

// Export all themes
export const themes: Theme[] = [
  // Professional
  corporateTheme,
  minimalTheme,
  classicTheme,
  // Creative
  cyberpunkTheme,
  forestTheme,
  oceanTheme,
  // Accessible
  highContrastTheme,
  largeTextTheme,
  // Special
  vintageTheme,
  neonTheme,
  winterTheme
];

// Export themes by category
export const themeCategories: Record<ThemeCategory, Theme[]> = {
  professional: [corporateTheme, minimalTheme, classicTheme],
  creative: [cyberpunkTheme, forestTheme, oceanTheme],
  accessible: [highContrastTheme, largeTextTheme],
  special: [vintageTheme, neonTheme, winterTheme]
};

// Default theme
export const defaultTheme = corporateTheme;

// Theme lookup helper
export const getThemeById = (id: string): Theme | undefined => {
  return themes.find(theme => theme.id === id);
}; 