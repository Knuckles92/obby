interface ActionButtonProps {
  onClick: () => void
  icon: any
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'danger'
  disabled?: boolean
  busy?: boolean
}

export default function ActionButton({ onClick, icon: Icon, children, variant = 'primary', disabled = false, busy = false }: ActionButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || busy}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-sm)',
        padding: 'var(--spacing-md) var(--spacing-lg)',
        backgroundColor: variant === 'danger' ? 'var(--color-error)' :
                        variant === 'secondary' ? 'var(--color-surface)' : 'var(--color-primary)',
        color: variant === 'secondary' ? 'var(--color-text-primary)' : 'white',
        border: variant === 'secondary' ? '1px solid var(--color-border)' : 'none',
        borderRadius: 'var(--border-radius-md)',
        cursor: disabled || busy ? 'not-allowed' : 'pointer',
        opacity: disabled || busy ? 0.6 : 1,
        transition: 'all 0.2s ease'
      }}
    >
      <Icon style={{ width: '1rem', height: '1rem' }} />
      {children}
    </button>
  )
}


