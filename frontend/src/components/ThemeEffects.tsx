import React, { useEffect, useState } from 'react';
import { useTheme, useThemeFeature } from '../contexts/ThemeContext';

interface ThemeEffectsProps {
  className?: string;
}

// Snowflake component for Winter theme
const Snowflake: React.FC<{ style: React.CSSProperties }> = ({ style }) => (
  <div style={style}>❄</div>
);

// Data stream component for Cyberpunk theme
const DataStream: React.FC<{ style: React.CSSProperties }> = ({ style }) => (
  <div style={style}>
    {Math.random().toString(36).substring(2, 8).toUpperCase()}
  </div>
);

// Particle component for creative themes
const Particle: React.FC<{ style: React.CSSProperties }> = ({ style }) => (
  <div style={style} />
);

export default function ThemeEffects({ className = '' }: ThemeEffectsProps) {
  const { currentTheme } = useTheme();
  const hasAnimations = useThemeFeature('hasAnimations');
  const hasParticles = useThemeFeature('hasParticles');
  const [particles, setParticles] = useState<Array<{ id: number; style: React.CSSProperties }>>([]);

  // Generate particles based on theme
  useEffect(() => {
    if (!hasParticles || !hasAnimations) {
      setParticles([]);
      return;
    }

    const particleCount = currentTheme.effects.specialEffects.particleCount || 0;
    const newParticles = [];

    for (let i = 0; i < particleCount; i++) {
      const particle = {
        id: i,
        style: generateParticleStyle(currentTheme.id, i)
      };
      newParticles.push(particle);
    }

    setParticles(newParticles);
  }, [currentTheme, hasParticles, hasAnimations]);

  const generateParticleStyle = (themeId: string, index: number): React.CSSProperties => {
    const baseStyle: React.CSSProperties = {
      position: 'fixed',
      pointerEvents: 'none',
      zIndex: -1,
      left: `${Math.random() * 100}%`,
      animationDelay: `${Math.random() * 5}s`,
      animationIterationCount: 'infinite',
      animationTimingFunction: 'linear'
    };

    switch (themeId) {
      case 'winter':
        return {
          ...baseStyle,
          top: '-10px',
          fontSize: `${12 + Math.random() * 12}px`,
          color: 'var(--color-border)',
          animationName: 'snowfall',
          animationDuration: `${8 + Math.random() * 6}s`
        };

      case 'cyberpunk':
        return {
          ...baseStyle,
          top: `${Math.random() * 100}%`,
          fontSize: '10px',
          color: 'var(--color-primary)',
          opacity: 0.6,
          fontFamily: 'var(--font-family-mono)',
          animationName: 'data-stream',
          animationDuration: `${3 + Math.random() * 4}s`
        };

      case 'forest':
        return {
          ...baseStyle,
          top: `${Math.random() * 100}%`,
          width: `${2 + Math.random() * 4}px`,
          height: `${2 + Math.random() * 4}px`,
          backgroundColor: 'var(--color-primary)',
          borderRadius: '50%',
          opacity: 0.4,
          animationName: 'organic-float',
          animationDuration: `${10 + Math.random() * 10}s`
        };

      case 'ocean':
        return {
          ...baseStyle,
          top: `${Math.random() * 100}%`,
          width: `${1 + Math.random() * 3}px`,
          height: `${1 + Math.random() * 3}px`,
          backgroundColor: 'var(--color-accent)',
          borderRadius: '50%',
          opacity: 0.5,
          animationName: 'wave-particle',
          animationDuration: `${6 + Math.random() * 8}s`
        };

      case 'neon':
        return {
          ...baseStyle,
          top: `${Math.random() * 100}%`,
          width: '2px',
          height: `${10 + Math.random() * 20}px`,
          backgroundColor: 'var(--color-accent)',
          boxShadow: `0 0 10px var(--color-accent)`,
          animationName: 'neon-pulse',
          animationDuration: `${1 + Math.random() * 2}s`
        };

      default:
        return baseStyle;
    }
  };

  const containerStyle: React.CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: -1,
    overflow: 'hidden'
  };

  // Add theme-specific background effects
  const getBackgroundEffect = () => {
    if (!hasAnimations) return null;

    switch (currentTheme.id) {
      case 'cyberpunk':
        return (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              backgroundImage: `
                repeating-linear-gradient(
                  90deg,
                  transparent,
                  transparent 98px,
                  var(--color-primary) 100px
                ),
                repeating-linear-gradient(
                  0deg,
                  transparent,
                  transparent 98px,
                  var(--color-secondary) 100px
                )
              `,
              opacity: 0.03,
              animation: `matrix-bg ${currentTheme.effects.specialEffects.dataStreamCount || 10}s linear infinite`
            }}
          />
        );

      case 'forest':
        return (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '200%',
              height: '200%',
              background: `
                radial-gradient(circle at 20% 50%, ${currentTheme.colors.primary}10 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, ${currentTheme.colors.accent}08 0%, transparent 50%),
                radial-gradient(circle at 40% 80%, ${currentTheme.colors.secondary}06 0%, transparent 50%)
              `,
              animation: `organic-bg ${(currentTheme.effects.specialEffects.waveSpeed || 1) * 30}s ease-in-out infinite`
            }}
          />
        );

      case 'ocean':
        return (
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: '100px',
              background: `
                linear-gradient(
                  to top,
                  ${currentTheme.colors.primary}15,
                  ${currentTheme.colors.accent}08,
                  transparent
                )
              `,
              animation: `wave-bg ${(currentTheme.effects.specialEffects.waveSpeed || 1) * 8}s ease-in-out infinite`
            }}
          />
        );

      case 'neon':
        return (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              background: `
                radial-gradient(circle at 25% 25%, ${currentTheme.colors.primary}20 0%, transparent 50%),
                radial-gradient(circle at 75% 75%, ${currentTheme.colors.accent}20 0%, transparent 50%),
                radial-gradient(circle at 75% 25%, ${currentTheme.colors.secondary}15 0%, transparent 50%)
              `,
              animation: `neon-bg ${(currentTheme.effects.specialEffects.pulseRate || 2)}s ease-in-out infinite alternate`
            }}
          />
        );

      default:
        return null;
    }
  };

  // Don't render anything if animations are disabled
  if (!hasAnimations && !hasParticles) {
    return null;
  }

  return (
    <div className={className} style={containerStyle}>
      {getBackgroundEffect()}
      
      {/* Render particles */}
      {particles.map((particle) => {
        switch (currentTheme.id) {
          case 'winter':
            return <Snowflake key={particle.id} style={particle.style} />;
          case 'cyberpunk':
            return <DataStream key={particle.id} style={particle.style} />;
          default:
            return <Particle key={particle.id} style={particle.style} />;
        }
      })}

      {/* Theme-specific CSS animations */}
      <style>{`
        @keyframes snowfall {
          0% {
            transform: translateY(-100px) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(360deg);
            opacity: 0;
          }
        }

        @keyframes data-stream {
          0% {
            transform: translateX(-100px);
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          90% {
            opacity: 1;
          }
          100% {
            transform: translateX(100vw);
            opacity: 0;
          }
        }

        @keyframes organic-float {
          0%, 100% {
            transform: translate(0, 0) scale(1);
          }
          25% {
            transform: translate(20px, -20px) scale(1.1);
          }
          50% {
            transform: translate(-15px, -40px) scale(0.9);
          }
          75% {
            transform: translate(-20px, -10px) scale(1.05);
          }
        }

        @keyframes wave-particle {
          0%, 100% {
            transform: translateY(0) scale(1);
          }
          50% {
            transform: translateY(-30px) scale(1.2);
          }
        }

        @keyframes neon-pulse {
          0%, 100% {
            opacity: 0.6;
            transform: scaleY(1);
          }
          50% {
            opacity: 1;
            transform: scaleY(1.5);
          }
        }

        @keyframes matrix-bg {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-100px);
          }
        }

        @keyframes organic-bg {
          0%, 100% {
            transform: rotate(0deg) scale(1);
          }
          50% {
            transform: rotate(180deg) scale(1.1);
          }
        }

        @keyframes wave-bg {
          0%, 100% {
            transform: translateX(0) scaleY(1);
          }
          50% {
            transform: translateX(-50px) scaleY(1.2);
          }
        }

        @keyframes neon-bg {
          0% {
            opacity: 0.3;
          }
          100% {
            opacity: 0.6;
          }
        }

        /* Reduced motion overrides */
        @media (prefers-reduced-motion: reduce) {
          .theme-effects * {
            animation: none !important;
          }
        }

        .reduce-motion .theme-effects * {
          animation: none !important;
        }
      `}</style>
    </div>
  );
} 