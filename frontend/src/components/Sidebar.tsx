import { Link, useLocation } from 'react-router-dom'
import { 
  Home, 
  GitBranch, 
  FileText, 
  Settings, 
  Menu,
  Activity,
  Shield
} from 'lucide-react'
import { useTheme, useThemeClasses, useThemeFeature } from '../contexts/ThemeContext'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Diff Viewer', href: '/diffs', icon: GitBranch },
  { name: 'Obby Summary', href: '/summary-notes', icon: FileText },
  { name: 'Administration', href: '/admin', icon: Shield },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const location = useLocation()
  const { currentTheme } = useTheme()
  const hasGlassmorphism = useThemeFeature('hasGlassmorphism')
  const sidebarClasses = useThemeClasses('sidebar')

  const sidebarStyle = {
    backgroundColor: hasGlassmorphism ? 'var(--color-overlay)' : 'var(--color-surface)',
    borderColor: 'var(--color-border)',
    backdropFilter: hasGlassmorphism ? 'var(--glass-blur)' : 'none',
    borderRight: `1px solid var(--color-border)`,
    width: isOpen ? '16rem' : '4rem',
    transition: `width var(--duration-normal) var(--easing-ease)`,
    position: 'fixed' as const,
    top: 0,
    left: 0,
    bottom: 0,
    zIndex: 50
  }

  const headerStyle = {
    borderBottom: `1px solid var(--color-border)`,
    padding: 'var(--spacing-md)',
    height: '4rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  }

  const toggleButtonStyle = {
    padding: 'var(--spacing-sm)',
    borderRadius: 'var(--border-radius-md)',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--color-text-secondary)',
    transition: `background-color var(--duration-fast) var(--easing-ease), color var(--duration-fast) var(--easing-ease)`
  }

  const navigationStyle = {
    marginTop: 'var(--spacing-xl)',
    padding: `0 var(--spacing-md)`
  }

  const getNavItemStyle = (isActive: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    padding: 'var(--spacing-sm) var(--spacing-md)',
    fontSize: 'var(--font-size-sm)',
    fontWeight: 500,
    borderRadius: 'var(--border-radius-md)',
    textDecoration: 'none',
    transition: `all var(--duration-fast) var(--easing-ease)`,
    backgroundColor: isActive ? 'var(--color-primary)' : 'transparent',
    color: isActive ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
    borderRight: isActive ? `2px solid var(--color-accent)` : 'none',
    marginBottom: 'var(--spacing-xs)'
  })

  const getIconStyle = (isActive: boolean) => ({
    color: isActive ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
    width: '1.25rem',
    height: '1.25rem'
  })

  return (
    <div className={sidebarClasses} style={sidebarStyle}>
      <div style={headerStyle}>
        {isOpen && (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Activity 
              style={{ 
                height: '2rem', 
                width: '2rem', 
                color: 'var(--color-primary)' 
              }} 
            />
            <span 
              style={{ 
                marginLeft: 'var(--spacing-sm)', 
                fontSize: 'var(--font-size-lg)', 
                fontWeight: 600, 
                color: 'var(--color-text-primary)',
                fontFamily: 'var(--font-family-display)'
              }}
            >
              Obby
            </span>
          </div>
        )}
        <button
          onClick={onToggle}
          style={toggleButtonStyle}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-hover)'
            e.currentTarget.style.color = 'var(--color-text-primary)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent'
            e.currentTarget.style.color = 'var(--color-text-secondary)'
          }}
        >
          <Menu style={{ height: '1.25rem', width: '1.25rem' }} />
        </button>
      </div>

      <nav style={navigationStyle}>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  to={item.href}
                  style={getNavItemStyle(isActive)}
                  title={!isOpen ? item.name : undefined}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'var(--color-hover)'
                      e.currentTarget.style.color = 'var(--color-text-primary)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent'
                      e.currentTarget.style.color = 'var(--color-text-secondary)'
                    }
                  }}
                >
                  <item.icon style={getIconStyle(isActive)} />
                  {isOpen && (
                    <span style={{ marginLeft: 'var(--spacing-md)' }}>
                      {item.name}
                    </span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      
      {/* Theme-specific decorative elements */}
      {currentTheme.category === 'creative' && hasGlassmorphism && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `linear-gradient(135deg, ${currentTheme.colors.primary}15, ${currentTheme.colors.accent}05)`,
            pointerEvents: 'none',
            zIndex: -1
          }}
        />
      )}
    </div>
  )
}