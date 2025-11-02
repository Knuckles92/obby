import { Activity, FileText, GitCommit, Code, TrendingUp, Zap, BarChart3, Target, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function MasonryLayout() {
  const cards = [
    {
      id: 1,
      title: 'Peak Activity',
      value: '3 PM',
      description: 'Highest activity detected',
      icon: <Zap className="h-5 w-5" />,
      color: '#667eea',
      stats: [{ label: 'Changes', value: '145' }, { label: 'Files', value: '12' }]
    },
    {
      id: 2,
      title: 'Total Changes',
      value: '1,284',
      description: 'This week',
      icon: <Activity className="h-5 w-5" />,
      color: '#f5576c',
      trend: '+12%'
    },
    {
      id: 3,
      title: 'Activity Score',
      value: '87%',
      description: 'Based on detected patterns',
      icon: <Target className="h-5 w-5" />,
      color: '#00f2fe',
      stats: [{ label: 'Intensive', value: '72%' }, { label: 'Duration', value: '6h' }]
    },
    {
      id: 4,
      title: 'Files Modified',
      value: '47',
      description: 'Active files',
      icon: <FileText className="h-5 w-5" />,
      color: '#38f9d7',
      trend: '+15%'
    },
    {
      id: 5,
      title: 'Commits',
      value: '23',
      description: 'This week',
      icon: <GitCommit className="h-5 w-5" />,
      color: '#30cfd0',
      stats: [{ label: 'Avg Size', value: '324' }, { label: 'Largest', value: '892' }]
    },
    {
      id: 6,
      title: 'Trending Up',
      value: '+12%',
      description: 'vs last week',
      icon: <TrendingUp className="h-5 w-5" />,
      color: '#a8edea',
      trend: '+12%'
    },
    {
      id: 7,
      title: 'Languages',
      value: '4',
      description: 'Active languages',
      icon: <Code className="h-5 w-5" />,
      color: '#ff9a9e',
      stats: [{ label: 'TypeScript', value: '45%' }, { label: 'CSS', value: '25%' }]
    },
    {
      id: 8,
      title: 'Lines Added',
      value: '4,823',
      description: 'Code changes',
      icon: <BarChart3 className="h-5 w-5" />,
      color: '#fa709a',
      trend: '+18%'
    }
  ]

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
          Insights Overview
        </h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Clean, organized view of your development metrics
        </p>
      </div>

      {/* KPI Cards - Organized Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <div
            key={card.id}
            className="rounded-xl p-5 shadow-md hover:shadow-lg transition-all duration-300 border"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            {/* Header with icon and color indicator */}
            <div className="flex items-start justify-between mb-4">
              <div
                className="p-2 rounded-lg"
                style={{
                  backgroundColor: card.color + '20',
                  color: card.color
                }}
              >
                {card.icon}
              </div>
              {card.trend && (
                <div className={`flex items-center gap-1 text-xs font-semibold ${
                  card.trend.startsWith('+') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {card.trend.startsWith('+') ? (
                    <ArrowUpRight className="h-3 w-3" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3" />
                  )}
                  {card.trend}
                </div>
              )}
            </div>

            {/* Content */}
            <div className="mb-4">
              <p className="text-sm mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                {card.title}
              </p>
              <p className="text-2xl font-bold" style={{ color: card.color }}>
                {card.value}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                {card.description}
              </p>
            </div>

            {/* Stats if present */}
            {card.stats && (
              <div className="pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
                <div className="grid grid-cols-2 gap-3">
                  {card.stats.map((stat, i) => (
                    <div key={i}>
                      <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                        {stat.label}
                      </p>
                      <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                        {stat.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary Section */}
      <div className="rounded-xl p-6 shadow-md border" style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)'
      }}>
        <h2 className="text-lg font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>
          Weekly Summary
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-background)' }}>
            <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
              Total Activity
            </p>
            <p className="text-2xl font-bold" style={{ color: 'var(--color-primary)' }}>
              2,168 hrs
            </p>
            <p className="text-xs mt-2" style={{ color: 'var(--color-text-secondary)' }}>
              Development time tracked
            </p>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-background)' }}>
            <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
              Code Quality
            </p>
            <p className="text-2xl font-bold text-green-600">
              94%
            </p>
            <p className="text-xs mt-2" style={{ color: 'var(--color-text-secondary)' }}>
              Test coverage & lint checks
            </p>
          </div>
          <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--color-background)' }}>
            <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
              Performance
            </p>
            <p className="text-2xl font-bold text-blue-600">
              2.3s
            </p>
            <p className="text-xs mt-2" style={{ color: 'var(--color-text-secondary)' }}>
              Avg build time
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

