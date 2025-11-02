import { useMemo } from 'react'
import { Calendar, Zap, TrendingUp, GitBranch } from 'lucide-react'

interface HeatmapLayoutProps {
  className?: string
}

// Mock data generators
const generateHourlyActivityGrid = () => {
  const grid: number[][] = []
  for (let day = 0; day < 7; day++) {
    const dayData: number[] = []
    for (let hour = 0; hour < 24; hour++) {
      dayData.push(Math.floor(Math.random() * 50))
    }
    grid.push(dayData)
  }
  return grid
}

const generateDailyContributions = () => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  return days.map(day => ({
    day,
    value: Math.floor(Math.random() * 200) + 20,
    date: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000)
  }))
}

const generateFileTypeBubbles = () => {
  const types = [
    { name: 'TypeScript', changes: 342, color: '#3b82f6' },
    { name: 'JavaScript', changes: 298, color: '#f59e0b' },
    { name: 'React', changes: 187, color: '#06b6d4' },
    { name: 'CSS', changes: 143, color: '#8b5cf6' },
    { name: 'JSON', changes: 98, color: '#ec4899' },
    { name: 'Markdown', changes: 67, color: '#10b981' }
  ]
  const maxChanges = Math.max(...types.map(t => t.changes))
  return types.map(type => ({
    ...type,
    size: (type.changes / maxChanges) * 100
  }))
}

const getHeatmapColor = (value: number, max: number): string => {
  const intensity = value / max
  if (intensity === 0) return '#e5e7eb'
  if (intensity < 0.2) return '#d4d4d8'
  if (intensity < 0.4) return '#90ee90'
  if (intensity < 0.6) return '#32d46a'
  if (intensity < 0.8) return '#10b981'
  return '#047857'
}

export function HeatmapLayout({ className = '' }: HeatmapLayoutProps) {
  const hourlyActivityGrid = useMemo(() => generateHourlyActivityGrid(), [])
  const dailyContributions = useMemo(() => generateDailyContributions(), [])
  const fileTypeBubbles = useMemo(() => generateFileTypeBubbles(), [])

  const maxHourlyValue = useMemo(
    () => Math.max(...hourlyActivityGrid.flat()),
    [hourlyActivityGrid]
  )
  const maxDailyValue = useMemo(
    () => Math.max(...dailyContributions.map(d => d.value)),
    [dailyContributions]
  )

  return (
    <div className={`w-full space-y-8 ${className}`}>
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, #10b981 0%, #06b6d4 50%, #3b82f6 100%)'
      }}>
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

        <div className="relative z-10 flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                <Zap className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Activity Heatmap</h1>
            </div>
            <p className="text-green-100 text-lg">Visualize your work intensity and patterns</p>
          </div>

          <div className="flex items-center space-x-4 px-6 py-3 rounded-full backdrop-blur-sm border border-white/20 bg-white/10">
            <div className="w-2 h-2 rounded-full bg-yellow-300 animate-pulse"></div>
            <span className="text-sm font-medium">Real-time</span>
          </div>
        </div>
      </div>

      {/* Hour-by-Hour Grid (7x24) */}
      <div className="rounded-2xl p-8 shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center space-x-3 mb-6">
          <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-primary)' }}>
            <Calendar className="h-5 w-5" style={{ color: 'white' }} />
          </div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Week Activity (Hour-by-Hour)
          </h2>
        </div>

        <div className="overflow-x-auto">
          <div className="inline-block min-w-full p-4 bg-white rounded-lg border" style={{ borderColor: 'var(--color-border)' }}>
            {/* Hour labels */}
            <div className="flex mb-4">
              <div className="w-16 flex-shrink-0"></div>
              <div className="flex gap-1">
                {Array.from({ length: 24 }).map((_, hour) => (
                  <div
                    key={hour}
                    className="w-12 h-6 flex items-center justify-center text-xs font-semibold"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {hour.toString().padStart(2, '0')}
                  </div>
                ))}
              </div>
            </div>

            {/* Days */}
            <div className="space-y-2">
              {hourlyActivityGrid.map((dayData, dayIndex) => (
                <div key={dayIndex} className="flex gap-2">
                  <div className="w-16 flex-shrink-0 flex items-center">
                    <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                      {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][dayIndex]}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {dayData.map((value, hourIndex) => (
                      <div
                        key={`${dayIndex}-${hourIndex}`}
                        className="w-12 h-8 rounded cursor-pointer transition-transform hover:scale-110 hover:shadow-md"
                        style={{
                          backgroundColor: getHeatmapColor(value, maxHourlyValue),
                          border: '1px solid rgba(0, 0, 0, 0.05)'
                        }}
                        title={`${value} changes at ${hourIndex}:00`}
                      ></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Heatmap Legend */}
        <div className="mt-6 flex items-center space-x-4 text-sm">
          <span style={{ color: 'var(--color-text-secondary)' }} className="font-semibold">Intensity:</span>
          <div className="flex gap-2 items-center">
            <div className="w-6 h-6 rounded" style={{ backgroundColor: '#e5e7eb' }}></div>
            <span style={{ color: 'var(--color-text-secondary)' }}>None</span>
          </div>
          <div className="flex gap-2 items-center">
            <div className="w-6 h-6 rounded" style={{ backgroundColor: '#d4d4d8' }}></div>
            <span style={{ color: 'var(--color-text-secondary)' }}>Low</span>
          </div>
          <div className="flex gap-2 items-center">
            <div className="w-6 h-6 rounded" style={{ backgroundColor: '#90ee90' }}></div>
            <span style={{ color: 'var(--color-text-secondary)' }}>Medium</span>
          </div>
          <div className="flex gap-2 items-center">
            <div className="w-6 h-6 rounded" style={{ backgroundColor: '#10b981' }}></div>
            <span style={{ color: 'var(--color-text-secondary)' }}>High</span>
          </div>
          <div className="flex gap-2 items-center">
            <div className="w-6 h-6 rounded" style={{ backgroundColor: '#047857' }}></div>
            <span style={{ color: 'var(--color-text-secondary)' }}>Very High</span>
          </div>
        </div>
      </div>

      {/* Daily Contribution Graph (GitHub-style) */}
      <div className="rounded-2xl p-8 shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center space-x-3 mb-6">
          <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-success)' }}>
            <GitBranch className="h-5 w-5" style={{ color: 'white' }} />
          </div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Daily Contributions (GitHub-style)
          </h2>
        </div>

        <div className="flex gap-12">
          {/* Calendar grid */}
          <div className="flex-1">
            <div className="grid grid-cols-7 gap-2">
              {Array.from({ length: 49 }).map((_, index) => {
                const day = index % 7
                const week = Math.floor(index / 7)
                const randomValue = Math.floor(Math.random() * dailyContributions[day]?.value || 100)
                const maxVal = dailyContributions[day]?.value || 100

                return (
                  <div
                    key={index}
                    className="w-6 h-6 rounded cursor-pointer transition-transform hover:scale-125 hover:shadow-lg border border-gray-200"
                    style={{
                      backgroundColor: getHeatmapColor(randomValue, maxVal * 2),
                      boxShadow: randomValue > 0 ? 'inset 0 0 2px rgba(0, 0, 0, 0.1)' : 'none'
                    }}
                    title={`${randomValue} changes - Week ${week}, Day ${day}`}
                  ></div>
                )
              })}
            </div>

            <p className="text-xs mt-4" style={{ color: 'var(--color-text-secondary)' }}>
              7 weeks of contribution activity
            </p>
          </div>

          {/* Statistics sidebar */}
          <div className="w-48 space-y-4">
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-divider)' }}>
              <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {dailyContributions.reduce((sum, d) => sum + d.value, 0)}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                Total contributions
              </p>
            </div>

            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-divider)' }}>
              <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {Math.round(dailyContributions.reduce((sum, d) => sum + d.value, 0) / 7)}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                Average per day
              </p>
            </div>

            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-divider)' }}>
              <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {Math.max(...dailyContributions.map(d => d.value))}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                Peak day
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* File Type Activity Bubbles */}
      <div className="rounded-2xl p-8 shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center space-x-3 mb-8">
          <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-accent)' }}>
            <TrendingUp className="h-5 w-5" style={{ color: 'white' }} />
          </div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            File Type Activity (Bubble Map)
          </h2>
        </div>

        <div className="relative h-80 rounded-lg overflow-hidden border" style={{
          backgroundColor: 'rgba(0, 0, 0, 0.02)',
          borderColor: 'var(--color-divider)'
        }}>
          <svg className="w-full h-full" style={{ filter: 'url(#bubble-shadow)' }}>
            <defs>
              <filter id="bubble-shadow">
                <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
              </filter>
            </defs>

            {fileTypeBubbles.map((file, index) => {
              const angle = (index / fileTypeBubbles.length) * Math.PI * 2
              const radius = 100
              const cx = 50 + radius * Math.cos(angle)
              const cy = 50 + radius * Math.sin(angle)
              const r = 8 + (file.size / 100) * 12

              return (
                <g key={index}>
                  <circle
                    cx={`${cx}%`}
                    cy={`${cy}%`}
                    r={`${r}%`}
                    fill={file.color}
                    opacity="0.8"
                    style={{
                      transition: 'all 0.3s ease',
                      cursor: 'pointer',
                      filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))'
                    }}
                    className="hover:opacity-100"
                  />
                  <text
                    x={`${cx}%`}
                    y={`${cy}%`}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="text-xs font-bold"
                    fill="white"
                    style={{ pointerEvents: 'none' }}
                  >
                    {file.name.split('')[0]}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* Bubble Legend */}
        <div className="mt-8 grid grid-cols-2 md:grid-cols-3 gap-4">
          {fileTypeBubbles.map((file, index) => (
            <div key={index} className="flex items-center space-x-3 p-3 rounded-lg" style={{
              backgroundColor: 'var(--color-divider)'
            }}>
              <div
                className="w-4 h-4 rounded-full flex-shrink-0"
                style={{ backgroundColor: file.color }}
              ></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
                  {file.name}
                </p>
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  {file.changes} changes
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Change Intensity Heatmap (Weekly) */}
      <div className="rounded-2xl p-8 shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <h2 className="text-xl font-semibold mb-6" style={{ color: 'var(--color-text-primary)' }}>
          Change Intensity Map
        </h2>

        <div className="space-y-6">
          {[
            { label: 'Bug Fixes', data: Array.from({ length: 7 }, () => Math.floor(Math.random() * 50)), color: '#ef4444' },
            { label: 'Features', data: Array.from({ length: 7 }, () => Math.floor(Math.random() * 50)), color: '#3b82f6' },
            { label: 'Documentation', data: Array.from({ length: 7 }, () => Math.floor(Math.random() * 50)), color: '#8b5cf6' },
            { label: 'Refactoring', data: Array.from({ length: 7 }, () => Math.floor(Math.random() * 50)), color: '#f59e0b' }
          ].map((category, catIndex) => {
            const maxVal = Math.max(...category.data)

            return (
              <div key={catIndex}>
                <div className="flex items-center space-x-3 mb-3">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: category.color }}
                  ></div>
                  <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    {category.label}
                  </span>
                </div>

                <div className="flex gap-2">
                  {category.data.map((value, dayIndex) => (
                    <div
                      key={dayIndex}
                      className="flex-1 h-12 rounded-lg cursor-pointer transition-transform hover:scale-105 hover:shadow-md border border-gray-200 flex items-center justify-center text-xs font-semibold"
                      style={{
                        backgroundColor: getHeatmapColor(value, maxVal),
                        color: value > maxVal * 0.5 ? 'white' : 'var(--color-text-secondary)'
                      }}
                      title={`${value} changes - Day ${dayIndex}`}
                    >
                      {value}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="rounded-2xl p-8 shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <h2 className="text-xl font-semibold mb-6" style={{ color: 'var(--color-text-primary)' }}>
          Heatmap Summary
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="p-6 rounded-xl" style={{
            backgroundColor: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1))',
            border: '2px solid rgba(16, 185, 129, 0.2)'
          }}>
            <p className="text-3xl font-bold text-green-600 mb-2">
              {Math.round(hourlyActivityGrid.flat().reduce((a, b) => a + b, 0) / hourlyActivityGrid.flat().length)}
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Avg hourly changes
            </p>
          </div>

          <div className="p-6 rounded-xl" style={{
            backgroundColor: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.1))',
            border: '2px solid rgba(59, 130, 246, 0.2)'
          }}>
            <p className="text-3xl font-bold text-blue-600 mb-2">
              {maxHourlyValue}
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Peak hourly activity
            </p>
          </div>

          <div className="p-6 rounded-xl" style={{
            backgroundColor: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(168, 85, 247, 0.1))',
            border: '2px solid rgba(139, 92, 246, 0.2)'
          }}>
            <p className="text-3xl font-bold text-purple-600 mb-2">
              {fileTypeBubbles.length}
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              File type categories
            </p>
          </div>

          <div className="p-6 rounded-xl" style={{
            backgroundColor: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(236, 72, 153, 0.1))',
            border: '2px solid rgba(245, 158, 11, 0.2)'
          }}>
            <p className="text-3xl font-bold text-yellow-600 mb-2">
              {dailyContributions.filter(d => d.value > 50).length}
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              High activity days
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HeatmapLayout
