import { useState } from 'react'
import { LayoutGrid, Minimize2, BarChart3, Clock, Grid, Layers, Columns, SplitSquareHorizontal, Eye, Table2, Calendar, CalendarIcon, Settings } from 'lucide-react'
import MinimalistLayout from '../components/layouts/MinimalistLayout'
import DashboardLayout from '../components/layouts/DashboardLayout'
import TimelineLayout from '../components/layouts/TimelineLayout'
import HeatmapLayout from '../components/layouts/HeatmapLayout'
import MasonryLayout from '../components/layouts/MasonryLayout'
import KanbanLayout from '../components/layouts/KanbanLayout'
import SplitLayout from '../components/layouts/SplitLayout'
import FocusLayout from '../components/layouts/FocusLayout'
import GridLayout from '../components/layouts/GridLayout'
import CalendarLayout from '../components/layouts/CalendarLayout'

type LayoutType = 'minimalist' | 'dashboard' | 'timeline' | 'heatmap' | 'masonry' | 'kanban' | 'split' | 'focus' | 'grid' | 'calendar'

interface LayoutOption {
  id: LayoutType
  name: string
  description: string
  icon: React.ReactNode
}

interface DateRange {
  start: string
  end: string
  days?: number
}

export default function Insights() {
  const [currentLayout, setCurrentLayout] = useState<LayoutType>('masonry')
  const [dateRangePreset, setDateRangePreset] = useState<string>('7d')
  const [showCustomDate, setShowCustomDate] = useState(false)
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')

  // Calculate date range based on preset or custom dates
  const getDateRange = (): DateRange => {
    if (showCustomDate && customStartDate && customEndDate) {
      return {
        start: customStartDate,
        end: customEndDate
      }
    }

    // Parse preset (e.g., "7d", "30d", "1d")
    const match = dateRangePreset.match(/^(\d+)([dDwWmMyY])$/)
    if (!match) {
      // Default to 7 days
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0],
        days: 7
      }
    }

    const value = parseInt(match[1], 10)
    const unit = match[2].toLowerCase()

    let days = value
    switch (unit) {
      case 'w':
        days = value * 7
        break
      case 'm':
        days = value * 30
        break
      case 'y':
        days = value * 365
        break
    }

    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - days)

    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      days
    }
  }

  const dateRange = getDateRange()

  const layoutOptions: LayoutOption[] = [
    {
      id: 'minimalist',
      name: 'Minimalist',
      description: 'Clean zen design',
      icon: <Minimize2 className="h-4 w-4" />
    },
    {
      id: 'dashboard',
      name: 'Dashboard',
      description: 'Dense metrics view',
      icon: <BarChart3 className="h-4 w-4" />
    },
    {
      id: 'timeline',
      name: 'Timeline',
      description: 'Story format',
      icon: <Clock className="h-4 w-4" />
    },
    {
      id: 'heatmap',
      name: 'Heatmap',
      description: 'Visual intensity',
      icon: <Grid className="h-4 w-4" />
    },
    {
      id: 'masonry',
      name: 'Masonry',
      description: 'Staggered grid',
      icon: <Layers className="h-4 w-4" />
    },
    {
      id: 'kanban',
      name: 'Kanban',
      description: 'Board columns',
      icon: <Columns className="h-4 w-4" />
    },
    {
      id: 'split',
      name: 'Split',
      description: 'Side by side',
      icon: <SplitSquareHorizontal className="h-4 w-4" />
    },
    {
      id: 'focus',
      name: 'Focus',
      description: 'One at a time',
      icon: <Eye className="h-4 w-4" />
    },
    {
      id: 'grid',
      name: 'Grid',
      description: 'Data table view',
      icon: <Table2 className="h-4 w-4" />
    },
    {
      id: 'calendar',
      name: 'Calendar',
      description: 'Monthly view',
      icon: <Calendar className="h-4 w-4" />
    }
  ]

  const renderLayout = () => {
    // Pass dateRange to all layouts
    const layoutProps = { dateRange }

    switch (currentLayout) {
      case 'minimalist':
        return <MinimalistLayout {...layoutProps} />
      case 'dashboard':
        return <DashboardLayout {...layoutProps} />
      case 'timeline':
        return <TimelineLayout {...layoutProps} />
      case 'heatmap':
        return <HeatmapLayout {...layoutProps} />
      case 'masonry':
        return <MasonryLayout {...layoutProps} />
      case 'kanban':
        return <KanbanLayout {...layoutProps} />
      case 'split':
        return <SplitLayout {...layoutProps} />
      case 'focus':
        return <FocusLayout {...layoutProps} />
      case 'grid':
        return <GridLayout {...layoutProps} />
      case 'calendar':
        return <CalendarLayout {...layoutProps} />
      default:
        return <MasonryLayout {...layoutProps} />
    }
  }

  return (
    <div className="min-h-screen">
      {/* Layout Switcher & Date Range Picker */}
      <div className="mb-6 p-6 rounded-2xl shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        {/* Header with Date Range */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <LayoutGrid className="h-6 w-6" style={{ color: 'var(--color-primary)' }} />
            <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
              Insights Dashboard
            </h2>
          </div>

          {/* Date Range Controls */}
          <div className="flex items-center gap-3">
            <CalendarIcon className="h-5 w-5" style={{ color: 'var(--color-text-secondary)' }} />

            {/* Quick Presets */}
            {!showCustomDate && (
              <div className="flex gap-2">
                {['1d', '7d', '30d', '90d'].map(preset => (
                  <button
                    key={preset}
                    onClick={() => setDateRangePreset(preset)}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      dateRangePreset === preset ? 'font-semibold' : ''
                    }`}
                    style={{
                      backgroundColor: dateRangePreset === preset ? 'var(--color-primary)' : 'var(--color-surface)',
                      color: dateRangePreset === preset ? 'var(--color-text-inverse)' : 'var(--color-text)',
                      border: '1px solid var(--color-border)'
                    }}
                  >
                    {preset === '1d' ? 'Today' : preset === '7d' ? 'Week' : preset === '30d' ? 'Month' : '3 Months'}
                  </button>
                ))}
                <button
                  onClick={() => setShowCustomDate(true)}
                  className="px-3 py-1 rounded text-sm transition-colors"
                  style={{
                    backgroundColor: 'var(--color-surface)',
                    color: 'var(--color-text)',
                    border: '1px solid var(--color-border)'
                  }}
                >
                  Custom
                </button>
              </div>
            )}

            {/* Custom Date Inputs */}
            {showCustomDate && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                  className="px-3 py-1 rounded text-sm"
                  style={{
                    backgroundColor: 'var(--color-surface)',
                    color: 'var(--color-text)',
                    border: '1px solid var(--color-border)'
                  }}
                />
                <span style={{ color: 'var(--color-text-secondary)' }}>to</span>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                  className="px-3 py-1 rounded text-sm"
                  style={{
                    backgroundColor: 'var(--color-surface)',
                    color: 'var(--color-text)',
                    border: '1px solid var(--color-border)'
                  }}
                />
                <button
                  onClick={() => {
                    setShowCustomDate(false)
                    setCustomStartDate('')
                    setCustomEndDate('')
                  }}
                  className="px-3 py-1 rounded text-sm transition-colors"
                  style={{
                    backgroundColor: 'var(--color-surface)',
                    color: 'var(--color-text)',
                    border: '1px solid var(--color-border)'
                  }}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Layout Options */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-10 gap-3">
          {layoutOptions.map((layout) => (
            <button
              key={layout.id}
              onClick={() => setCurrentLayout(layout.id)}
              className={`group relative overflow-hidden rounded-xl p-4 border-2 transition-all duration-300 transform hover:scale-105 ${
                currentLayout === layout.id
                  ? 'shadow-lg'
                  : 'hover:shadow-md'
              }`}
              style={{
                backgroundColor: currentLayout === layout.id ? 'var(--color-primary)' : 'var(--color-surface)',
                borderColor: currentLayout === layout.id ? 'var(--color-primary)' : 'var(--color-border)',
                color: currentLayout === layout.id ? 'var(--color-text-inverse)' : 'var(--color-text-primary)'
              }}
            >
              {currentLayout === layout.id && (
                <div
                  className="absolute inset-0 opacity-20"
                  style={{
                    background: 'linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.2) 100%)'
                  }}
                ></div>
              )}

              <div className="relative flex flex-col items-center text-center space-y-2">
                <div className={`p-2 rounded-lg ${
                  currentLayout === layout.id ? 'bg-white/20' : ''
                }`} style={{
                  color: currentLayout === layout.id ? 'var(--color-text-inverse)' : 'var(--color-primary)'
                }}>
                  {layout.icon}
                </div>
                <div>
                  <p className="font-semibold text-sm">{layout.name}</p>
                  <p className={`text-xs mt-1 ${
                    currentLayout === layout.id ? 'opacity-90' : ''
                  }`} style={{
                    color: currentLayout === layout.id ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)'
                  }}>
                    {layout.description}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Render Selected Layout */}
      {renderLayout()}
    </div>
  )
}
