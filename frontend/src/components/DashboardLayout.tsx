import { Activity, TrendingUp, FileText, Clock, Zap, AlertCircle, CheckCircle } from 'lucide-react'

interface HeatmapCell {
  day: string
  hour: number
  value: number
  maxValue: number
}

interface TopFile {
  name: string
  changes: number
  percentage: number
  color: string
}

interface MetricData {
  label: string
  value: number
  trend?: number
  unit?: string
}

interface TimePattern {
  hour: number
  count: number
  maxCount: number
}

interface LanguageStat {
  name: string
  percentage: number
  color: string
}

const generateActivityHeatmap = (): HeatmapCell[] => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const hours = Array.from({ length: 24 }, (_, i) => i)
  const cells: HeatmapCell[] = []

  for (const dayIdx of days.keys()) {
    for (const hour of hours) {
      const value = Math.floor(Math.random() * 15)
      cells.push({
        day: days[dayIdx],
        hour,
        value,
        maxValue: 15
      })
    }
  }

  return cells
}

const generateSparkline = (count: number = 12): number[] => {
  return Array.from({ length: count }, () => Math.floor(Math.random() * 100) + 20)
}

export function DashboardLayout() {
  // Mock data
  const topFiles: TopFile[] = [
    { name: 'App.tsx', changes: 342, percentage: 28, color: 'rgb(59, 130, 246)' },
    { name: 'Dashboard.tsx', changes: 287, percentage: 24, color: 'rgb(139, 92, 246)' },
    { name: 'index.css', changes: 198, percentage: 16, color: 'rgb(236, 72, 153)' },
    { name: 'utils.ts', changes: 156, percentage: 13, color: 'rgb(245, 158, 11)' },
    { name: 'types.ts', changes: 95, percentage: 8, color: 'rgb(16, 185, 129)' },
    { name: 'Other', changes: 72, percentage: 6, color: 'rgb(107, 114, 128)' },
  ]

  const commitFrequency: MetricData[] = [
    { label: 'Today', value: 47, trend: 12 },
    { label: 'This Week', value: 284, trend: 8 },
    { label: 'This Month', value: 1284, trend: -3 },
  ]

  const complexityMetrics: MetricData[] = [
    { label: 'High', value: 12, unit: 'files' },
    { label: 'Medium', value: 34, unit: 'files' },
    { label: 'Low', value: 89, unit: 'files' },
  ]

  const languages: LanguageStat[] = [
    { name: 'TypeScript', percentage: 45, color: 'rgb(59, 130, 246)' },
    { name: 'CSS', percentage: 25, color: 'rgb(236, 72, 153)' },
    { name: 'JavaScript', percentage: 20, color: 'rgb(245, 158, 11)' },
    { name: 'Markdown', percentage: 10, color: 'rgb(34, 197, 94)' },
  ]

  const timeOfDayPatterns: TimePattern[] = [
    { hour: 0, count: 2, maxCount: 50 },
    { hour: 1, count: 1, maxCount: 50 },
    { hour: 2, count: 0, maxCount: 50 },
    { hour: 3, count: 0, maxCount: 50 },
    { hour: 4, count: 1, maxCount: 50 },
    { hour: 5, count: 3, maxCount: 50 },
    { hour: 6, count: 8, maxCount: 50 },
    { hour: 7, count: 15, maxCount: 50 },
    { hour: 8, count: 32, maxCount: 50 },
    { hour: 9, count: 48, maxCount: 50 },
    { hour: 10, count: 45, maxCount: 50 },
    { hour: 11, count: 42, maxCount: 50 },
    { hour: 12, count: 38, maxCount: 50 },
    { hour: 13, count: 35, maxCount: 50 },
    { hour: 14, count: 40, maxCount: 50 },
    { hour: 15, count: 44, maxCount: 50 },
    { hour: 16, count: 40, maxCount: 50 },
    { hour: 17, count: 35, maxCount: 50 },
    { hour: 18, count: 22, maxCount: 50 },
    { hour: 19, count: 18, maxCount: 50 },
    { hour: 20, count: 12, maxCount: 50 },
    { hour: 21, count: 8, maxCount: 50 },
    { hour: 22, count: 5, maxCount: 50 },
    { hour: 23, count: 3, maxCount: 50 },
  ]

  const weeklyComparison = [
    { week: 'W1', thisWeek: 156, lastWeek: 128 },
    { week: 'W2', thisWeek: 189, lastWeek: 145 },
    { week: 'W3', thisWeek: 167, lastWeek: 172 },
    { week: 'W4', thisWeek: 203, lastWeek: 195 },
  ]

  const activityHeatmap = generateActivityHeatmap()
  const sparklineData = generateSparkline()

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Header */}
      <div className="relative overflow-hidden rounded-xl mb-6 p-6 text-white shadow-lg" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
      }}>
        <div className="absolute -top-8 -right-8 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
        <div className="absolute -bottom-8 -left-8 w-24 h-24 bg-white/5 rounded-full blur-2xl"></div>
        <div className="relative flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-1">Insights Dashboard</h1>
            <p className="text-sm opacity-90">Information-dense metrics and analytics</p>
          </div>
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-white/20 text-xs font-semibold">
            <div className="w-2 h-2 rounded-full bg-green-300 animate-pulse"></div>
            Live
          </div>
        </div>
      </div>

      {/* Top KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Total Changes', value: '1,284', icon: Activity, color: 'var(--color-primary)' },
          { label: 'Files Modified', value: '47', icon: FileText, color: 'var(--color-accent)' },
          { label: 'Avg Commit Size', value: '324', icon: TrendingUp, color: 'var(--color-success)' },
          { label: 'Peak Hour', value: '9 AM', icon: Clock, color: 'var(--color-warning)' },
        ].map((item, idx) => (
          <div
            key={idx}
            className="rounded-lg p-4 shadow-sm border"
            style={{
              background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
              borderColor: 'var(--color-border)'
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                {item.label}
              </p>
              <item.icon className="w-3.5 h-3.5" style={{ color: item.color }} />
            </div>
            <p className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
              {item.value}
            </p>
          </div>
        ))}
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Activity Heatmap - Takes up 2 cols */}
        <div className="lg:col-span-2 rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Activity Heatmap (24h × 7d)
          </h3>
          <div className="overflow-x-auto">
            <div className="space-y-1 pb-2">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
                <div key={day} className="flex items-center gap-1">
                  <span className="text-xs font-medium w-8" style={{ color: 'var(--color-text-secondary)' }}>
                    {day}
                  </span>
                  <div className="flex gap-0.5 flex-1">
                    {activityHeatmap
                      .filter(cell => cell.day === day)
                      .sort((a, b) => a.hour - b.hour)
                      .map((cell, idx) => {
                        const intensity = cell.value / cell.maxValue
                        return (
                          <div
                            key={idx}
                            className="w-3 h-3 rounded-sm"
                            style={{
                              backgroundColor: `rgba(59, 130, 246, ${intensity * 0.8 + 0.1})`,
                              border: '1px solid var(--color-border)'
                            }}
                            title={`${cell.hour}:00 - ${cell.value} commits`}
                          />
                        )
                      })}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-2 flex items-center justify-end gap-3 text-xs">
            <span style={{ color: 'var(--color-text-secondary)' }}>Less</span>
            {[0.2, 0.4, 0.6, 0.8, 1].map((val, i) => (
              <div
                key={i}
                className="w-3 h-3 rounded-sm"
                style={{
                  backgroundColor: `rgba(59, 130, 246, ${val * 0.8 + 0.1})`
                }}
              />
            ))}
            <span style={{ color: 'var(--color-text-secondary)' }}>More</span>
          </div>
        </div>

        {/* Top Files Chart */}
        <div className="rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Top Files
          </h3>
          <div className="space-y-2">
            {topFiles.map((file, idx) => (
              <div key={idx}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs truncate" style={{ color: 'var(--color-text-primary)' }}>
                    {file.name}
                  </span>
                  <span className="text-xs font-semibold" style={{ color: file.color }}>
                    {file.changes}
                  </span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${file.percentage * 4}%`, backgroundColor: file.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {/* Commit Frequency */}
        <div className="rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Commit Frequency
          </h3>
          <div className="space-y-2">
            {commitFrequency.map((metric, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  {metric.label}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>
                    {metric.value}
                  </span>
                  {metric.trend !== undefined && (
                    <span className={`text-xs font-semibold ${metric.trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {metric.trend >= 0 ? '+' : ''}{metric.trend}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Code Complexity Trends */}
        <div className="rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Code Complexity
          </h3>
          <div className="space-y-2">
            {complexityMetrics.map((metric, idx) => {
              const icons = [AlertCircle, Clock, CheckCircle]
              const Icon = icons[idx]
              return (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className="w-3.5 h-3.5" style={{ color: idx === 0 ? '#ef4444' : idx === 1 ? '#f59e0b' : '#10b981' }} />
                    <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                      {metric.label}
                    </span>
                  </div>
                  <span className="text-sm font-bold" style={{ color: 'var(--color-text-primary)' }}>
                    {metric.value} {metric.unit}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Language Distribution (Pie) */}
        <div className="rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Language Distribution
          </h3>
          <svg viewBox="0 0 100 100" className="w-20 h-20 mx-auto mb-3">
            {languages.reduce((acc, lang, idx) => {
              const startAngle = languages.slice(0, idx).reduce((sum, l) => sum + l.percentage, 0) * 3.6
              const endAngle = startAngle + lang.percentage * 3.6
              const startRad = (startAngle - 90) * (Math.PI / 180)
              const endRad = (endAngle - 90) * (Math.PI / 180)
              const x1 = 50 + 40 * Math.cos(startRad)
              const y1 = 50 + 40 * Math.sin(startRad)
              const x2 = 50 + 40 * Math.cos(endRad)
              const y2 = 50 + 40 * Math.sin(endRad)
              const largeArc = lang.percentage > 50 ? 1 : 0
              const path = `M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`

              return [
                ...acc,
                <path
                  key={`path-${idx}`}
                  d={path}
                  fill={lang.color}
                  stroke="var(--color-background)"
                  strokeWidth="1"
                />
              ]
            }, [] as JSX.Element[])}
          </svg>
          <div className="space-y-1">
            {languages.map((lang, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: lang.color }} />
                  <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {lang.name}
                  </span>
                </div>
                <span className="text-xs font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                  {lang.percentage}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Third Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Time of Day Patterns */}
        <div className="rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Time of Day Patterns
          </h3>
          <div className="flex items-end justify-between h-16 gap-0.5">
            {timeOfDayPatterns.map((pattern, idx) => (
              <div
                key={idx}
                className="flex-1 rounded-t-sm transition-all"
                style={{
                  height: `${(pattern.count / pattern.maxCount) * 100}%`,
                  background: 'linear-gradient(180deg, var(--color-primary), var(--color-accent))',
                  opacity: pattern.count > 0 ? 1 : 0.2
                }}
                title={`${String(pattern.hour).padStart(2, '0')}:00 - ${pattern.count} commits`}
              />
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <span>00:00</span>
            <span>12:00</span>
            <span>23:00</span>
          </div>
        </div>

        {/* Weekly Comparison */}
        <div className="rounded-lg p-4 shadow-sm border" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Weekly Comparison
          </h3>
          <div className="space-y-2">
            {weeklyComparison.map((week, idx) => {
              const maxVal = Math.max(week.thisWeek, week.lastWeek)
              return (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
                      {week.week}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs" style={{ color: 'var(--color-primary)' }}>
                        {week.thisWeek}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                        vs {week.lastWeek}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        flex: week.thisWeek / maxVal,
                        backgroundColor: 'var(--color-primary)'
                      }}
                    />
                    <div
                      className="h-2 rounded-full"
                      style={{
                        flex: week.lastWeek / maxVal,
                        backgroundColor: 'var(--color-warning)',
                        opacity: 0.6
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Sparklines Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {[
          { title: 'Daily Trend', color: 'rgb(59, 130, 246)' },
          { title: 'Weekly Trend', color: 'rgb(139, 92, 246)' },
        ].map((item, idx) => (
          <div key={idx} className="rounded-lg p-4 shadow-sm border" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)'
          }}>
            <h3 className="text-sm font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
              {item.title}
            </h3>
            <svg viewBox="0 0 300 40" className="w-full h-12">
              <polyline
                points={sparklineData.map((val, i) => `${i * (300 / sparklineData.length)},${40 - (val / 100) * 35}`).join(' ')}
                fill="none"
                stroke={item.color}
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
              />
              <polyline
                points={sparklineData.map((val, i) => `${i * (300 / sparklineData.length)},${40 - (val / 100) * 35}`).join(' ')}
                fill={`${item.color}20`}
                stroke="none"
                fillOpacity="0.2"
              />
            </svg>
          </div>
        ))}
      </div>

      {/* Summary Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: 'Commits', value: '284', unit: 'this week' },
          { label: 'Avg/Day', value: '40.6', unit: 'commits' },
          { label: 'Peak Day', value: 'Thursday', unit: '+23%' },
          { label: 'Consistency', value: '94%', unit: 'score' },
          { label: 'Active Hours', value: '8.5', unit: 'hrs/day' },
          { label: 'Files Touched', value: '47', unit: 'total' },
        ].map((stat, idx) => (
          <div key={idx} className="rounded-lg p-3 shadow-sm border text-center" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)'
          }}>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              {stat.label}
            </p>
            <p className="text-base font-bold mt-1" style={{ color: 'var(--color-text-primary)' }}>
              {stat.value}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
              {stat.unit}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
