import { Activity, FileText, GitCommit, Zap, Clock, Target, Lightbulb, Info, AlertCircle, Eye } from 'lucide-react'
import { useState } from 'react'

export default function FocusLayout() {
  const [currentFocus, setCurrentFocus] = useState(0)

  const focusAreas = [
    {
      id: 0,
      title: 'Activity Score',
      value: '87%',
      subtitle: 'out of 100',
      description: 'Overall activity score detected by the agent based on patterns, consistency, and change intensity.',
      longDescription: 'The Activity Score is a composite metric that measures your overall development productivity and engagement. It combines multiple factors including how frequently you make changes, how consistent your work patterns are, and the intensity of modifications. A higher score indicates sustained, consistent development activity.',
      icon: <Target className="h-16 w-16" />,
      color: 'var(--color-primary)',
      details: [
        { label: 'High Intensity', value: '72%', description: 'Percentage of changes that are substantial modifications' },
        { label: 'Active Duration', value: '6h', description: 'Total time spent in active development sessions' },
        { label: 'Consistency', value: '85%', description: 'How regular and predictable your activity patterns are' }
      ],
      insights: [
        'Your activity is highly consistent, suggesting strong project engagement',
        'Peak activity occurs during core hours, enabling better collaboration',
        'Consider maintaining this momentum for optimal project velocity'
      ],
      chart: { labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], values: [82, 85, 79, 91, 87] }
    },
    {
      id: 1,
      title: 'Peak Activity Window',
      value: '3 PM',
      subtitle: 'most productive hour',
      description: 'Agent detected peak activity hour with highest change volume and intensity.',
      longDescription: 'Understanding your peak activity window helps identify your most productive period. This is when you typically make the most substantial changes, commit code most frequently, and show the highest level of engagement. Scheduling important work during this window can maximize your effectiveness.',
      icon: <Zap className="h-16 w-16" />,
      color: 'var(--color-accent)',
      details: [
        { label: 'Changes/Hour', value: '145', description: 'Average number of file changes during peak hours' },
        { label: 'Files Modified', value: '12', description: 'Distinct files typically changed during peak window' },
        { label: 'Commits/Window', value: '8', description: 'Average number of commits in the peak activity hour' }
      ],
      insights: [
        'Your productivity peaks in early afternoon—protect this time for deep work',
        '3x more changes happen during peak hours compared to off-peak times',
        'Consider scheduling meetings outside your peak window to preserve coding time'
      ],
      chart: { labels: ['9 AM', '12 PM', '3 PM', '6 PM', '9 PM'], values: [32, 28, 45, 38, 15] }
    },
    {
      id: 2,
      title: 'Activity Overview',
      value: '1,284',
      subtitle: 'total changes',
      description: 'Comprehensive view of detected activity including file modifications, commits, and code changes.',
      longDescription: 'This comprehensive view aggregates all tracked changes across your codebase. It includes every file modification, commit, and code change detected by the agent. Use this metric to understand the scale of your project work and track productivity trends over time.',
      icon: <Activity className="h-16 w-16" />,
      color: 'var(--color-primary)',
      details: [
        { label: 'Files Modified', value: '47', description: 'Unique files that have been changed in tracked period' },
        { label: 'Commits', value: '23', description: 'Total commits made across all branches' },
        { label: 'Lines Changed', value: '8.2k', description: 'Total lines added, modified, or removed' }
      ],
      insights: [
        'Average of 55 changes per file indicates focused, iterative development',
        'Your commit frequency suggests regular, manageable code reviews',
        'High line-change count reflects substantial feature work or refactoring'
      ],
      chart: { labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'], values: [45, 62, 38, 71] }
    }
  ]

  const current = focusAreas[currentFocus]
  const maxChart = Math.max(...current.chart.values)

  return (
    <div className="min-h-screen p-6 md:p-12" style={{ backgroundColor: 'var(--color-background)' }}>
      <div className="max-w-5xl mx-auto">
        {/* Header Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            <Eye className="inline mr-3 h-10 w-10" style={{ color: 'var(--color-primary)' }} />
            Focus View
          </h1>
          <p className="text-lg mb-4" style={{ color: 'var(--color-text-secondary)' }}>
            One insight at a time for maximum clarity and understanding
          </p>
          
          {/* Concept Explanation */}
          <div className="bg-gradient-to-r rounded-lg p-6 mb-8" style={{ 
            backgroundColor: 'var(--color-surface)',
            borderLeft: '4px solid var(--color-primary)'
          }}>
            <div className="flex items-start gap-3">
              <Lightbulb className="h-5 w-5 mt-1 flex-shrink-0" style={{ color: 'var(--color-primary)' }} />
              <div className="text-left">
                <h3 className="font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                  What is the Focus View?
                </h3>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                  The Focus View breaks down your development activity into three key dimensions: your overall productivity level (Activity Score), 
                  your most productive time window (Peak Activity), and a comprehensive overview of all changes. 
                  Each view is designed to help you understand your work patterns and optimize your workflow.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Dots with Labels */}
        <div className="mb-12">
          <div className="flex justify-center gap-2 mb-4 flex-wrap">
            {focusAreas.map((area, index) => (
              <button
                key={area.id}
                onClick={() => setCurrentFocus(index)}
                className={`px-4 py-2 rounded-full transition-all font-medium text-sm ${
                  currentFocus === index 
                    ? 'text-white shadow-lg' 
                    : 'border'
                }`}
                style={{
                  backgroundColor: currentFocus === index ? current.color : 'transparent',
                  borderColor: currentFocus === index ? 'transparent' : 'var(--color-border)',
                  color: currentFocus === index ? 'white' : 'var(--color-text-primary)'
                }}
                aria-label={`View ${area.title}`}
              >
                {area.title}
              </button>
            ))}
          </div>
        </div>

        {/* Main Focus Card */}
        <div
          className="rounded-3xl p-8 md:p-12 mb-8 shadow-2xl transition-all duration-500 w-full"
          style={(
            {
              // local CSS variables so we can use the theme vars directly inside the gradient
              ['--focus-start']: current.color,
              ['--focus-end']: 'var(--color-overlay)',
              background: 'linear-gradient(135deg, var(--focus-start) 0%, var(--focus-start) 80%, color-mix(in srgb, var(--focus-start) 60%, black) 100%)',
              minHeight: 'auto',
              display: 'flex',
              flexDirection: 'column',
              color: 'var(--color-text-inverse)'
            } as React.CSSProperties
          )}
        >
          <div className="flex flex-col items-center text-center mb-8">
            <div className="mb-6 opacity-90">{current.icon}</div>
            <h2 className="text-3xl md:text-4xl font-bold mb-2">{current.title}</h2>
            <div className="text-6xl md:text-7xl font-bold mb-2">{current.value}</div>
            <p className="text-lg opacity-90 mb-6">{current.subtitle}</p>
            <div className="h-px bg-white/30 w-12 mb-6"></div>
          </div>

          <p className="text-center text-base md:text-lg mb-8 opacity-95 max-w-3xl mx-auto leading-relaxed">
            {current.description}
          </p>

          {/* Extended Description */}
          <div className="bg-white/15 backdrop-blur-sm rounded-2xl p-6 mb-8">
            <p className="text-center text-sm md:text-base leading-relaxed whitespace-normal">
              {current.longDescription}
            </p>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {current.details.map((detail, i) => (
              <div
                key={i}
                className="rounded-xl p-6 backdrop-blur-sm hover:bg-white/20 transition-colors"
                style={{ backgroundColor: 'rgba(255,255,255,0.15)' }}
              >
                <div className="text-sm font-semibold mb-2 opacity-90">{detail.label}</div>
                <div className="text-3xl font-bold mb-3">{detail.value}</div>
                <p className="text-xs opacity-85 leading-relaxed whitespace-normal">{detail.description}</p>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="mt-8 mb-8">
            <h3 className="text-center text-lg font-semibold mb-4 opacity-90">Trend Analysis</h3>
            <div className="flex items-end justify-center gap-3 h-40">
              {current.chart.values.map((value, i) => (
                <div key={i} className="flex flex-col items-center flex-1 max-w-[80px]">
                  <div
                    className="w-full rounded-t transition-all hover:opacity-80"
                    style={{
                      height: `${(value / maxChart) * 100}%`,
                      backgroundColor: 'rgba(255,255,255,0.9)',
                      minHeight: '8px'
                    }}
                    title={`${current.chart.labels[i]}: ${value}`}
                  />
                  <span className="text-xs mt-2 opacity-75">{current.chart.labels[i]}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Key Insights */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6">
            <h3 className="font-semibold mb-4 text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Key Insights
            </h3>
            <ul className="space-y-3">
              {current.insights.map((insight, i) => (
                <li key={i} className="flex gap-3 text-sm opacity-95">
                  <span className="text-yellow-200 font-bold flex-shrink-0">•</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Footer Information */}
        <div className="bg-gradient-to-r rounded-lg p-6 mb-8" style={{
          backgroundColor: 'var(--color-surface)',
          borderTop: '2px solid var(--color-primary)'
        }}>
          <h3 className="font-semibold mb-3 text-lg flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
            <Info className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            How to Use This Insight
          </h3>
          <ul className="space-y-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            <li>• Compare your current metrics with previous periods to identify trends</li>
            <li>• Use the peak activity window to schedule deep work and important tasks</li>
            <li>• Monitor consistency to ensure sustainable work patterns</li>
            <li>• Navigate between views to get a complete picture of your development activity</li>
          </ul>
        </div>

        {/* Quick Reference Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Changes', value: '1,284', icon: <Activity className="h-5 w-5" />, desc: 'All tracked modifications' },
            { label: 'Files Affected', value: '47', icon: <FileText className="h-5 w-5" />, desc: 'Unique files modified' },
            { label: 'Commits', value: '23', icon: <GitCommit className="h-5 w-5" />, desc: 'Code commits' },
            { label: 'Peak Hour', value: '3 PM', icon: <Clock className="h-5 w-5" />, desc: 'Most productive' }
          ].map((stat, i) => (
            <div
              key={i}
              className="rounded-xl p-4 border group hover:shadow-lg transition-all cursor-help"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)'
              }}
              title={stat.desc}
            >
              <div className="flex justify-center mb-2 group-hover:scale-110 transition-transform" style={{ color: 'var(--color-primary)' }}>
                {stat.icon}
              </div>
              <div className="text-xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
                {stat.value}
              </div>
              <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

