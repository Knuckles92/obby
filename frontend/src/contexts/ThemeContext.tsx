import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Theme, ThemeContextValue, ThemePreferences, ThemeCategory } from '../types';
import { themes, themeCategories, defaultTheme, getThemeById } from '../themes';
import { applyTheme } from '../themes/css-variables';

// Create the context
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

// Default preferences
const defaultPreferences: ThemePreferences = {
  preferredCategory: 'professional',
  autoSwitchByTime: false,
  dayTheme: 'corporate',
  nightTheme: 'cyberpunk',
  reduceMotion: false,
  highContrast: false,
  largeText: false,
  customCssVariables: {}
};

interface ThemeProviderProps {
  children: ReactNode;
  initialTheme?: string;
}

export function ThemeProvider({ children, initialTheme }: ThemeProviderProps) {
  const [currentTheme, setCurrentTheme] = useState<Theme>(defaultTheme);
  const [preferences, setPreferences] = useState<ThemePreferences>(defaultPreferences);
  const [isLoading, setIsLoading] = useState(true);

  // Load preferences from localStorage on mount
  useEffect(() => {
    const loadPreferences = () => {
      try {
        const savedPreferences = localStorage.getItem('obby-theme-preferences');
        if (savedPreferences) {
          const parsed = JSON.parse(savedPreferences);
          setPreferences({ ...defaultPreferences, ...parsed });
        }

        // Load saved theme or use initial theme
        const savedThemeId = localStorage.getItem('obby-current-theme');
        const themeId = initialTheme || savedThemeId || defaultTheme.id;
        const theme = getThemeById(themeId) || defaultTheme;
        
        setCurrentTheme(theme);
        applyTheme(theme);
      } catch (error) {
        console.error('Error loading theme preferences:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadPreferences();
  }, [initialTheme]);

  // Save preferences to localStorage whenever they change
  useEffect(() => {
    if (!isLoading) {
      try {
        localStorage.setItem('obby-theme-preferences', JSON.stringify(preferences));
      } catch (error) {
        console.error('Error saving theme preferences:', error);
      }
    }
  }, [preferences, isLoading]);

  // Auto-switch themes based on time if enabled
  useEffect(() => {
    if (!preferences.autoSwitchByTime) return;

    const checkTimeBasedTheme = () => {
      const hour = new Date().getHours();
      const isDayTime = hour >= 6 && hour < 18;
      const targetThemeId = isDayTime ? preferences.dayTheme : preferences.nightTheme;
      
      if (currentTheme.id !== targetThemeId) {
        const targetTheme = getThemeById(targetThemeId);
        if (targetTheme) {
          setTheme(targetThemeId);
        }
      }
    };

    checkTimeBasedTheme();
    
    // Check every hour
    const interval = setInterval(checkTimeBasedTheme, 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, [preferences.autoSwitchByTime, preferences.dayTheme, preferences.nightTheme, currentTheme.id]);

  // Apply accessibility preferences
  useEffect(() => {
    const body = document.body;
    
    // Handle reduced motion preference
    if (preferences.reduceMotion) {
      body.classList.add('reduce-motion');
    } else {
      body.classList.remove('reduce-motion');
    }

    // Handle high contrast preference
    if (preferences.highContrast) {
      body.classList.add('force-high-contrast');
    } else {
      body.classList.remove('force-high-contrast');
    }

    // Handle large text preference
    if (preferences.largeText) {
      body.classList.add('force-large-text');
    } else {
      body.classList.remove('force-large-text');
    }

    // Apply custom CSS variables
    const root = document.documentElement;
    Object.entries(preferences.customCssVariables).forEach(([property, value]) => {
      if (property.startsWith('--')) {
        root.style.setProperty(property, value);
      }
    });
  }, [preferences.reduceMotion, preferences.highContrast, preferences.largeText, preferences.customCssVariables]);

  const setTheme = (themeId: string) => {
    const theme = getThemeById(themeId);
    if (!theme) {
      console.error(`Theme with id "${themeId}" not found`);
      return;
    }

    setCurrentTheme(theme);
    applyTheme(theme);
    
    // Save to localStorage
    try {
      localStorage.setItem('obby-current-theme', themeId);
    } catch (error) {
      console.error('Error saving current theme:', error);
    }
  };

  const updatePreferences = (newPreferences: Partial<ThemePreferences>) => {
    setPreferences(prev => ({ ...prev, ...newPreferences }));
  };

  const contextValue: ThemeContextValue = {
    currentTheme,
    setTheme,
    availableThemes: themes,
    themeCategories,
    isLoading,
    preferences,
    updatePreferences
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

// Hook to use the theme context
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// Hook to get current theme ID
export function useCurrentThemeId(): string {
  const { currentTheme } = useTheme();
  return currentTheme.id;
}

// Hook to check if a specific theme feature is available
export function useThemeFeature(feature: keyof Theme['features']): boolean {
  const { currentTheme } = useTheme();
  return currentTheme.features[feature];
}

// Hook to get theme-aware CSS classes
export function useThemeClasses(...baseClasses: string[]): string {
  const { currentTheme } = useTheme();
  
  const themeClasses = [
    `theme-${currentTheme.id}`,
    `theme-category-${currentTheme.category}`,
    ...baseClasses
  ];

  return themeClasses.join(' ');
}

// Hook for conditional rendering based on theme category
export function useThemeCategory(): ThemeCategory {
  const { currentTheme } = useTheme();
  return currentTheme.category;
}

// Hook to get themes by category
export function useThemesByCategory(category?: ThemeCategory): Theme[] {
  const { themeCategories, availableThemes } = useTheme();
  
  if (!category) {
    return availableThemes;
  }
  
  return themeCategories[category] || [];
}

// Hook for theme switching with validation
export function useThemeSwitch() {
  const { setTheme, availableThemes } = useTheme();
  
  const switchToTheme = (themeId: string): boolean => {
    const theme = availableThemes.find(t => t.id === themeId);
    if (theme) {
      setTheme(themeId);
      return true;
    }
    return false;
  };
  
  const switchToCategory = (category: ThemeCategory): boolean => {
    const { themeCategories } = useTheme();
    const themesInCategory = themeCategories[category];
    if (themesInCategory && themesInCategory.length > 0) {
      setTheme(themesInCategory[0].id);
      return true;
    }
    return false;
  };
  
  const switchToRandom = (): void => {
    const randomIndex = Math.floor(Math.random() * availableThemes.length);
    setTheme(availableThemes[randomIndex].id);
  };
  
  return {
    switchToTheme,
    switchToCategory,
    switchToRandom
  };
}

// Hook for accessibility-aware theme selection
export function useAccessibleTheme() {
  const { availableThemes, setTheme } = useTheme();
  
  const getHighContrastThemes = (): Theme[] => {
    return availableThemes.filter(theme => 
      theme.accessibility.colorContrast === 'high' || 
      theme.features.supportsHighContrast
    );
  };
  
  const getMotionSafeThemes = (): Theme[] => {
    return availableThemes.filter(theme => 
      theme.accessibility.motionSafety === 'high'
    );
  };
  
  const getLowCognitiveLoadThemes = (): Theme[] => {
    return availableThemes.filter(theme => 
      theme.accessibility.cognitiveLoad === 'low'
    );
  };
  
  const switchToAccessibleTheme = (): void => {
    const accessibleThemes = getHighContrastThemes().filter(theme =>
      theme.accessibility.motionSafety === 'high' &&
      theme.accessibility.cognitiveLoad === 'low'
    );
    
    if (accessibleThemes.length > 0) {
      setTheme(accessibleThemes[0].id);
    }
  };
  
  return {
    getHighContrastThemes,
    getMotionSafeThemes,
    getLowCognitiveLoadThemes,
    switchToAccessibleTheme
  };
} 