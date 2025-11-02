import React, { useState } from 'react'
import { TrendingUp, Zap, Coffee, Flame, Moon, Trophy } from 'lucide-react'

interface TimelineEvent {
  id: string
  time: string
  title: string
  description: string
  category: 'milestone' | 'peak' | 'activity' | 'break'
  duration?: string
  metrics?: {
    label: string
    value: string
  }[]
  isPeak?: boolean
}

interface TimelineSection {
  period: string
  startTime: string
  endTime: string
  events: TimelineEvent[]
  summary: string
  keyAchievement?: string
}

const mockTimelineData: TimelineSection[] = [
  {
    period: 'Morning Session',
    startTime: '8:00 AM',
    endTime: '12:00 PM',
    summary: 'Focused deep work on project initialization. High energy startup period.',
    keyAchievement: '3 files created, 250 lines of code',
    events: [
      {
        id: '1',
        time: '8:15 AM',
        title: 'Project Started',
        description: 'Initialized new project repository and set up development environment',
        category: 'milestone',
        duration: '45 min',
        metrics: [{ label: 'Setup Time', value: '45 min' }]
      },
      {
        id: '2',
        time: '9:30 AM',
        title: 'Peak Productivity',
        description: 'Intensive coding session with 3 major components completed',
        category: 'peak',
        isPeak: true,
        duration: '2.5 hours',
        metrics: [
          { label: 'Files Modified', value: '12' },
          { label: 'Lines Added', value: '250' }
        ]
      },
      {
        id: '3',
        time: '11:45 AM',
        title: 'Code Review Checkpoint',
        description: 'Self-review of morning work, identified 2 refactoring opportunities',
        category: 'activity',
        metrics: [{ label: 'Issues Found', value: '2' }]
      }
    ]
  },
  {
    period: 'Afternoon Focus',
    startTime: '1:00 PM',
    endTime: '5:00 PM',
    summary: 'Afternoon shift with sustained focus. Problem-solving and optimization work.',
    keyAchievement: 'Debugged critical issue, 8 commits',
    events: [
      {
        id: '4',
        time: '1:00 PM',
        title: 'Lunch Break',
        description: 'Recharged with a healthy lunch and 15-minute walk',
        category: 'break',
        duration: '1 hour',
        metrics: [{ label: 'Break Time', value: '1 hour' }]
      },
      {
        id: '5',
        time: '2:15 PM',
        title: 'Bug Investigation',
        description: 'Deep dive into critical bug affecting user authentication flow',
        category: 'activity',
        duration: '1.5 hours',
        metrics: [{ label: 'Bug Severity', value: 'Critical' }]
      },
      {
        id: '6',
        time: '4:00 PM',
        title: 'Peak Focus Period',
        description: 'Resolved critical issue and optimized database queries',
        category: 'peak',
        isPeak: true,
        duration: '1 hour',
        metrics: [
          { label: 'Performance Gain', value: '35%' },
          { label: 'Commits', value: '3' }
        ]
      },
      {
        id: '7',
        time: '4:45 PM',
        title: 'Documentation',
        description: 'Updated API documentation and added inline comments',
        category: 'activity',
        metrics: [{ label: 'Docs Added', value: '5' }]
      }
    ]
  },
  {
    period: 'Evening Review',
    startTime: '6:00 PM',
    endTime: '9:00 PM',
    summary: 'Final stretch with reflection and planning. Wrapping up with quality checks.',
    keyAchievement: 'All tests passing, 15 commits total',
    events: [
      {
        id: '8',
        time: '6:00 PM',
        title: 'Automated Tests',
        description: 'Ran full test suite - all 47 tests passing',
        category: 'milestone',
        metrics: [{ label: 'Tests Passing', value: '47/47' }]
      },
      {
        id: '9',
        time: '7:00 PM',
        title: 'Code Quality Check',
        description: 'Linting and code style verification completed',
        category: 'activity',
        metrics: [{ label: 'Style Issues', value: '0' }]
      },
      {
        id: '10',
        time: '8:15 PM',
        title: 'Daily Review',
        description: 'Reflection on accomplishments, updated project backlog for tomorrow',
        category: 'activity',
        duration: '45 min',
        metrics: [{ label: 'Tasks Completed', value: '8' }]
      },
      {
        id: '11',
        time: '9:00 PM',
        title: 'Day Complete',
        description: 'Ready for tomorrow with comprehensive progress summary',
        category: 'milestone',
        metrics: [{ label: 'Total Hours', value: '9.5' }]
      }
    ]
  }
]

const categoryIcons = {
  milestone: <Trophy className="w-5 h-5" />,
  peak: <Flame className="w-5 h-5" />,
  activity: <TrendingUp className="w-5 h-5" />,
  break: <Coffee className="w-5 h-5" />
}

const categoryColors = {
  milestone: {
    bg: 'var(--color-success)',
    text: 'var(--color-text-inverse)',
    border: 'var(--color-success)',
    light: 'rgba(5, 150, 105, 0.1)'
  },
  peak: {
    bg: 'var(--color-warning)',
    text: 'var(--color-text-inverse)',
    border: 'var(--color-warning)',
    light: 'rgba(217, 119, 6, 0.1)'
  },
  activity: {
    bg: 'var(--color-info)',
    text: 'var(--color-text-inverse)',
    border: 'var(--color-info)',
    light: 'rgba(2, 132, 199, 0.1)'
  },
  break: {
    bg: 'var(--color-accent)',
    text: 'var(--color-text-inverse)',
    border: 'var(--color-accent)',
    light: 'rgba(59, 130, 246, 0.1)'
  }
}

const TimelineEvent: React.FC<{
  event: TimelineEvent
  isLast: boolean
}> = ({ event, isLast }) => {
  const colors = categoryColors[event.category]

  return (
    <div className="relative flex gap-6 pb-8">
      {/* Timeline line */}
      {!isLast && (
        <div
          className="absolute left-6 top-12 w-1 h-12 -mb-8"
          style={{
            background: `linear-gradient(to bottom, ${colors.border}, ${colors.border}80)`,
            height: 'calc(100% + 2rem)'
          }}
        />
      )}

      {/* Timeline dot */}
      <div className="relative flex flex-col items-center pt-1">
        <div
          className="relative w-12 h-12 rounded-full flex items-center justify-center shadow-md border-2 transition-all duration-300 hover:scale-110"
          style={{
            backgroundColor: colors.bg,
            borderColor: colors.border,
            color: colors.text
          }}
        >
          {categoryIcons[event.category]}
        </div>
      </div>

      {/* Event card */}
      <div className="flex-1 pt-1">
        <div
          className="rounded-lg border-2 p-4 transition-all duration-300 hover:shadow-lg hover:scale-105"
          style={{
            backgroundColor: colors.light,
            borderColor: colors.border
          }}
        >
          {/* Time badge */}
          <div className="flex items-center justify-between mb-2">
            <span
              className="text-xs font-bold px-3 py-1 rounded-full"
              style={{
                backgroundColor: colors.bg,
                color: colors.text
              }}
            >
              {event.time}
            </span>
            {event.isPeak && (
              <span
                className="text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1"
                style={{
                  backgroundColor: 'var(--color-warning)',
                  color: 'var(--color-text-inverse)'
                }}
              >
                <Zap className="w-3 h-3" />
                Peak Moment
              </span>
            )}
          </div>

          {/* Title */}
          <h4
            className="text-lg font-bold mb-1"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {event.title}
          </h4>

          {/* Description */}
          <p
            className="text-sm mb-3 leading-relaxed"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            {event.description}
          </p>

          {/* Duration and metrics */}
          {(event.duration || event.metrics) && (
            <div className="flex flex-wrap gap-2">
              {event.duration && (
                <span
                  className="text-xs font-semibold px-2 py-1 rounded-md"
                  style={{
                    backgroundColor: colors.bg,
                    color: colors.text,
                    opacity: 0.8
                  }}
                >
                  ⏱ {event.duration}
                </span>
              )}
              {event.metrics?.map((metric, idx) => (
                <span
                  key={idx}
                  className="text-xs font-semibold px-2 py-1 rounded-md"
                  style={{
                    backgroundColor: colors.bg,
                    color: colors.text,
                    opacity: 0.8
                  }}
                >
                  {metric.label}: {metric.value}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const TimelineSection: React.FC<{
  section: TimelineSection
  index: number
}> = ({ section, index }) => {
  const sectionIcons = [
    <Coffee className="w-6 h-6" />,
    <TrendingUp className="w-6 h-6" />,
    <Moon className="w-6 h-6" />
  ]

  return (
    <div className="mb-12">
      {/* Section header */}
      <div className="relative mb-8">
        <div className="flex items-center gap-4 mb-4">
          <div
            className="p-3 rounded-lg"
            style={{
              backgroundColor: 'var(--color-primary)',
              color: 'var(--color-text-inverse)'
            }}
          >
            {sectionIcons[index]}
          </div>
          <div className="flex-1">
            <h3
              className="text-2xl font-bold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              {section.period}
            </h3>
            <p
              className="text-sm"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {section.startTime} - {section.endTime}
            </p>
          </div>
        </div>

        {/* Section summary */}
        <div
          className="rounded-lg border-2 p-4"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <p
            className="text-sm mb-2"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            {section.summary}
          </p>
          {section.keyAchievement && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
              <Trophy className="w-4 h-4" style={{ color: 'var(--color-success)' }} />
              <span
                className="text-sm font-semibold"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Key Achievement: {section.keyAchievement}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Events timeline */}
      <div className="relative">
        <div className="ml-6">
          {section.events.map((event, idx) => (
            <TimelineEvent
              key={event.id}
              event={event}
              isLast={idx === section.events.length - 1}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export const TimelineLayout: React.FC = () => {
  const [expandedSection, setExpandedSection] = useState<number | null>(null)

  const totalMetrics = {
    totalHours: '9.5',
    tasksCompleted: 8,
    peakPeriods: 2,
    breakTime: '1 hour'
  }

  return (
    <div
      className="min-h-screen p-6 md:p-8"
      style={{ backgroundColor: 'var(--color-background)' }}
    >
      {/* Header */}
      <div className="mb-12">
        <h1
          className="text-4xl font-bold mb-2"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Daily Insights Timeline
        </h1>
        <p
          className="text-lg"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Your productivity journey through the day
        </p>
      </div>

      {/* Key metrics summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
        {[
          { label: 'Total Hours', value: totalMetrics.totalHours, icon: '⏱' },
          { label: 'Tasks Completed', value: totalMetrics.tasksCompleted, icon: '✓' },
          { label: 'Peak Periods', value: totalMetrics.peakPeriods, icon: '🔥' },
          { label: 'Break Time', value: totalMetrics.breakTime, icon: '☕' }
        ].map((metric, idx) => (
          <div
            key={idx}
            className="rounded-lg border-2 p-4"
            style={{
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-border)'
            }}
          >
            <div
              className="text-sm font-semibold mb-2"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {metric.icon} {metric.label}
            </div>
            <div
              className="text-2xl font-bold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              {metric.value}
            </div>
          </div>
        ))}
      </div>

      {/* Timeline sections */}
      <div>
        {mockTimelineData.map((section, idx) => (
          <TimelineSection
            key={idx}
            section={section}
            index={idx}
          />
        ))}
      </div>

      {/* Daily summary footer */}
      <div
        className="rounded-lg border-2 p-6 mt-12"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-primary)',
          backgroundImage: `linear-gradient(135deg, var(--color-surface) 0%, rgba(59, 130, 246, 0.05) 100%)`
        }}
      >
        <h3
          className="text-xl font-bold mb-3"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Today's Story
        </h3>
        <p
          className="text-sm leading-relaxed mb-4"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Started the day with strong momentum, establishing a solid project foundation during the morning session. The afternoon brought problem-solving challenges that showcased effective debugging skills, resulting in a 35% performance improvement. Ended the day with comprehensive testing and documentation, ensuring quality standards are met. A well-balanced day with productive work sessions punctuated by essential breaks.
        </p>
        <div className="flex flex-wrap gap-2">
          {['Productivity', 'Problem-solving', 'Quality-focused', 'Well-balanced'].map(
            (tag, idx) => (
              <span
                key={idx}
                className="text-xs font-bold px-3 py-1 rounded-full"
                style={{
                  backgroundColor: 'var(--color-accent)',
                  color: 'var(--color-text-inverse)'
                }}
              >
                #{tag}
              </span>
            )
          )}
        </div>
      </div>
    </div>
  )
}

export default TimelineLayout
