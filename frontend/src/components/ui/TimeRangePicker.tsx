import { useState } from 'react'
import { Calendar, ChevronLeft, ChevronRight, Clock } from 'lucide-react'

interface TimeRange {
  start: Date
  end: Date
}

interface TimeRangePickerProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
  className?: string
}

const QUICK_PRESETS = [
  { id: 'today', label: 'Today', description: 'All changes from today' },
  { id: 'yesterday', label: 'Yesterday', description: 'Changes from yesterday' },
  { id: 'last7days', label: 'Last 7 days', description: 'Past week of activity' },
  { id: 'thisWeek', label: 'This week', description: 'Monday to now' },
  { id: 'lastWeek', label: 'Last week', description: 'Previous full week' },
  { id: 'thisMonth', label: 'This month', description: 'Month to date' },
  { id: 'last30days', label: 'Last 30 days', description: 'Past month of activity' },
]

export default function TimeRangePicker({ value, onChange, className = '' }: TimeRangePickerProps) {
  const [mode, setMode] = useState<'preset' | 'calendar'>('preset')

  const normalizeStartOfDay = (d: Date) => {
    const x = new Date(d)
    x.setHours(0, 0, 0, 0)
    return x
  }

  const normalizeEndOfDay = (d: Date) => {
    const x = new Date(d)
    x.setHours(23, 59, 59, 999)
    return x
  }

  const isSameDay = (a: Date, b: Date) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()

  const isSameRange = (a: TimeRange, b: TimeRange) => isSameDay(a.start, b.start) && isSameDay(a.end, b.end)

  const handlePresetSelect = (presetId: string) => {
    const now = new Date()
    let start: Date
    let end: Date = now

    switch (presetId) {
      case 'today':
        start = normalizeStartOfDay(now)
        end = normalizeEndOfDay(now)
        break
      case 'yesterday':
        start = normalizeStartOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1))
        end = normalizeEndOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1))
        break
      case 'last7days':
        start = normalizeStartOfDay(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000))
        end = normalizeEndOfDay(now)
        break
      case 'thisWeek':
        const dayOfWeek = now.getDay()
        const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1
        start = normalizeStartOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - mondayOffset))
        end = normalizeEndOfDay(now)
        break
      case 'lastWeek':
        const lastWeekEnd = new Date(now.getTime() - now.getDay() * 24 * 60 * 60 * 1000)
        if (now.getDay() === 0) lastWeekEnd.setTime(lastWeekEnd.getTime() - 7 * 24 * 60 * 60 * 1000)
        const lastWeekStart = new Date(lastWeekEnd.getTime() - 6 * 24 * 60 * 60 * 1000)
        start = normalizeStartOfDay(lastWeekStart)
        end = normalizeEndOfDay(lastWeekEnd)
        break
      case 'thisMonth':
        start = normalizeStartOfDay(new Date(now.getFullYear(), now.getMonth(), 1))
        end = normalizeEndOfDay(now)
        break
      case 'last30days':
        start = normalizeStartOfDay(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000))
        end = normalizeEndOfDay(now)
        break
      default:
        start = normalizeStartOfDay(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000))
        end = normalizeEndOfDay(now)
    }

    onChange({ start, end })
  }

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
    })
  }

  const formatTimeRange = (range: TimeRange) => {
    const start = formatDate(range.start)
    const end = formatDate(range.end)
    
    if (start === end) {
      return start
    }
    return `${start} - ${end}`
  }

  const isToday = (date: Date) => {
    const today = new Date()
    return date.toDateString() === today.toDateString()
  }

  const isInRange = (date: Date) => {
    return date >= value.start && date <= value.end
  }

  const renderCalendar = () => {
    const [currentMonth, setCurrentMonth] = useState(new Date())
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()
    
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const firstDayWeekday = firstDay.getDay()
    
    const days = []
    
    // Previous month's trailing days
    for (let i = firstDayWeekday; i > 0; i--) {
      const date = new Date(year, month, -i + 1)
      days.push(
        <button
          key={`prev-${date.getDate()}`}
          className="w-8 h-8 text-xs opacity-40 hover:opacity-60 transition-opacity"
          style={{ color: 'var(--color-text-secondary)' }}
          onClick={() => {
            const newStart = new Date(date)
            newStart.setHours(0, 0, 0, 0)
            onChange({ start: newStart, end: value.end })
          }}
        >
          {date.getDate()}
        </button>
      )
    }
    
    // Current month's days
    for (let day = 1; day <= lastDay.getDate(); day++) {
      const date = new Date(year, month, day)
      const isSelected = isInRange(date)
      const isTodayDate = isToday(date)
      
      days.push(
        <button
          key={day}
          className={`w-8 h-8 text-xs rounded transition-all duration-200 ${
            isSelected 
              ? 'text-white font-semibold' 
              : 'hover:bg-opacity-20'
          }`}
          style={{
            backgroundColor: isSelected ? 'var(--color-primary)' : 'transparent',
            color: isSelected ? 'var(--color-text-inverse)' : 'var(--color-text-primary)',
            border: isTodayDate ? '2px solid var(--color-accent)' : 'none',
          }}
          onClick={() => {
            const newDate = new Date(date)
            newDate.setHours(0, 0, 0, 0)
            
            if (mode === 'calendar') {
              // Range selection logic
              if (!value.start || (value.start && value.end)) {
                // Start new range
                const endOfDay = new Date(newDate)
                endOfDay.setHours(23, 59, 59, 999)
                onChange({ start: newDate, end: endOfDay })
              } else {
                // Complete range
                if (newDate >= value.start) {
                  const endOfDay = new Date(newDate)
                  endOfDay.setHours(23, 59, 59, 999)
                  onChange({ start: value.start, end: endOfDay })
                } else {
                  const endOfDay = new Date(value.start)
                  endOfDay.setHours(23, 59, 59, 999)
                  onChange({ start: newDate, end: endOfDay })
                }
              }
            }
          }}
        >
          {day}
        </button>
      )
    }
    
    // Next month's leading days
    const remainingCells = 42 - days.length
    for (let i = 1; i <= remainingCells; i++) {
      const date = new Date(year, month + 1, i)
      days.push(
        <button
          key={`next-${i}`}
          className="w-8 h-8 text-xs opacity-40 hover:opacity-60 transition-opacity"
          style={{ color: 'var(--color-text-secondary)' }}
          onClick={() => {
            const newEnd = new Date(date)
            newEnd.setHours(23, 59, 59, 999)
            onChange({ start: value.start, end: newEnd })
          }}
        >
          {i}
        </button>
      )
    }
    
    return (
      <div 
        className="p-4 rounded-lg border"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)'
        }}
      >
        {/* Calendar Header */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))}
            className="p-1 rounded hover:bg-opacity-20 transition-colors"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <ChevronLeft size={16} />
          </button>
          
          <h3 
            className="font-semibold"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </h3>
          
          <button
            onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))}
            className="p-1 rounded hover:bg-opacity-20 transition-colors"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <ChevronRight size={16} />
          </button>
        </div>
        
        {/* Weekday Headers */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((day) => (
            <div 
              key={day}
              className="w-8 h-6 text-xs font-medium text-center flex items-center justify-center"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {day}
            </div>
          ))}
        </div>
        
        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-1">
          {days}
        </div>
        
        {/* Selected Range Display */}
        <div 
          className="mt-4 p-2 rounded text-sm text-center"
          style={{
            backgroundColor: 'var(--color-background)',
            color: 'var(--color-text-secondary)'
          }}
        >
          Selected: {formatTimeRange(value)}
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Mode Selection */}
      <div className="flex space-x-1">
        {[
          { id: 'preset', label: 'Quick Select', icon: Clock },
          { id: 'calendar', label: 'Calendar', icon: Calendar },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setMode(id as any)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2`}
            style={{
              backgroundColor: mode === id ? 'var(--color-primary)' : 'var(--color-surface)',
              color: mode === id ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
              border: `1px solid ${mode === id ? 'var(--color-primary)' : 'var(--color-border)'}`
            }}
          >
            {Icon && <Icon size={14} />}
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Content based on mode */}
      {mode === 'preset' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {QUICK_PRESETS.map((preset) => {
              const now = new Date()
              let presetRange: TimeRange = { start: value.start, end: value.end }
              switch (preset.id) {
                case 'today':
                  presetRange = { start: normalizeStartOfDay(now), end: normalizeEndOfDay(now) }
                  break
                case 'yesterday':
                  presetRange = {
                    start: normalizeStartOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)),
                    end: normalizeEndOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1))
                  }
                  break
                case 'last7days':
                  presetRange = { start: normalizeStartOfDay(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)), end: normalizeEndOfDay(now) }
                  break
                case 'thisWeek':
                  const dow = now.getDay()
                  const mondayOffset = dow === 0 ? 6 : dow - 1
                  presetRange = { start: normalizeStartOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - mondayOffset)), end: normalizeEndOfDay(now) }
                  break
                case 'lastWeek':
                  const lastWeekEndX = new Date(now.getTime() - now.getDay() * 24 * 60 * 60 * 1000)
                  if (now.getDay() === 0) lastWeekEndX.setTime(lastWeekEndX.getTime() - 7 * 24 * 60 * 60 * 1000)
                  const lastWeekStartX = new Date(lastWeekEndX.getTime() - 6 * 24 * 60 * 60 * 1000)
                  presetRange = { start: normalizeStartOfDay(lastWeekStartX), end: normalizeEndOfDay(lastWeekEndX) }
                  break
                case 'thisMonth':
                  presetRange = { start: normalizeStartOfDay(new Date(now.getFullYear(), now.getMonth(), 1)), end: normalizeEndOfDay(now) }
                  break
                case 'last30days':
                  presetRange = { start: normalizeStartOfDay(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)), end: normalizeEndOfDay(now) }
                  break
              }
              const active = isSameRange({ start: normalizeStartOfDay(value.start), end: normalizeEndOfDay(value.end) }, presetRange)
              return (
                <button
                  key={preset.id}
                  onClick={() => handlePresetSelect(preset.id)}
                  className="p-3 rounded-lg border text-left hover:scale-[1.02] transition-all duration-200"
                  style={{
                    backgroundColor: active ? 'var(--color-primary)' : 'var(--color-surface)',
                    borderColor: active ? 'var(--color-primary)' : 'var(--color-border)',
                    color: active ? 'var(--color-text-inverse)' : 'var(--color-text-primary)'
                  }}
                >
                  <div 
                    className="font-medium text-sm"
                    style={{ color: 'inherit' }}
                  >
                    {preset.label}
                  </div>
                  <div 
                    className="text-xs mt-1"
                    style={{ color: 'inherit', opacity: 0.9 }}
                  >
                    {preset.description}
                  </div>
                </button>
              )
            })}
          </div>
          
          {/* Current Selection Display */}
          <div 
            className="p-3 rounded-lg border text-center"
            style={{
              backgroundColor: 'var(--color-background)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)'
            }}
          >
            Current selection: <span style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>
              {formatTimeRange(value)}
            </span>
          </div>
        </div>
      )}

      {mode === 'calendar' && renderCalendar()}
    </div>
  )
}