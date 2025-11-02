import { Calendar, Activity, GitCommit, FileText, Code, Zap, TrendingUp, Clock } from 'lucide-react'
import { useState } from 'react'

export default function CalendarLayout() {
  const [selectedDay, setSelectedDay] = useState<number | null>(15)

  // Generate calendar data
  const daysInMonth = 30
  const startDay = 2 // 0 = Sunday, 1 = Monday, etc.
  
  const calendarData = Array.from({ length: daysInMonth }, (_, i) => {
    const day = i + 1
    const intensity = Math.floor(Math.random() * 100)
    const hasActivity = intensity > 20
    
    return {
      day,
      intensity,
      hasActivity,
      changes: hasActivity ? Math.floor(Math.random() * 150) + 10 : 0,
      commits: hasActivity ? Math.floor(Math.random() * 10) + 1 : 0,
      files: hasActivity ? Math.floor(Math.random() * 30) + 5 : 0,
      activeTime: hasActivity ? `${Math.floor(Math.random() * 8) + 1}h ${Math.floor(Math.random() * 60)}m` : '0h'
    }
  })

  const getIntensityColor = (intensity: number) => {
    if (intensity === 0) return 'var(--color-surface)'
    if (intensity < 30) return '#3b82f620'
    if (intensity < 60) return '#3b82f660'
    if (intensity < 80) return '#3b82f6a0'
    return 'var(--color-primary)'
  }

  const getIntensityBorder = (intensity: number) => {
    if (intensity === 0) return 'var(--color-border)'
    if (intensity < 30) return '#3b82f640'
    if (intensity < 60) return '#3b82f680'
    return 'var(--color-primary)'
  }

  const selectedData = selectedDay ? calendarData[selectedDay - 1] : null

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Calendar className="h-8 w-8" style={{ color: 'var(--color-primary)' }} />
          <h1 className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            Calendar View
          </h1>
        </div>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Monthly activity calendar with daily insights
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Calendar */}
        <div className="xl:col-span-2">
          <div
            className="rounded-2xl p-6 border shadow-lg"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            {/* Month Header */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                November 2025
              </h2>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  <span>Less</span>
                  <div className="flex gap-1">
                    {[0, 25, 50, 75, 100].map((intensity, i) => (
                      <div
                        key={i}
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: getIntensityColor(intensity) }}
                      />
                    ))}
                  </div>
                  <span>More</span>
                </div>
              </div>
            </div>

            {/* Week Days */}
            <div className="grid grid-cols-7 gap-2 mb-2">
              {weekDays.map((day) => (
                <div
                  key={day}
                  className="text-center text-sm font-semibold py-2"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-2">
              {/* Empty cells for days before month starts */}
              {Array.from({ length: startDay }).map((_, i) => (
                <div key={`empty-${i}`} className="aspect-square" />
              ))}

              {/* Calendar days */}
              {calendarData.map((data) => (
                <button
                  key={data.day}
                  onClick={() => setSelectedDay(data.day)}
                  className={`aspect-square rounded-xl border-2 transition-all duration-200 hover:scale-105 ${
                    selectedDay === data.day ? 'ring-2' : ''
                  }`}
                  style={{
                    backgroundColor: getIntensityColor(data.intensity),
                    borderColor: selectedDay === data.day 
                      ? 'var(--color-primary)' 
                      : getIntensityBorder(data.intensity),
                    ringColor: 'var(--color-primary)'
                  }}
                >
                  <div className="flex flex-col items-center justify-center h-full p-1">
                    <span
                      className="text-sm font-bold"
                      style={{
                        color: data.intensity > 60 ? '#ffffff' : 'var(--color-text-primary)'
                      }}
                    >
                      {data.day}
                    </span>
                    {data.hasActivity && (
                      <div className="flex gap-[2px] mt-1">
                        {data.changes > 50 && (
                          <div
                            className="w-1 h-1 rounded-full"
                            style={{ backgroundColor: data.intensity > 60 ? '#ffffff' : 'var(--color-primary)' }}
                          />
                        )}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Daily Details */}
        <div className="xl:col-span-1">
          {selectedData ? (
            <div className="space-y-4">
              {/* Day Info Card */}
              <div
                className="rounded-2xl p-6 border shadow-lg"
                style={{
                  backgroundColor: 'var(--color-surface)',
                  borderColor: 'var(--color-border)'
                }}
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                    Day {selectedData.day}
                  </h3>
                  <div
                    className="px-3 py-1 rounded-full text-xs font-semibold"
                    style={{
                      backgroundColor: `${getIntensityColor(selectedData.intensity)}40`,
                      color: 'var(--color-primary)'
                    }}
                  >
                    {selectedData.intensity}% Active
                  </div>
                </div>

                {selectedData.hasActivity ? (
                  <div className="space-y-4">
                    {/* Metrics */}
                    <div className="grid grid-cols-2 gap-3">
                      <div
                        className="p-4 rounded-xl"
                        style={{ backgroundColor: 'var(--color-background)' }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Activity className="h-4 w-4" style={{ color: '#3b82f6' }} />
                          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            Changes
                          </p>
                        </div>
                        <p className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                          {selectedData.changes}
                        </p>
                      </div>

                      <div
                        className="p-4 rounded-xl"
                        style={{ backgroundColor: 'var(--color-background)' }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <GitCommit className="h-4 w-4" style={{ color: '#10b981' }} />
                          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            Commits
                          </p>
                        </div>
                        <p className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                          {selectedData.commits}
                        </p>
                      </div>

                      <div
                        className="p-4 rounded-xl"
                        style={{ backgroundColor: 'var(--color-background)' }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="h-4 w-4" style={{ color: '#8b5cf6' }} />
                          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            Files
                          </p>
                        </div>
                        <p className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                          {selectedData.files}
                        </p>
                      </div>

                      <div
                        className="p-4 rounded-xl"
                        style={{ backgroundColor: 'var(--color-background)' }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Clock className="h-4 w-4" style={{ color: '#f59e0b' }} />
                          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            Time
                          </p>
                        </div>
                        <p className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                          {selectedData.activeTime}
                        </p>
                      </div>
                    </div>

                    {/* Activity Bar */}
                    <div>
                      <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                        Intensity
                      </p>
                      <div
                        className="h-2 rounded-full overflow-hidden"
                        style={{ backgroundColor: 'var(--color-background)' }}
                      >
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            backgroundColor: 'var(--color-primary)',
                            width: `${selectedData.intensity}%`
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Zap className="h-12 w-12 mx-auto mb-3 opacity-20" style={{ color: 'var(--color-text-secondary)' }} />
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                      No activity recorded
                    </p>
                  </div>
                )}
              </div>

              {/* Stats Card */}
              <div
                className="rounded-2xl p-6 border shadow-lg"
                style={{
                  backgroundColor: 'var(--color-surface)',
                  borderColor: 'var(--color-border)'
                }}
              >
                <h4 className="text-lg font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                  Month Summary
                </h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" style={{ color: '#10b981' }} />
                      <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        Active Days
                      </span>
                    </div>
                    <span className="font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      24/30
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Code className="h-4 w-4" style={{ color: '#3b82f6' }} />
                      <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        Total Changes
                      </span>
                    </div>
                    <span className="font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      1,284
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Activity className="h-4 w-4" style={{ color: '#8b5cf6' }} />
                      <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        Avg Intensity
                      </span>
                    </div>
                    <span className="font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      67%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div
              className="rounded-2xl p-12 border text-center"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)'
              }}
            >
              <Calendar className="h-16 w-16 mx-auto mb-4 opacity-20" style={{ color: 'var(--color-text-secondary)' }} />
              <p style={{ color: 'var(--color-text-secondary)' }}>
                Select a day to view details
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
