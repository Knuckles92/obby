import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Palette,
  Check,
  Monitor,
  Eye,
  Zap,
  Sparkles,
  Accessibility,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { 
  useTheme, 
  useThemesByCategory, 
  useThemeClasses,
  useThemeFeature 
} from '../contexts/ThemeContext';
import { Theme, ThemeCategory } from '../types';

interface ThemeSwitcherProps {
  className?: string;
  showCategories?: boolean;
  showPreview?: boolean;
  compact?: boolean;
}

const categoryIcons: Record<ThemeCategory, React.ComponentType<any>> = {
  professional: Monitor,
  creative: Sparkles,
  accessible: Accessibility,
  special: Zap
};

const categoryDescriptions: Record<ThemeCategory, string> = {
  professional: 'Clean, business-focused designs',
  creative: 'Vibrant, artistic themes with animations',
  accessible: 'High contrast and large text options',
  special: 'Unique themes with special effects'
};

export default function ThemeSwitcher({
  className = '',
  showCategories = true,
  showPreview = true,
  compact = false
}: ThemeSwitcherProps) {
  const { currentTheme, setTheme, preferences, updatePreferences } = useTheme();
  const [selectedCategory, setSelectedCategory] = useState<ThemeCategory>('professional');
  const [isOpen, setIsOpen] = useState(false);
  const themesInCategory = useThemesByCategory(selectedCategory);
  const hasGlassmorphism = useThemeFeature('hasGlassmorphism');
  const switcherClasses = useThemeClasses('theme-switcher', className);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });

  // Update dropdown position when opened or category changes
  useEffect(() => {
    const updatePosition = () => {
      if (isOpen && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDropdownPosition({
          top: rect.bottom + 4,
          left: rect.left,
          width: rect.width
        });
      }
    };

    updatePosition();

    if (isOpen) {
      // Update position on scroll or resize
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);

      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [isOpen, selectedCategory]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      // Check if click is outside both the container and the dropdown
      if (
        containerRef.current && !containerRef.current.contains(target) &&
        dropdownRef.current && !dropdownRef.current.contains(target)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const containerStyle = {
    position: 'relative' as const,
    minWidth: compact ? '200px' : '300px',
    zIndex: isOpen ? 50 : 10
  };

  const triggerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    padding: 'var(--spacing-sm) var(--spacing-md)',
    backgroundColor: hasGlassmorphism ? 'var(--color-overlay)' : 'var(--color-surface)',
    border: `1px solid var(--color-border)`,
    borderRadius: 'var(--border-radius-md)',
    cursor: 'pointer',
    fontSize: 'var(--font-size-sm)',
    color: 'var(--color-text-primary)',
    transition: `all var(--duration-fast) var(--easing-ease)`,
    backdropFilter: hasGlassmorphism ? 'var(--glass-blur)' : 'none'
  };

  const dropdownStyle = {
    position: 'fixed' as const,
    top: `${dropdownPosition.top}px`,
    left: `${dropdownPosition.left}px`,
    width: `${dropdownPosition.width}px`,
    backgroundColor: hasGlassmorphism ? 'var(--color-overlay)' : 'var(--color-surface)',
    border: `1px solid var(--color-border)`,
    borderRadius: 'var(--border-radius-lg)',
    boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
    zIndex: 9999,
    backdropFilter: hasGlassmorphism ? 'var(--glass-blur)' : 'none',
    maxHeight: '500px',
    overflowY: 'auto' as const,
    overflowX: 'hidden' as const
  };

  const categoryTabStyle = (isActive: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    padding: 'var(--spacing-sm) var(--spacing-md)',
    fontSize: 'var(--font-size-sm)',
    fontWeight: 500,
    backgroundColor: isActive ? 'var(--color-primary)' : 'transparent',
    color: isActive ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
    border: 'none',
    cursor: 'pointer',
    borderRadius: 'var(--border-radius-md)',
    transition: `all var(--duration-fast) var(--easing-ease)`,
    marginRight: 'var(--spacing-xs)',
    flex: 1
  });

  const themeItemStyle = (isSelected: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 'var(--spacing-md)',
    borderBottom: `1px solid var(--color-divider)`,
    cursor: 'pointer',
    transition: `all var(--duration-fast) var(--easing-ease)`,
    backgroundColor: isSelected ? 'var(--color-hover)' : 'transparent'
  });

  const themePreviewStyle = (theme: Theme) => ({
    width: '24px',
    height: '24px',
    borderRadius: 'var(--border-radius-sm)',
    background: `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.accent})`,
    border: `1px solid var(--color-border)`,
    marginRight: 'var(--spacing-sm)'
  });

  const accessibilityOptionsStyle = {
    padding: 'var(--spacing-md)',
    borderTop: `1px solid var(--color-divider)`,
    backgroundColor: 'var(--color-surface)'
  };

  const checkboxStyle = {
    display: 'flex',
    alignItems: 'center',
    marginBottom: 'var(--spacing-sm)',
    fontSize: 'var(--font-size-sm)',
    color: 'var(--color-text-secondary)'
  };

  const handleThemeSelect = (theme: Theme) => {
    setTheme(theme.id);
    setIsOpen(false);
  };

  const handleCategorySelect = (category: ThemeCategory) => {
    setSelectedCategory(category);
  };

  const toggleAccessibilityOption = (option: keyof typeof preferences) => {
    updatePreferences({ [option]: !preferences[option] });
  };

  return (
    <div ref={containerRef} className={switcherClasses} style={containerStyle}>
      <button
        style={triggerStyle}
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--color-focus)';
          e.currentTarget.style.backgroundColor = 'var(--color-hover)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--color-border)';
          e.currentTarget.style.backgroundColor = hasGlassmorphism ? 'var(--color-overlay)' : 'var(--color-surface)';
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Palette style={{ width: '1rem', height: '1rem', marginRight: 'var(--spacing-sm)' }} />
          <span>{compact ? currentTheme.name : `Theme: ${currentTheme.name}`}</span>
        </div>
        {isOpen ? (
          <ChevronUp style={{ width: '1rem', height: '1rem' }} />
        ) : (
          <ChevronDown style={{ width: '1rem', height: '1rem' }} />
        )}
      </button>

      {isOpen && createPortal(
        <div ref={dropdownRef} style={dropdownStyle}>
          {showCategories && !compact && (
            <div style={{ padding: 'var(--spacing-md)', borderBottom: `1px solid var(--color-divider)` }}>
              <div style={{ display: 'flex', marginBottom: 'var(--spacing-sm)' }}>
                {(Object.keys(categoryIcons) as ThemeCategory[]).map((category) => {
                  const Icon = categoryIcons[category];
                  const isActive = selectedCategory === category;
                  
                  return (
                    <button
                      key={category}
                      style={categoryTabStyle(isActive)}
                      onClick={() => handleCategorySelect(category)}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          e.currentTarget.style.backgroundColor = 'var(--color-hover)';
                          e.currentTarget.style.color = 'var(--color-text-primary)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = 'var(--color-text-secondary)';
                        }
                      }}
                    >
                      <Icon style={{ width: '1rem', height: '1rem', marginRight: 'var(--spacing-xs)' }} />
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </button>
                  );
                })}
              </div>
              <p style={{ 
                fontSize: 'var(--font-size-xs)', 
                color: 'var(--color-text-secondary)', 
                margin: 0 
              }}>
                {categoryDescriptions[selectedCategory]}
              </p>
            </div>
          )}

          <div>
            {themesInCategory.map((theme) => {
              const isSelected = theme.id === currentTheme.id;
              
              return (
                <div
                  key={theme.id}
                  style={themeItemStyle(isSelected)}
                  onClick={() => handleThemeSelect(theme)}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = 'var(--color-hover)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    {showPreview && <div style={themePreviewStyle(theme)} />}
                    <div>
                      <div style={{ 
                        fontWeight: 500, 
                        color: 'var(--color-text-primary)',
                        fontSize: 'var(--font-size-sm)'
                      }}>
                        {theme.name}
                      </div>
                      {!compact && (
                        <div style={{ 
                          fontSize: 'var(--font-size-xs)', 
                          color: 'var(--color-text-secondary)',
                          marginTop: '2px'
                        }}>
                          {theme.description}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    {/* Feature indicators */}
                    <div style={{ display: 'flex', marginRight: 'var(--spacing-sm)' }}>
                      {theme.features.hasAnimations && (
                        <Zap style={{ 
                          width: '0.875rem', 
                          height: '0.875rem', 
                          color: 'var(--color-accent)',
                          marginRight: '2px'
                        }} />
                      )}
                      {theme.features.hasGlassmorphism && (
                        <Eye style={{ 
                          width: '0.875rem', 
                          height: '0.875rem', 
                          color: 'var(--color-info)',
                          marginRight: '2px'
                        }} />
                      )}
                      {theme.features.supportsHighContrast && (
                        <Accessibility style={{ 
                          width: '0.875rem', 
                          height: '0.875rem', 
                          color: 'var(--color-success)',
                          marginRight: '2px'
                        }} />
                      )}
                    </div>
                    
                    {isSelected && (
                      <Check style={{ 
                        width: '1rem', 
                        height: '1rem', 
                        color: 'var(--color-success)' 
                      }} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {!compact && (
            <div style={accessibilityOptionsStyle}>
              <h4 style={{ 
                margin: '0 0 var(--spacing-sm) 0', 
                fontSize: 'var(--font-size-sm)', 
                fontWeight: 600,
                color: 'var(--color-text-primary)'
              }}>
                Accessibility Options
              </h4>
              
              <label style={checkboxStyle}>
                <input
                  type="checkbox"
                  checked={preferences.reduceMotion}
                  onChange={() => toggleAccessibilityOption('reduceMotion')}
                  style={{ marginRight: 'var(--spacing-sm)' }}
                />
                Reduce motion
              </label>
              
              <label style={checkboxStyle}>
                <input
                  type="checkbox"
                  checked={preferences.highContrast}
                  onChange={() => toggleAccessibilityOption('highContrast')}
                  style={{ marginRight: 'var(--spacing-sm)' }}
                />
                High contrast
              </label>
              
              <label style={checkboxStyle}>
                <input
                  type="checkbox"
                  checked={preferences.largeText}
                  onChange={() => toggleAccessibilityOption('largeText')}
                  style={{ marginRight: 'var(--spacing-sm)' }}
                />
                Large text
              </label>
              
              <label style={checkboxStyle}>
                <input
                  type="checkbox"
                  checked={preferences.autoSwitchByTime}
                  onChange={() => toggleAccessibilityOption('autoSwitchByTime')}
                  style={{ marginRight: 'var(--spacing-sm)' }}
                />
                Auto switch by time
              </label>
            </div>
          )}
        </div>,
        document.body
      )}
    </div>
  );
} 