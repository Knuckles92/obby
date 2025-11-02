import { Clock, Coffee, Zap, TrendingUp, Award, FileText, CheckCircle } from 'lucide-react'

interface TimelineEvent {
  time: string
  title: string
  description: string
  type: 'milestone' | 'peak' | 'activity' | 'break'
  metrics?: {
    duration?: string
    files?: number
    tests?: number
  }
}

export default function TimelineLayout() {
  const morningEvents: TimelineEvent[] = [
    {
      time: '8:15 AM',
      title: 'Activity Detected',
      description: 'Initial file changes detected across project configuration',
      type: 'activity',
      metrics: { duration: '45 min', files: 3 }
    },
    {
      time: '9:30 AM',
      title: 'Major Changes Detected',
      description: 'Agent noticed significant additions to dashboard components',
      type: 'milestone',
      metrics: { files: 12, tests: 8 }
    },
    {
      time: '11:00 AM',
      title: 'Peak Activity Detected',
      description: 'Highest change volume and intensity observed',
      type: 'peak'
    }
  ]

  const afternoonEvents: TimelineEvent[] = [
    {
      time: '1:00 PM',
      title: 'Low Activity Period',
      description: 'Minimal file changes detected during this window',
      type: 'break',
      metrics: { duration: '30 min' }
    },
    {
      time: '2:15 PM',
      title: 'Review Activity Detected',
      description: 'Agent observed extensive file review patterns across 6 branches',
      type: 'activity',
      metrics: { files: 24 }
    },
    {
      time: '3:45 PM',
      title: 'Bug Fix Pattern Identified',
      description: 'Detected fixes and corrections across 8 related modules',
      type: 'milestone',
      metrics: { files: 15, tests: 12 }
    }
  ]

  const eveningEvents: TimelineEvent[] = [
    {
      time: '6:00 PM',
      title: 'Documentation Updates',
      description: 'Agent detected changes to README and API documentation',
      type: 'activity',
      metrics: { files: 4 }
    },
    {
      time: '7:30 PM',
      title: 'Session Complete',
      description: 'Agent compiled activity summary and detected session end',
      type: 'milestone'
    }
  ]

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'milestone': return <Award className="h-5 w-5" />
      case 'peak': return <Zap className="h-5 w-5" />
      case 'activity': return <FileText className="h-5 w-5" />
      case 'break': return <Coffee className="h-5 w-5" />
      default: return <CheckCircle className="h-5 w-5" />
    }
  }

  const getEventColor = (type: string) => {
    switch (type) {
      case 'milestone': return 'var(--color-success)'
      case 'peak': return 'var(--color-warning)'
      case 'activity': return 'var(--color-info)'
      case 'break': return 'var(--color-accent)'
      default: return 'var(--color-primary)'
    }
  }

  const renderEvents = (events: TimelineEvent[]) => (
    <div className="space-y-6">
      {events.map((event, index) => (
        <div key={index} className="relative pl-8 group">
          {/* Timeline dot and line */}
          <div className="absolute left-0 top-2">
            <div
              className="w-4 h-4 rounded-full border-4 transition-all duration-300 group-hover:scale-125"
              style={{
                backgroundColor: getEventColor(event.type),
                borderColor: 'var(--color-background)'
              }}
            ></div>
            {index < events.length - 1 && (
              <div
                className="absolute left-1/2 top-full h-12 w-px -translate-x-1/2"
                style={{ backgroundColor: 'var(--color-border)' }}
              ></div>
            )}
          </div>

          {/* Event card */}
          <div
            className="rounded-lg p-4 shadow-sm border transition-all duration-300 hover:shadow-md hover:scale-105"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)',
              borderLeft: `4px solid ${getEventColor(event.type)}`
            }}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <div style={{ color: getEventColor(event.type) }}>
                  {getEventIcon(event.type)}
                </div>
                <h4 className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                  {event.title}
                </h4>
              </div>
              <span className="text-xs px-2 py-1 rounded" style={{
                backgroundColor: 'var(--color-divider)',
                color: 'var(--color-text-secondary)'
              }}>
                {event.time}
              </span>
            </div>
            <p className="text-sm mb-3" style={{ color: 'var(--color-text-secondary)' }}>
              {event.description}
            </p>
            {event.metrics && (
              <div className="flex gap-4 text-xs">
                {event.metrics.duration && (
                  <span style={{ color: 'var(--color-text-secondary)' }}>
                    <Clock className="inline h-3 w-3 mr-1" />
                    {event.metrics.duration}
                  </span>
                )}
                {event.metrics.files && (
                  <span style={{ color: 'var(--color-text-secondary)' }}>
                    <FileText className="inline h-3 w-3 mr-1" />
                    {event.metrics.files} files
                  </span>
                )}
                {event.metrics.tests && (
                  <span style={{ color: 'var(--color-text-secondary)' }}>
                    <CheckCircle className="inline h-3 w-3 mr-1" />
                    {event.metrics.tests} tests
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
      }}>
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Activity Timeline</h1>
          <p className="text-blue-100">Agent-tracked patterns throughout the day</p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Active Time', value: '9.2 hrs', icon: <Clock className="h-5 w-5" /> },
          { label: 'High Activity Periods', value: '3', icon: <Zap className="h-5 w-5" /> },
          { label: 'Notable Events', value: '4', icon: <Award className="h-5 w-5" /> },
          { label: 'Activity Score', value: '94%', icon: <TrendingUp className="h-5 w-5" /> }
        ].map((metric, i) => (
          <div key={i} className="rounded-lg p-4 shadow border" style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}>
            <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--color-primary)' }}>
              {metric.icon}
              <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{metric.label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>{metric.value}</p>
          </div>
        ))}
      </div>

      {/* Timeline Sections */}
      <div className="space-y-12">
        {/* Morning */}
        <div>
          <div className="mb-6 pb-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
              Morning Activity (8:00 - 12:00)
            </h2>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              High change volume detected during this period
            </p>
          </div>
          {renderEvents(morningEvents)}
        </div>

        {/* Afternoon */}
        <div>
          <div className="mb-6 pb-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
              Afternoon Activity (1:00 - 5:00)
            </h2>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Review patterns and bug fixes observed
            </p>
          </div>
          {renderEvents(afternoonEvents)}
        </div>

        {/* Evening */}
        <div>
          <div className="mb-6 pb-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
              Evening Activity (6:00 - 9:00)
            </h2>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Documentation updates and session completion
            </p>
          </div>
          {renderEvents(eveningEvents)}
        </div>
      </div>

      {/* Summary */}
      <div className="mt-12 rounded-lg p-6 shadow border" style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)'
      }}>
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
          Daily Summary
        </h3>
        <p className="mb-4" style={{ color: 'var(--color-text-secondary)' }}>
          Agent detected high activity throughout the day with 4 notable events. Peak activity occurred during the late morning session, with 9.2 hours of total active time tracked. Three distinct high-intensity periods were identified, with maximum change volume between 11 AM and 2 PM.
        </p>
        <div className="flex flex-wrap gap-2">
          {['Intensive Changes', 'Bug Fixes', 'Code Reviews', 'Documentation'].map((tag, i) => (
            <span key={i} className="px-3 py-1 rounded-full text-xs" style={{
              backgroundColor: 'var(--color-primary)',
              color: 'var(--color-text-inverse)'
            }}>
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
