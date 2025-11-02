import { Activity, TrendingUp, Clock, Zap } from 'lucide-react'

interface MetricCard {
  title: string
  value: string | number
  label: string
  icon: React.ReactNode
}

export default function MinimalistLayout() {
  // Mock data for minimalist layout
  const metrics: MetricCard[] = [
    {
      title: 'Code Activity Score',
      value: '87',
      label: 'out of 100',
      icon: <Activity className="h-12 w-12" />
    },
    {
      title: 'Development Rhythm',
      value: '9.2 hrs',
      label: 'active hours detected',
      icon: <TrendingUp className="h-12 w-12" />
    },
    {
      title: 'Active Sessions',
      value: '6',
      label: 'coding sessions',
      icon: <Clock className="h-12 w-12" />
    },
    {
      title: 'Code Intensity',
      value: '72%',
      label: 'high-activity periods',
      icon: <Zap className="h-12 w-12" />
    }
  ]

  const activityData = [
    { hour: '6 AM', value: 5, percentage: 10 },
    { hour: '9 AM', value: 32, percentage: 65 },
    { hour: '12 PM', value: 28, percentage: 55 },
    { hour: '3 PM', value: 45, percentage: 92 },
    { hour: '6 PM', value: 38, percentage: 78 },
    { hour: '9 PM', value: 15, percentage: 30 },
    { hour: '12 AM', value: 3, percentage: 6 }
  ]

  return (
    <div className="min-h-screen p-8 md:p-12" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Minimalist Header */}
      <div className="max-w-6xl mx-auto mb-20">
        <h1 className="text-5xl md:text-6xl font-light tracking-tight mb-4" style={{ color: 'var(--color-text-primary)' }}>
          Agent Discoveries
        </h1>
        <div className="w-16 h-1 rounded-full" style={{ backgroundColor: 'var(--color-primary)' }}></div>
        <p className="text-lg mt-6" style={{ color: 'var(--color-text-secondary)' }}>
          Patterns detected in your codebase
        </p>
      </div>

      {/* Key Metrics Grid - 4 Cards Only */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-24">
        {metrics.map((metric, index) => (
          <div
            key={index}
            className="group relative transition-all duration-500 hover:transform hover:scale-105"
            style={{
              animation: `fadeInUp 0.6s ease-out ${index * 0.1}s both`
            }}
          >
            {/* Subtle background circle */}
            <div
              className="absolute -inset-8 rounded-full opacity-0 group-hover:opacity-10 transition-opacity duration-300"
              style={{ backgroundColor: 'var(--color-primary)' }}
            ></div>

            <div className="relative text-center space-y-6">
              {/* Icon with subtle animation */}
              <div className="flex justify-center">
                <div
                  className="transition-transform duration-500 group-hover:rotate-6"
                  style={{ color: 'var(--color-primary)' }}
                >
                  {metric.icon}
                </div>
              </div>

              {/* Large Value */}
              <div>
                <p className="text-5xl md:text-6xl font-light tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
                  {metric.value}
                </p>
                <p className="text-xs tracking-widest uppercase mt-2" style={{ color: 'var(--color-text-secondary)', letterSpacing: '0.1em' }}>
                  {metric.label}
                </p>
              </div>

              {/* Metric title */}
              <p className="text-sm font-light" style={{ color: 'var(--color-text-secondary)' }}>
                {metric.title}
              </p>

              {/* Subtle divider on hover */}
              <div
                className="absolute bottom-0 left-1/2 transform -translate-x-1/2 h-px w-0 group-hover:w-full transition-all duration-300"
                style={{ backgroundColor: 'var(--color-primary)', opacity: 0.2 }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {/* Activity Rhythm Visualization */}
      <div className="max-w-6xl mx-auto mb-24">
        <div className="mb-12">
          <h2 className="text-3xl font-light tracking-tight mb-2" style={{ color: 'var(--color-text-primary)' }}>
            Hourly Activity Pattern
          </h2>
          <div className="w-12 h-px" style={{ backgroundColor: 'var(--color-primary)', opacity: 0.3 }}></div>
        </div>

        {/* Minimal bar chart */}
        <div className="flex items-end justify-between gap-3 h-40 p-8 rounded-lg" style={{ backgroundColor: 'var(--color-surface)' }}>
          {activityData.map((data, index) => (
            <div key={index} className="flex flex-col items-center flex-1 group">
              <div
                className="w-full rounded-t-lg transition-all duration-300 hover:shadow-lg"
                style={{
                  height: `${data.percentage * 1.2}px`,
                  backgroundColor: 'var(--color-primary)',
                  opacity: 0.8
                }}
              />
              <p className="text-xs mt-3 font-light" style={{ color: 'var(--color-text-secondary)' }}>
                {data.hour}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Breathing Statement */}
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="space-y-6">
          <p className="text-2xl font-light leading-relaxed" style={{ color: 'var(--color-text-primary)' }}>
            Consistent coding patterns detected
          </p>
          <p className="text-base font-light" style={{ color: 'var(--color-text-secondary)' }}>
            Peak activity occurs between 2–4 PM. The agent noticed sustained high-intensity work during these hours.
          </p>
          <div className="flex justify-center gap-4 pt-4">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--color-primary)', animation: 'pulse 2s ease-in-out infinite' }}></div>
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--color-primary)', animation: 'pulse 2s ease-in-out infinite 0.3s' }}></div>
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--color-primary)', animation: 'pulse 2s ease-in-out infinite 0.6s' }}></div>
          </div>
        </div>
      </div>

      {/* Subtle Geometric Accent */}
      <div className="max-w-6xl mx-auto mt-24">
        <div className="relative rounded-lg overflow-hidden p-12" style={{ backgroundColor: 'var(--color-surface)' }}>
          <div className="absolute top-0 right-0 w-40 h-40 rounded-full opacity-5 -mr-20 -mt-20" style={{ backgroundColor: 'var(--color-primary)' }}></div>
          <div className="absolute bottom-0 left-0 w-32 h-32 rounded-full opacity-5 -ml-16 -mb-16" style={{ backgroundColor: 'var(--color-primary)' }}></div>

          <div className="relative space-y-4">
            <h3 className="text-xl font-light" style={{ color: 'var(--color-text-primary)' }}>Key Observations</h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-4">
                <span className="inline-block w-2 h-2 rounded-full mt-2" style={{ backgroundColor: 'var(--color-primary)' }}></span>
                <span className="text-sm font-light" style={{ color: 'var(--color-text-secondary)' }}>72% of code activity occurs during afternoon sessions</span>
              </li>
              <li className="flex items-start gap-4">
                <span className="inline-block w-2 h-2 rounded-full mt-2" style={{ backgroundColor: 'var(--color-primary)' }}></span>
                <span className="text-sm font-light" style={{ color: 'var(--color-text-secondary)' }}>Agent detected a 6-hour continuous coding block pattern</span>
              </li>
              <li className="flex items-start gap-4">
                <span className="inline-block w-2 h-2 rounded-full mt-2" style={{ backgroundColor: 'var(--color-primary)' }}></span>
                <span className="text-sm font-light" style={{ color: 'var(--color-text-secondary)' }}>Code activity score consistently above 85 this week</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  )
}
