import { Activity, FileText, GitCommit, Code, TrendingUp, Zap, BarChart3, Clock, Target, ArrowRight } from 'lucide-react'

export default function SplitLayout() {
  const leftData = {
    title: 'Activity Overview',
    metrics: [
      { label: 'Total Changes', value: '1,284', change: '+12%', icon: <Activity className="h-5 w-5" /> },
      { label: 'Files Modified', value: '47', change: '+5', icon: <FileText className="h-5 w-5" /> },
      { label: 'Commits', value: '23', change: '+3', icon: <GitCommit className="h-5 w-5" /> },
      { label: 'Lines Changed', value: '8.2k', change: '+1.1k', icon: <Code className="h-5 w-5" /> }
    ],
    chart: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      values: [45, 62, 38, 71, 55, 48, 67]
    }
  }

  const rightData = {
    title: 'Pattern Insights',
    metrics: [
      { label: 'Activity Score', value: '87%', change: '+4%', icon: <Target className="h-5 w-5" /> },
      { label: 'Peak Hour', value: '3 PM', change: '↑', icon: <Clock className="h-5 w-5" /> },
      { label: 'High Intensity', value: '72%', change: '+8%', icon: <Zap className="h-5 w-5" /> },
      { label: 'Active Duration', value: '6h', change: '+1.5h', icon: <TrendingUp className="h-5 w-5" /> }
    ],
    chart: {
      labels: ['6 AM', '9 AM', '12 PM', '3 PM', '6 PM', '9 PM'],
      values: [5, 32, 28, 45, 38, 15]
    }
  }

  const maxLeft = Math.max(...leftData.chart.values)
  const maxRight = Math.max(...rightData.chart.values)

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
          Split View
        </h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Side-by-side comparison of activity patterns
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Activity */}
        <div className="rounded-xl border p-6" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="mb-6">
            <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
              {leftData.title}
            </h2>
            <div className="w-12 h-1 rounded-full" style={{ backgroundColor: 'var(--color-primary)' }} />
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {leftData.metrics.map((metric, i) => (
              <div
                key={i}
                className="rounded-lg p-4 border"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-border)'
                }}
              >
                <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--color-primary)' }}>
                  {metric.icon}
                  <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                    {metric.label}
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                    {metric.value}
                  </span>
                  <span className="text-sm font-medium" style={{ color: 'var(--color-accent)' }}>
                    {metric.change}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Weekly Chart */}
          <div>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
              Weekly Activity
            </h3>
            <div className="flex items-end gap-2 h-32">
              {leftData.chart.values.map((value, i) => (
                <div key={i} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full rounded-t transition-all hover:opacity-80"
                    style={{
                      height: `${(value / maxLeft) * 100}%`,
                      backgroundColor: 'var(--color-primary)',
                      minHeight: '4px'
                    }}
                    title={`${leftData.chart.labels[i]}: ${value}`}
                  />
                  <span className="text-xs mt-2" style={{ color: 'var(--color-text-secondary)' }}>
                    {leftData.chart.labels[i]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column - Performance */}
        <div className="rounded-xl border p-6" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="mb-6">
            <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
              {rightData.title}
            </h2>
            <div className="w-12 h-1 rounded-full" style={{ backgroundColor: 'var(--color-accent)' }} />
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {rightData.metrics.map((metric, i) => (
              <div
                key={i}
                className="rounded-lg p-4 border"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-border)'
                }}
              >
                <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--color-accent)' }}>
                  {metric.icon}
                  <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                    {metric.label}
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                    {metric.value}
                  </span>
                  <span className="text-sm font-medium" style={{ color: 'var(--color-accent)' }}>
                    {metric.change}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Hourly Chart */}
          <div>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
              Daily Rhythm
            </h3>
            <div className="flex items-end gap-2 h-32">
              {rightData.chart.values.map((value, i) => (
                <div key={i} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full rounded-t transition-all hover:opacity-80"
                    style={{
                      height: `${(value / maxRight) * 100}%`,
                      backgroundColor: 'var(--color-accent)',
                      minHeight: '4px'
                    }}
                    title={`${rightData.chart.labels[i]}: ${value}`}
                  />
                  <span className="text-xs mt-2" style={{ color: 'var(--color-text-secondary)' }}>
                    {rightData.chart.labels[i]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Comparison Bar */}
      <div className="mt-6 rounded-xl border p-6" style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
              Quick Comparison
            </h3>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Activity patterns and insights side by side
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>1,284</div>
              <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Changes</div>
            </div>
            <ArrowRight className="h-5 w-5" style={{ color: 'var(--color-text-secondary)' }} />
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--color-accent)' }}>87%</div>
              <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Score</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


