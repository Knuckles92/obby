interface StatCardProps {
  title: string
  value: string | number
  icon: any
  color?: string
  percentage?: number
}

export default function StatCard({ title, value, icon: Icon, color = 'blue', percentage }: StatCardProps) {
  return (
    <div style={{
      backgroundColor: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--border-radius-lg)',
      padding: 'var(--spacing-lg)',
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--spacing-md)'
    }}>
      <div style={{
        backgroundColor: `var(--color-${color})`,
        borderRadius: 'var(--border-radius-md)',
        padding: 'var(--spacing-sm)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Icon style={{ width: '1.5rem', height: '1.5rem', color: 'white' }} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ 
          fontSize: 'var(--font-size-sm)', 
          color: 'var(--color-text-secondary)',
          marginBottom: 'var(--spacing-xs)'
        }}>
          {title}
        </div>
        <div style={{ 
          fontSize: 'var(--font-size-xl)', 
          fontWeight: 'var(--font-weight-bold)',
          color: 'var(--color-text-primary)'
        }}>
          {value}
        </div>
        {percentage !== undefined && (
          <div style={{
            width: '100%',
            height: '4px',
            backgroundColor: 'var(--color-border)',
            borderRadius: '2px',
            marginTop: 'var(--spacing-xs)',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${percentage}%`,
              height: '100%',
              backgroundColor: `var(--color-${color})`,
              transition: 'width 0.3s ease'
            }} />
          </div>
        )}
      </div>
    </div>
  )
}


