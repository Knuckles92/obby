import { Activity, FileText, GitCommit, Code, TrendingUp, Zap, BarChart3, Clock, Target, Sparkles, Calendar, Users, Folder } from 'lucide-react'

export default function GridLayout() {
  const gridData = [
    {
      category: 'Activity',
      icon: <Activity className="h-5 w-5" />,
      color: '#3b82f6',
      items: [
        { label: 'Total Changes', value: '1,284', trend: '+12%' },
        { label: 'Active Time', value: '6h 32m', trend: '+8%' },
        { label: 'Intensity Score', value: '87%', trend: '+5%' },
        { label: 'Peak Hour', value: '3 PM', trend: 'stable' }
      ]
    },
    {
      category: 'Files',
      icon: <FileText className="h-5 w-5" />,
      color: '#10b981',
      items: [
        { label: 'Modified', value: '47', trend: '+15%' },
        { label: 'Created', value: '12', trend: '+3%' },
        { label: 'Deleted', value: '8', trend: '-2%' },
        { label: 'Avg Size', value: '324 KB', trend: 'stable' }
      ]
    },
    {
      category: 'Code',
      icon: <Code className="h-5 w-5" />,
      color: '#8b5cf6',
      items: [
        { label: 'Lines Added', value: '4,823', trend: '+18%' },
        { label: 'Lines Deleted', value: '3,547', trend: '+12%' },
        { label: 'Net Change', value: '+1,276', trend: '+23%' },
        { label: 'Complexity', value: 'Medium', trend: 'stable' }
      ]
    },
    {
      category: 'Commits',
      icon: <GitCommit className="h-5 w-5" />,
      color: '#f59e0b',
      items: [
        { label: 'Total', value: '23', trend: '+4%' },
        { label: 'Avg Size', value: '156 lines', trend: '+8%' },
        { label: 'Largest', value: '892 lines', trend: 'new' },
        { label: 'Frequency', value: '3.2/day', trend: '-5%' }
      ]
    },
    {
      category: 'Languages',
      icon: <Sparkles className="h-5 w-5" />,
      color: '#ec4899',
      items: [
        { label: 'TypeScript', value: '45%', trend: '+3%' },
        { label: 'Python', value: '30%', trend: '-2%' },
        { label: 'CSS', value: '15%', trend: '+5%' },
        { label: 'Other', value: '10%', trend: 'stable' }
      ]
    },
    {
      category: 'Performance',
      icon: <Zap className="h-5 w-5" />,
      color: '#f97316',
      items: [
        { label: 'Build Time', value: '2.3s', trend: '-12%' },
        { label: 'Test Coverage', value: '78%', trend: '+5%' },
        { label: 'Lint Errors', value: '3', trend: '-67%' },
        { label: 'Bundle Size', value: '245 KB', trend: '+2%' }
      ]
    },
    {
      category: 'Patterns',
      icon: <Target className="h-5 w-5" />,
      color: '#06b6d4',
      items: [
        { label: 'Refactoring', value: '34%', trend: '+8%' },
        { label: 'New Features', value: '42%', trend: '+12%' },
        { label: 'Bug Fixes', value: '18%', trend: '-3%' },
        { label: 'Documentation', value: '6%', trend: '+2%' }
      ]
    },
    {
      category: 'Timeline',
      icon: <Clock className="h-5 w-5" />,
      color: '#14b8a6',
      items: [
        { label: 'Morning', value: '32%', trend: 'stable' },
        { label: 'Afternoon', value: '48%', trend: '+5%' },
        { label: 'Evening', value: '18%', trend: '-2%' },
        { label: 'Night', value: '2%', trend: '-1%' }
      ]
    }
  ]

  const getTrendColor = (trend: string) => {
    if (trend.startsWith('+')) return '#10b981'
    if (trend.startsWith('-')) return '#ef4444'
    return 'var(--color-text-secondary)'
  }

  const getTrendBg = (trend: string) => {
    if (trend.startsWith('+')) return '#10b98115'
    if (trend.startsWith('-')) return '#ef444415'
    return 'var(--color-surface)'
  }

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <BarChart3 className="h-8 w-8" style={{ color: 'var(--color-primary)' }} />
          <h1 className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            Grid View
          </h1>
        </div>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Organized data grid with comprehensive metrics and trends
        </p>
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {gridData.map((section, idx) => (
          <div
            key={idx}
            className="rounded-2xl p-6 border shadow-lg transition-all duration-300 hover:shadow-xl"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            {/* Section Header */}
            <div className="flex items-center gap-3 mb-5 pb-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
              <div
                className="p-2 rounded-lg"
                style={{ backgroundColor: `${section.color}15`, color: section.color }}
              >
                {section.icon}
              </div>
              <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {section.category}
              </h3>
            </div>

            {/* Items */}
            <div className="space-y-3">
              {section.items.map((item, itemIdx) => (
                <div
                  key={itemIdx}
                  className="flex items-center justify-between p-3 rounded-lg transition-all hover:scale-[1.02]"
                  style={{ backgroundColor: 'var(--color-background)' }}
                >
                  <div className="flex-1">
                    <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                      {item.label}
                    </p>
                    <p className="text-base font-bold" style={{ color: 'var(--color-text-primary)' }}>
                      {item.value}
                    </p>
                  </div>
                  <div
                    className="px-2 py-1 rounded-md text-xs font-semibold"
                    style={{
                      color: getTrendColor(item.trend),
                      backgroundColor: getTrendBg(item.trend)
                    }}
                  >
                    {item.trend}
                  </div>
                </div>
              ))}
            </div>

            {/* Visual Indicator Bar */}
            <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-background)' }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      backgroundColor: section.color,
                      width: `${Math.random() * 40 + 60}%`
                    }}
                  />
                </div>
                <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  Active
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Footer */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          className="rounded-xl p-6 border text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center justify-center gap-2 mb-2">
            <TrendingUp className="h-5 w-5" style={{ color: '#10b981' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Overall Trend
            </p>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#10b981' }}>
            +12.4%
          </p>
        </div>
        <div
          className="rounded-xl p-6 border text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center justify-center gap-2 mb-2">
            <Folder className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Active Projects
            </p>
          </div>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            7
          </p>
        </div>
        <div
          className="rounded-xl p-6 border text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center justify-center gap-2 mb-2">
            <Calendar className="h-5 w-5" style={{ color: 'var(--color-accent)' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Days Active
            </p>
          </div>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            24/30
          </p>
        </div>
      </div>
    </div>
  )
}
