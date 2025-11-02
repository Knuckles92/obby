import { Calendar, Zap, TrendingUp, GitBranch } from 'lucide-react'

export default function HeatmapLayout() {
  // Generate weekly 7x24 hour heatmap data
  const generateWeeklyHeatmap = () => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    return days.map(day => ({
      day,
      hours: Array.from({ length: 24 }, (_, hour) => ({
        hour,
        intensity: Math.floor(Math.random() * 5) // 0-4 intensity levels
      }))
    }))
  }

  // Generate contribution calendar (7 weeks)
  const generateContributions = () => {
    const weeks = []
    for (let week = 0; week < 7; week++) {
      const days = []
      for (let day = 0; day < 7; day++) {
        days.push({
          date: new Date(2025, 9, week * 7 + day + 1),
          count: Math.floor(Math.random() * 20)
        })
      }
      weeks.push(days)
    }
    return weeks
  }

  // File type bubbles with size proportional to changes
  const fileTypeBubbles = [
    { type: 'TypeScript', changes: 342, size: 80, x: 20, y: 30 },
    { type: 'CSS', changes: 187, size: 60, x: 55, y: 25 },
    { type: 'JavaScript', changes: 156, size: 55, x: 35, y: 65 },
    { type: 'Markdown', changes: 98, size: 45, x: 70, y: 60 },
    { type: 'JSON', changes: 45, size: 30, x: 50, y: 50 },
    { type: 'HTML', changes: 28, size: 25, x: 80, y: 35 }
  ]

  // Change intensity map by category
  const intensityMap = [
    { category: 'Bug Fixes', data: [3, 4, 2, 4, 3, 1, 2] },
    { category: 'Features', data: [2, 3, 4, 3, 2, 1, 1] },
    { category: 'Documentation', data: [1, 2, 2, 3, 4, 2, 1] },
    { category: 'Refactoring', data: [2, 1, 3, 2, 2, 0, 1] }
  ]

  const getIntensityColor = (level: number) => {
    const colors = [
      'var(--color-divider)',    // 0 - none
      '#dcfce7',                  // 1 - low
      '#86efac',                  // 2 - medium
      '#22c55e',                  // 3 - high
      '#15803d'                   // 4 - very high
    ]
    return colors[level] || colors[0]
  }

  const getContributionColor = (count: number) => {
    if (count === 0) return 'var(--color-divider)'
    if (count < 5) return '#dbeafe'
    if (count < 10) return '#93c5fd'
    if (count < 15) return '#3b82f6'
    return '#1e40af'
  }

  const weeklyHeatmap = generateWeeklyHeatmap()
  const contributions = generateContributions()

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
      }}>
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Activity Heatmap</h1>
          <p className="text-blue-100">Code activity patterns visualized by the agent</p>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Peak Day', value: 'Thursday', icon: <Calendar className="h-5 w-5" /> },
          { label: 'Peak Hour', value: '3 PM', icon: <Zap className="h-5 w-5" /> },
          { label: 'Consistency', value: '87%', icon: <TrendingUp className="h-5 w-5" /> },
          { label: 'Total Changes', value: '1,284', icon: <GitBranch className="h-5 w-5" /> }
        ].map((stat, i) => (
          <div key={i} className="rounded-lg p-4 shadow border" style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}>
            <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--color-primary)' }}>
              {stat.icon}
            </div>
            <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{stat.value}</p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* 7x24 Hour Heatmap */}
      <div className="mb-8 rounded-lg p-6 shadow border" style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Weekly Activity Grid (24 Hours × 7 Days)
          </h2>
          <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <span>Less</span>
            {[0, 1, 2, 3, 4].map(level => (
              <div
                key={level}
                className="w-4 h-4 rounded-sm"
                style={{ backgroundColor: getIntensityColor(level) }}
              ></div>
            ))}
            <span>More</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <div className="inline-grid gap-1" style={{ gridTemplateColumns: 'auto repeat(24, 1fr)' }}>
            {/* Hour headers */}
            <div></div>
            {Array.from({ length: 24 }, (_, i) => (
              <div key={i} className="text-xs text-center w-5" style={{ color: 'var(--color-text-secondary)' }}>
                {i % 6 === 0 ? i : ''}
              </div>
            ))}

            {/* Heatmap rows */}
            {weeklyHeatmap.map((dayData, dayIdx) => (
              <>
                <div key={`day-${dayIdx}`} className="text-xs py-1 pr-2" style={{ color: 'var(--color-text-secondary)' }}>
                  {dayData.day}
                </div>
                {dayData.hours.map((hour, hourIdx) => (
                  <div
                    key={`${dayIdx}-${hourIdx}`}
                    className="w-5 h-5 rounded-sm transition-all duration-200 hover:scale-125 hover:shadow-lg cursor-pointer"
                    style={{ backgroundColor: getIntensityColor(hour.intensity) }}
                    title={`${dayData.day} ${hour.hour}:00 - ${hour.intensity > 0 ? 'Activity level ' + hour.intensity : 'No activity'}`}
                  ></div>
                ))}
              </>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Contribution Calendar */}
        <div className="rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <h2 className="text-xl font-semibold mb-6" style={{ color: 'var(--color-text-primary)' }}>
            Daily Contributions (7 Weeks)
          </h2>
          <div className="flex gap-1">
            {contributions.map((week, weekIdx) => (
              <div key={weekIdx} className="flex flex-col gap-1">
                {week.map((day, dayIdx) => (
                  <div
                    key={`${weekIdx}-${dayIdx}`}
                    className="w-3 h-3 rounded-sm transition-all duration-200 hover:scale-150 hover:shadow-lg cursor-pointer"
                    style={{ backgroundColor: getContributionColor(day.count) }}
                    title={`${day.date.toLocaleDateString()}: ${day.count} changes`}
                  ></div>
                ))}
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between mt-4 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <span>Oct 1</span>
            <span>Nov 18</span>
          </div>
        </div>

        {/* File Type Activity Bubbles */}
        <div className="rounded-lg p-6 shadow border" style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}>
          <h2 className="text-xl font-semibold mb-6" style={{ color: 'var(--color-text-primary)' }}>
            File Type Distribution (Bubble Size = Changes)
          </h2>
          <div className="relative h-64">
            <svg width="100%" height="100%" viewBox="0 0 100 100">
              {fileTypeBubbles.map((bubble, idx) => (
                <g key={idx} className="cursor-pointer transition-all hover:opacity-80">
                  <circle
                    cx={bubble.x}
                    cy={bubble.y}
                    r={bubble.size / 10}
                    fill={`hsl(${idx * 60}, 70%, 60%)`}
                    opacity="0.7"
                  />
                  <text
                    x={bubble.x}
                    y={bubble.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="3"
                    fill="white"
                    fontWeight="bold"
                  >
                    {bubble.type.slice(0, 2)}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {fileTypeBubbles.map((bubble, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: `hsl(${idx * 60}, 70%, 60%)` }}
                ></div>
                <span style={{ color: 'var(--color-text-primary)' }}>
                  {bubble.type}: <span style={{ color: 'var(--color-text-secondary)' }}>{bubble.changes}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Change Intensity by Category */}
      <div className="rounded-lg p-6 shadow border" style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)'
      }}>
        <h2 className="text-xl font-semibold mb-6" style={{ color: 'var(--color-text-primary)' }}>
          Change Intensity Map (By Category)
        </h2>
        <div className="space-y-4">
          {intensityMap.map((row, rowIdx) => (
            <div key={rowIdx}>
              <div className="flex items-center gap-4">
                <div className="w-32 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  {row.category}
                </div>
                <div className="flex gap-1 flex-1">
                  {row.data.map((value, colIdx) => (
                    <div
                      key={colIdx}
                      className="flex-1 h-10 rounded transition-all duration-200 hover:scale-105 cursor-pointer"
                      style={{ backgroundColor: getIntensityColor(value) }}
                      title={`${['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][colIdx]}: Level ${value}`}
                    ></div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 mt-6 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          <span>Mon</span>
          <span className="flex-1 text-center">→</span>
          <span>Sun</span>
        </div>
      </div>
    </div>
  )
}
