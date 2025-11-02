import { useState } from 'react'
import { LayoutGrid, Minimize2, BarChart3, Clock, Grid, Layers, Columns, SplitSquareHorizontal, Eye, Table2, Calendar } from 'lucide-react'
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

export default function Insights() {
  const [currentLayout, setCurrentLayout] = useState<LayoutType>('minimalist')

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
    switch (currentLayout) {
      case 'minimalist':
        return <MinimalistLayout />
      case 'dashboard':
        return <DashboardLayout />
      case 'timeline':
        return <TimelineLayout />
      case 'heatmap':
        return <HeatmapLayout />
      case 'masonry':
        return <MasonryLayout />
      case 'kanban':
        return <KanbanLayout />
      case 'split':
        return <SplitLayout />
      case 'focus':
        return <FocusLayout />
      case 'grid':
        return <GridLayout />
      case 'calendar':
        return <CalendarLayout />
      default:
        return <MinimalistLayout />
    }
  }

  return (
    <div className="min-h-screen">
      {/* Layout Switcher */}
      <div className="mb-6 p-6 rounded-2xl shadow-lg border" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex items-center gap-3 mb-4">
          <LayoutGrid className="h-6 w-6" style={{ color: 'var(--color-primary)' }} />
          <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            Choose Your Layout
          </h2>
        </div>

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
