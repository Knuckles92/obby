import { Activity, FileText, GitCommit, Code, TrendingUp, Zap, BarChart3 } from 'lucide-react'

export default function DashboardLayout() {
  // Mock data generators
  const generateHeatmapData = () => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    const hours = Array.from({ length: 24 }, (_, i) => i)
    return days.map(day => ({
      day,
      hours: hours.map(hour => ({
        hour,
        value: Math.floor(Math.random() * 10)
      }))
    }))
  }

  const topFiles = [
    { name: 'components/Dashboard.tsx', changes: 45 },
    { name: 'utils/api.ts', changes: 32 },
    { name: 'pages/Insights.tsx', changes: 28 },
    { name: 'styles/theme.css', changes: 24 },
    { name: 'hooks/useData.ts', changes: 18 },
    { name: 'types/index.ts', changes: 12 }
  ]

  const languages = [
    { name: 'TypeScript', percentage: 45, color: '#3178c6' },
    { name: 'CSS', percentage: 25, color: '#264de4' },
    { name: 'JavaScript', percentage: 20, color: '#f7df1e' },
    { name: 'Markdown', percentage: 10, color: '#083fa1' }
  ]

  const hourlyActivity = Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    value: Math.floor(Math.random() * 30) + 5
  }))

  const weeklyComparison = [
    { week: 'Week 1', value: 45 },
    { week: 'Week 2', value: 62 },
    { week: 'Week 3', value: 38 },
    { week: 'Week 4', value: 71 }
  ]

  const maxHourly = Math.max(...hourlyActivity.map(h => h.value))
  const maxWeekly = Math.max(...weeklyComparison.map(w => w.value))

  return (
    <div className="min-h-screen p-6">
      {/* Compact Header */}
      <div className="relative overflow-hidden rounded-xl mb-6 p-6 text-white shadow-lg" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
      }}>
        <div className="absolute -top-6 -right-6 w-24 h-24 bg-white/10 rounded-full blur-2xl"></div>
        <div className="relative flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Discovery Dashboard</h1>
            <p className="text-sm text-blue-100 mt-1">AI findings at a glance</p>
          </div>
          <div className="px-3 py-1 rounded-lg bg-white/20 backdrop-blur-sm text-sm font-medium">
            Live
          </div>
        </div>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Changes', value: '1,284', icon: <Activity className="h-4 w-4" />, color: '#3b82f6' },
          { label: 'Files Modified', value: '47', icon: <FileText className="h-4 w-4" />, color: '#8b5cf6' },
          { label: 'Avg Change Size', value: '324', icon: <GitCommit className="h-4 w-4" />, color: '#ec4899' },
          { label: 'Peak Activity', value: '3 PM', icon: <Zap className="h-4 w-4" />, color: '#f59e0b' }
        ].map((kpi, i) => (
          <div key={i} className="rounded-lg p-4 shadow border" style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>{kpi.label}</span>
              <div style={{ color: kpi.color }}>{kpi.icon}</div>
            </div>
            <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Activity Heatmap */}
        <div className="lg:col-span-2 rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4" style={{ color: 'var(--color-primary)' }} />
            <h3 className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>24/7 Activity Heatmap</h3>
          </div>
          <div className="overflow-x-auto">
            <div className="inline-grid gap-1" style={{ gridTemplateColumns: 'auto repeat(24, 1fr)' }}>
              <div></div>
              {Array.from({ length: 24 }, (_, i) => (
                <div key={i} className="text-xs text-center" style={{ color: 'var(--color-text-secondary)' }}>
                  {i}
                </div>
              ))}
              {generateHeatmapData().map((day, dayIdx) => (
                <>
                  <div key={`day-${dayIdx}`} className="text-xs pr-2" style={{ color: 'var(--color-text-secondary)' }}>
                    {day.day}
                  </div>
                  {day.hours.map((hour, hourIdx) => (
                    <div
                      key={`${dayIdx}-${hourIdx}`}
                      className="w-4 h-4 rounded-sm"
                      style={{
                        backgroundColor: hour.value === 0 ? 'var(--color-divider)' :
                          hour.value < 3 ? '#dbeafe' :
                          hour.value < 6 ? '#93c5fd' :
                          hour.value < 8 ? '#3b82f6' : '#1e40af'
                      }}
                    ></div>
                  ))}
                </>
              ))}
            </div>
          </div>
        </div>

        {/* Language Distribution Pie */}
        <div className="rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="flex items-center gap-2 mb-4">
            <Code className="h-4 w-4" style={{ color: 'var(--color-primary)' }} />
            <h3 className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>Languages</h3>
          </div>
          <div className="flex justify-center mb-4">
            <svg width="120" height="120" viewBox="0 0 100 100">
              {(() => {
                let currentAngle = 0
                return languages.map((lang, i) => {
                  const angle = (lang.percentage / 100) * 360
                  const startAngle = currentAngle
                  const endAngle = currentAngle + angle
                  currentAngle = endAngle

                  const startRad = (startAngle - 90) * Math.PI / 180
                  const endRad = (endAngle - 90) * Math.PI / 180
                  const x1 = 50 + 40 * Math.cos(startRad)
                  const y1 = 50 + 40 * Math.sin(startRad)
                  const x2 = 50 + 40 * Math.cos(endRad)
                  const y2 = 50 + 40 * Math.sin(endRad)
                  const largeArc = angle > 180 ? 1 : 0

                  return (
                    <path
                      key={i}
                      d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`}
                      fill={lang.color}
                      opacity="0.9"
                    />
                  )
                })
              })()}
            </svg>
          </div>
          <div className="space-y-2">
            {languages.map((lang, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: lang.color }}></div>
                  <span style={{ color: 'var(--color-text-primary)' }}>{lang.name}</span>
                </div>
                <span style={{ color: 'var(--color-text-secondary)' }}>{lang.percentage}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Secondary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {/* Top Files */}
        <div className="rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>Top Files</h3>
          <div className="space-y-3">
            {topFiles.map((file, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span style={{ color: 'var(--color-text-primary)' }} className="truncate">{file.name}</span>
                  <span style={{ color: 'var(--color-text-secondary)' }}>{file.changes}</span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-divider)' }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(file.changes / 45) * 100}%`,
                      backgroundColor: 'var(--color-primary)'
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Time of Day Patterns */}
        <div className="rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>Hourly Pattern</h3>
          <div className="flex items-end justify-between h-32 gap-0.5">
            {hourlyActivity.map((data, i) => (
              <div
                key={i}
                className="flex-1 rounded-t"
                style={{
                  height: `${(data.value / maxHourly) * 100}%`,
                  backgroundColor: i === 9 ? 'var(--color-warning)' : 'var(--color-primary)',
                  opacity: 0.8
                }}
                title={`${i}:00 - ${data.value}`}
              ></div>
            ))}
          </div>
          <p className="text-xs mt-2 text-center" style={{ color: 'var(--color-text-secondary)' }}>
            Peak at 9 AM
          </p>
        </div>

        {/* Weekly Comparison */}
        <div className="rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>Weekly Trend</h3>
          <div className="space-y-3">
            {weeklyComparison.map((week, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span style={{ color: 'var(--color-text-secondary)' }}>{week.week}</span>
                  <span style={{ color: 'var(--color-text-primary)' }} className="font-semibold">{week.value}</span>
                </div>
                <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-divider)' }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(week.value / maxWeekly) * 100}%`,
                      background: 'linear-gradient(90deg, var(--color-primary), var(--color-accent))'
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Stats Footer */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: 'Total Changes', value: '1.2k' },
          { label: 'Avg/Day', value: '48' },
          { label: 'Consistency', value: '94%' },
          { label: 'Activity Score', value: '8.7' },
          { label: 'Active Time', value: '6.2h' },
          { label: 'Peak Days', value: '4' }
        ].map((stat, i) => (
          <div key={i} className="rounded-lg p-4 text-center shadow border" style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}>
            <p className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{stat.value}</p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>{stat.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
