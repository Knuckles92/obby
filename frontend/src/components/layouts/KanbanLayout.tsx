import { Activity, FileText, GitCommit, Code, TrendingUp, Zap, BarChart3, Clock, CheckCircle2, Circle, ArrowRight, Sparkles } from 'lucide-react'

export default function KanbanLayout() {
  const columns = [
    {
      id: 'today',
      title: 'Today',
      color: '#3b82f6',
      items: [
        { id: 1, title: 'Dashboard Updates', value: '45 changes', files: 3, priority: 'high' },
        { id: 2, title: 'API Refactoring', value: '32 changes', files: 2, priority: 'medium' },
        { id: 3, title: 'Theme Improvements', value: '24 changes', files: 1, priority: 'low' }
      ]
    },
    {
      id: 'this-week',
      title: 'This Week',
      color: '#8b5cf6',
      items: [
        { id: 4, title: 'New Features', value: '128 changes', files: 5, priority: 'high' },
        { id: 5, title: 'Bug Fixes', value: '67 changes', files: 4, priority: 'medium' },
        { id: 6, title: 'Documentation', value: '42 changes', files: 2, priority: 'low' }
      ]
    },
    {
      id: 'insights',
      title: 'Insights',
      color: '#ec4899',
      items: [
        { id: 7, title: 'Peak Hours', value: '3 PM', files: null, priority: 'info' },
        { id: 8, title: 'Total Changes', value: '1,284', files: null, priority: 'info' },
        { id: 9, title: 'Activity Score', value: '87%', files: null, priority: 'info' }
      ]
    },
    {
      id: 'stats',
      title: 'Stats',
      color: '#f59e0b',
      items: [
        { id: 10, title: 'Files Modified', value: '47', files: null, priority: 'stat' },
        { id: 11, title: 'Commits', value: '23', files: null, priority: 'stat' },
        { id: 12, title: 'Languages', value: '4', files: null, priority: 'stat' }
      ]
    }
  ]

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#ef4444'
      case 'medium': return '#f59e0b'
      case 'low': return '#10b981'
      case 'info': return '#3b82f6'
      case 'stat': return '#8b5cf6'
      default: return '#6b7280'
    }
  }

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
          Categorized Findings
        </h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Insights organized by timeframe and category
        </p>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map((column) => (
          <div
            key={column.id}
            className="flex-shrink-0 w-72 rounded-xl border"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            {/* Column Header */}
            <div
              className="p-4 rounded-t-xl flex items-center justify-between"
              style={{
                backgroundColor: `${column.color}15`,
                borderBottom: `2px solid ${column.color}`
              }}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: column.color }}
                />
                <h2 className="font-bold" style={{ color: 'var(--color-text-primary)' }}>
                  {column.title}
                </h2>
              </div>
              <span
                className="text-xs font-medium px-2 py-1 rounded"
                style={{
                  backgroundColor: `${column.color}20`,
                  color: column.color
                }}
              >
                {column.items.length}
              </span>
            </div>

            {/* Column Items */}
            <div className="p-4 space-y-3 min-h-[400px]">
              {column.items.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg p-4 border cursor-pointer hover:shadow-md transition-all"
                  style={{
                    backgroundColor: 'var(--color-background)',
                    borderColor: 'var(--color-border)'
                  }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
                      {item.title}
                    </h3>
                    {item.priority && item.priority !== 'info' && item.priority !== 'stat' && (
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0 mt-1"
                        style={{ backgroundColor: getPriorityColor(item.priority) }}
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                    <span className="font-medium">{item.value}</span>
                    {item.files && (
                      <>
                        <span>•</span>
                        <span>{item.files} files</span>
                      </>
                    )}
                  </div>
                  {item.priority === 'info' || item.priority === 'stat' ? (
                    <div className="flex items-center gap-1 text-xs" style={{ color: column.color }}>
                      <Sparkles className="h-3 w-3" />
                      <span>Insight</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.random() * 40 + 60}%`,
                            backgroundColor: getPriorityColor(item.priority)
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Summary Row */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Changes', value: '1,284', icon: <Activity className="h-4 w-4" /> },
          { label: 'Files Modified', value: '47', icon: <FileText className="h-4 w-4" /> },
          { label: 'Commits', value: '23', icon: <GitCommit className="h-4 w-4" /> },
          { label: 'Peak Hour', value: '3 PM', icon: <Clock className="h-4 w-4" /> }
        ].map((stat, i) => (
          <div
            key={i}
            className="rounded-lg p-4 border flex items-center gap-3"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <div style={{ color: 'var(--color-primary)' }}>{stat.icon}</div>
            <div>
              <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                {stat.label}
              </div>
              <div className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {stat.value}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

