import { Activity, FileText, GitCommit, Code, TrendingUp, Zap, BarChart3, Clock, Target } from 'lucide-react'

export default function CompactLayout() {
  const metrics = [
    { label: 'Changes', value: '1,284', icon: <Activity className="h-3 w-3" />, trend: '+12%' },
    { label: 'Files', value: '47', icon: <FileText className="h-3 w-3" />, trend: '+5' },
    { label: 'Commits', value: '23', icon: <GitCommit className="h-3 w-3" />, trend: '+3' },
    { label: 'Lines', value: '8.2k', icon: <Code className="h-3 w-3" />, trend: '+1.1k' },
    { label: 'Peak', value: '3 PM', icon: <Clock className="h-3 w-3" />, trend: '↑' },
    { label: 'Score', value: '87', icon: <Target className="h-3 w-3" />, trend: '+4' }
  ]

  const recentActivity = [
    { time: '2h', file: 'components/Dashboard.tsx', action: 'Modified', lines: '+45' },
    { time: '3h', file: 'utils/api.ts', action: 'Modified', lines: '+32' },
    { time: '4h', file: 'pages/Insights.tsx', action: 'Created', lines: '+128' },
    { time: '5h', file: 'styles/theme.css', action: 'Modified', lines: '+24' },
    { time: '6h', file: 'hooks/useData.ts', action: 'Modified', lines: '+18' }
  ]

  const languages = [
    { name: 'TS', percent: 45, color: '#3178c6' },
    { name: 'CSS', percent: 25, color: '#264de4' },
    { name: 'JS', percent: 20, color: '#f7df1e' },
    { name: 'MD', percent: 10, color: '#083fa1' }
  ]

  return (
    <div className="min-h-screen p-4" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Ultra-compact header */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>Compact Findings</h1>
        <div className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text-secondary)' }}>
          Live
        </div>
      </div>

      {/* Dense metrics grid */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
        {metrics.map((metric, i) => (
          <div
            key={i}
            className="rounded-lg p-2 border text-center"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <div className="flex items-center justify-center gap-1 mb-1" style={{ color: 'var(--color-primary)' }}>
              {metric.icon}
              <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                {metric.label}
              </span>
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
              {metric.value}
            </div>
            <div className="text-xs" style={{ color: 'var(--color-accent)' }}>
              {metric.trend}
            </div>
          </div>
        ))}
      </div>

      {/* Two-column dense layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Recent Activity - Compact List */}
        <div className="rounded-lg p-3 border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="h-3 w-3" style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Recent</h3>
          </div>
          <div className="space-y-2">
            {recentActivity.map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-xs p-2 rounded border"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-border)'
                }}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-xs font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                    {item.time}
                  </span>
                  <span className="truncate font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    {item.file}
                  </span>
                </div>
                <div className="flex items-center gap-2 ml-2">
                  <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {item.action}
                  </span>
                  <span className="text-xs font-bold" style={{ color: 'var(--color-accent)' }}>
                    {item.lines}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Language Distribution - Compact */}
        <div className="rounded-lg p-3 border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="flex items-center gap-2 mb-3">
            <Code className="h-3 w-3" style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Languages</h3>
          </div>
          <div className="space-y-2">
            {languages.map((lang, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    {lang.name}
                  </span>
                  <span className="font-bold" style={{ color: 'var(--color-text-secondary)' }}>
                    {lang.percent}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${lang.percent}%`,
                      backgroundColor: lang.color
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Hourly activity - ultra compact */}
      <div className="mt-3 rounded-lg p-3 border" style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="h-3 w-3" style={{ color: 'var(--color-primary)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>24h Activity</h3>
        </div>
        <div className="flex items-end gap-1 h-20">
          {Array.from({ length: 24 }, (_, i) => {
            const height = Math.floor(Math.random() * 60) + 20
            return (
              <div
                key={i}
                className="flex-1 rounded-t transition-all hover:opacity-80"
                style={{
                  height: `${height}%`,
                  backgroundColor: i >= 9 && i <= 17 ? 'var(--color-primary)' : 'var(--color-accent)',
                  minHeight: '4px'
                }}
                title={`${i}:00 - ${height} changes`}
              />
            )
          })}
        </div>
        <div className="flex justify-between text-xs mt-2" style={{ color: 'var(--color-text-secondary)' }}>
          <span>00:00</span>
          <span>12:00</span>
          <span>24:00</span>
        </div>
      </div>
    </div>
  )
}

