import { useState, useEffect } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Clock,
  Filter,
  FileText,
  Settings,
  Calendar,
  Folder,
  X,
  Tag,
  Search,
  CheckSquare,
  Square,
  ChevronRight,
  ChevronDown as ChevronDownIcon,
  Code2,
  Trash2,
  BookOpen,
  FileCode,
  History,
  GitCommit,
  Zap,
  Sunrise,
  Sun,
  Moon,
  CalendarDays,
  CalendarRange,
  Layers,
  FileStack,
  Sparkles
} from 'lucide-react'
import { apiRequest } from '../../utils/api'
import { fuzzyMatch } from '../../utils/fuzzyMatch'

// Type definitions
interface WatchedFileNode {
  path: string
  name: string
  type: 'file' | 'directory'
  size?: number
  lastModified?: number
  children?: WatchedFileNode[]
}

export interface SummaryContextConfig {
  timeWindow: {
    preset: 'last_hour' | '6_hours' | '24_hours' | '7_days' | 'custom'
    customStart?: Date
    customEnd?: Date
    includePreviouslyCovered?: boolean
  }
  fileFilters: {
    includePatterns: string[]
    excludePatterns: string[]
    useObbyWatch: boolean
  }
  contentTypes: {
    recentChanges: boolean
    existingContent: boolean
    codeFiles: boolean
    documentation: boolean
    deletedFiles: boolean
  }
  scope: {
    detailLevel: 'brief' | 'standard' | 'detailed'
    focusAreas: string[]
  }
  selectedNotes: string[]
  includePreviousSummaries?: boolean
}

interface SummaryContextControlsProps {
  onConfigChange: (config: SummaryContextConfig) => void
  defaultConfig?: SummaryContextConfig
  isCollapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
}

const DEFAULT_CONFIG: SummaryContextConfig = {
  timeWindow: {
    preset: 'auto',
    includePreviouslyCovered: false,
  },
  fileFilters: {
    includePatterns: [],
    excludePatterns: [],
    useObbyWatch: true,
  },
  contentTypes: {
    recentChanges: true,
    existingContent: false,
    codeFiles: true,
    documentation: true,
    deletedFiles: false,
  },
  scope: {
    detailLevel: 'standard',
    focusAreas: [],
  },
  selectedNotes: [],
  includePreviousSummaries: false,
}

const TIME_PRESETS = [
  { id: 'changes_since_last', label: 'Since Last', sublabel: 'Auto-detect changes', hours: null, mode: 'changes_since_last', icon: 'Zap' },
  { id: 'last_hour', label: 'Last Hour', sublabel: '60 minutes', hours: 1, mode: null, icon: 'Sunrise' },
  { id: '12_hours', label: '12 Hours', sublabel: 'Half day', hours: 12, mode: null, icon: 'Sun' },
  { id: '24_hours', label: '24 Hours', sublabel: 'Full day', hours: 24, mode: null, icon: 'Moon' },
  { id: '7_days', label: '7 Days', sublabel: 'One week', hours: 168, mode: null, icon: 'CalendarDays' },
  { id: 'custom', label: 'Custom', sublabel: 'Pick dates', hours: null, mode: 'custom', icon: 'CalendarRange' },
] as const

export default function SummaryContextControls({
  onConfigChange,
  defaultConfig = DEFAULT_CONFIG,
  isCollapsed: externalCollapsed,
  onCollapsedChange,
}: SummaryContextControlsProps) {
  const [internalCollapsed, setInternalCollapsed] = useState(false)
  const [config, setConfig] = useState<SummaryContextConfig>(defaultConfig)

  // Use external collapsed state if provided, otherwise use internal
  const collapsed = externalCollapsed !== undefined ? externalCollapsed : internalCollapsed
  const setCollapsed = onCollapsedChange || setInternalCollapsed

  // Local state for input fields
  const [focusInput, setFocusInput] = useState('')
  const [showCustomRange, setShowCustomRange] = useState(false)
  
  // Note selector state
  const [notes, setNotes] = useState<WatchedFileNode[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [noteSearchQuery, setNoteSearchQuery] = useState('')
  const [expandedDirectories, setExpandedDirectories] = useState<Set<string>>(new Set())

  useEffect(() => {
    onConfigChange(config)
  }, [config, onConfigChange])

  // Load notes on mount
  useEffect(() => {
    const loadNotes = async () => {
      try {
        setNotesLoading(true)
        const response = await apiRequest<{ directories: any[] }>('/api/files/watched')
        const directories = Array.isArray(response.directories) ? response.directories : []

        const formatted: WatchedFileNode[] = directories.map((directory: any) => {
          const dirChildren: WatchedFileNode[] = Array.isArray(directory.files)
            ? directory.files.map((file: any) => ({
                path: file?.relativePath || file?.path || '',
                name: file?.name || file?.relativePath || file?.path || 'Unknown file',
                type: 'file' as const,
                size: typeof file?.size === 'number' ? file.size : undefined,
                lastModified: typeof file?.lastModified === 'number' ? file.lastModified : undefined
              })).filter((child: WatchedFileNode) => Boolean(child.path))
            : []

          return {
            path: typeof directory?.path === 'string' && directory.path.length > 0
              ? directory.path
              : directory?.name || 'notes',
            name: directory?.name || directory?.path || 'notes',
            type: 'directory' as const,
            children: dirChildren
          }
        }).filter((node: any) => node.children && node.children.length > 0)

        setNotes(formatted)
        // Auto-expand first directory if only one exists
        if (formatted.length === 1) {
          setExpandedDirectories(new Set([formatted[0].path]))
        }
      } catch (err) {
        console.error('Failed to load notes:', err)
      } finally {
        setNotesLoading(false)
      }
    }
    loadNotes()
  }, [])

  // Update config helper
  const updateConfig = <K extends keyof SummaryContextConfig>(
    section: K,
    updates: Partial<SummaryContextConfig[K]>
  ) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        ...updates,
      },
    }))
  }

  // Toggle note selection
  const toggleNoteSelection = (notePath: string) => {
    const isSelected = config.selectedNotes.includes(notePath)
    if (isSelected) {
      updateConfig('selectedNotes', config.selectedNotes.filter(p => p !== notePath))
    } else {
      updateConfig('selectedNotes', [...config.selectedNotes, notePath])
    }
  }

  // Toggle directory expansion
  const toggleDirectory = (dirPath: string) => {
    const newExpanded = new Set(expandedDirectories)
    if (newExpanded.has(dirPath)) {
      newExpanded.delete(dirPath)
    } else {
      newExpanded.add(dirPath)
    }
    setExpandedDirectories(newExpanded)
  }

  // Filter notes based on fuzzy search query
  const filterNotes = (nodes: WatchedFileNode[], query: string): WatchedFileNode[] => {
    if (!query.trim()) return nodes
    
    return nodes.map(dir => {
      // Fuzzy match files in directory
      const filesWithScores = (dir.children || []).map(file => {
        const nameMatch = fuzzyMatch(query, file.name)
        const pathMatch = fuzzyMatch(query, file.path)
        
        // Use the best match score (filename matches weighted higher)
        const score = nameMatch.matches 
          ? nameMatch.score * 2 
          : pathMatch.matches 
            ? pathMatch.score 
            : -1
        
        return { file, score }
      }).filter(item => item.score >= 0)
      
      // Sort by score descending
      filesWithScores.sort((a, b) => b.score - a.score)
      
      const matchingFiles = filesWithScores.map(item => item.file)
      
      // Check if directory name matches
      const dirMatch = fuzzyMatch(query, dir.name)
      
      if (matchingFiles.length > 0 || dirMatch.matches) {
        return { ...dir, children: matchingFiles }
      }
      return null
    }).filter((node): node is WatchedFileNode => node !== null)
  }

  // Format file size
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const filteredNotes = filterNotes(notes, noteSearchQuery)

  // Get icon component from name
  const getIcon = (iconName: string) => {
    const icons: Record<string, any> = {
      Zap, Sunrise, Sun, Moon, CalendarDays, CalendarRange
    }
    return icons[iconName] || Clock
  }

  // Handle time preset selection
  const handlePresetSelect = (presetId: typeof TIME_PRESETS[number]['id']) => {
    const preset = TIME_PRESETS.find(p => p.id === presetId)
    if (preset?.mode === 'changes_since_last') {
      updateConfig('timeWindow', { preset: 'auto', includePreviouslyCovered: false })
      setShowCustomRange(false)
    } else if (preset?.mode === 'custom') {
      setShowCustomRange(true)
      updateConfig('timeWindow', { preset: 'custom', includePreviouslyCovered: false })
    } else {
      updateConfig('timeWindow', { preset: presetId, includePreviouslyCovered: false })
      setShowCustomRange(false)
    }
  }

  // Handle custom date selection
  const handleCustomToggle = () => {
    const isEnabling = !showCustomRange
    setShowCustomRange(isEnabling)

    if (isEnabling) {
      const end = new Date()
      const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
      updateConfig('timeWindow', {
        preset: 'custom',
        customStart: start,
        customEnd: end,
      })
    } else {
      updateConfig('timeWindow', { preset: '24_hours' })
    }
  }

  // Add focus area
  const addFocusArea = () => {
    if (focusInput.trim()) {
      const areas = focusInput.split(',').map(a => a.trim()).filter(Boolean)
      updateConfig('scope', {
        focusAreas: [...config.scope.focusAreas, ...areas],
      })
      setFocusInput('')
    }
  }

  // Remove focus area
  const removeFocusArea = (area: string) => {
    updateConfig('scope', {
      focusAreas: config.scope.focusAreas.filter(a => a !== area),
    })
  }

  // Format date for datetime-local input
  const formatDateTimeLocal = (date: Date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day}T${hours}:${minutes}`
  }

  return (
    <div
      className="rounded-lg border shadow-sm"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-opacity-50 transition-colors"
        style={{ backgroundColor: 'var(--color-background)' }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center space-x-3">
          <Settings
            size={20}
            style={{ color: 'var(--color-primary)' }}
          />
          <h3
            className="font-semibold text-lg"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Summary Context Controls
          </h3>
        </div>

        {collapsed ? (
          <ChevronDown size={20} style={{ color: 'var(--color-text-secondary)' }} />
        ) : (
          <ChevronUp size={20} style={{ color: 'var(--color-text-secondary)' }} />
        )}
      </div>

      {/* Content */}
      {!collapsed && (
        <div className="p-4 space-y-6">
          {/* Section 1: Time Window Picker */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Clock size={16} style={{ color: 'var(--color-accent)' }} />
              <h4
                className="font-medium text-sm"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Time Window
              </h4>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {TIME_PRESETS.map((preset) => {
                const isSelected = preset.mode === 'changes_since_last'
                  ? config.timeWindow.preset === 'auto'
                  : preset.mode === 'custom'
                    ? showCustomRange
                    : config.timeWindow.preset === preset.id

                const IconComponent = getIcon(preset.icon)

                return (
                  <button
                    key={preset.id}
                    onClick={() => handlePresetSelect(preset.id)}
                    className="group relative p-3 rounded-lg border-2 transition-all duration-200 text-left"
                    style={{
                      borderColor: isSelected
                        ? 'var(--color-primary)'
                        : 'var(--color-border)',
                      backgroundColor: isSelected
                        ? 'rgba(59, 130, 246, 0.08)'
                        : 'var(--color-background)',
                    }}
                  >
                    <div className="flex items-center space-x-3">
                      <div
                        className="p-2 rounded-md transition-colors flex-shrink-0"
                        style={{
                          backgroundColor: isSelected
                            ? 'var(--color-primary)'
                            : 'rgba(59, 130, 246, 0.1)',
                        }}
                      >
                        <IconComponent
                          size={16}
                          style={{
                            color: isSelected
                              ? 'white'
                              : 'var(--color-primary)',
                          }}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div
                          className="font-medium text-sm mb-0.5"
                          style={{ color: 'var(--color-text-primary)' }}
                        >
                          {preset.label}
                        </div>
                        <div
                          className="text-xs truncate"
                          style={{ color: 'var(--color-text-secondary)' }}
                        >
                          {preset.sublabel}
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>

            {showCustomRange && (
              <div
                className="p-4 rounded-lg border-2"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-primary)',
                }}
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label
                      className="block text-sm font-medium mb-2"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Start Date & Time
                    </label>
                    <input
                      type="datetime-local"
                      value={
                        config.timeWindow.customStart
                          ? formatDateTimeLocal(config.timeWindow.customStart)
                          : ''
                      }
                      onChange={(e) =>
                        updateConfig('timeWindow', {
                          customStart: new Date(e.target.value),
                        })
                      }
                      className="w-full px-3 py-2.5 text-sm rounded-lg border-2 transition-all"
                      style={{
                        backgroundColor: 'var(--color-background)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                    />
                  </div>
                  <div>
                    <label
                      className="block text-sm font-medium mb-2"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      End Date & Time
                    </label>
                    <input
                      type="datetime-local"
                      value={
                        config.timeWindow.customEnd
                          ? formatDateTimeLocal(config.timeWindow.customEnd)
                          : ''
                      }
                      onChange={(e) =>
                        updateConfig('timeWindow', {
                          customEnd: new Date(e.target.value),
                        })
                      }
                      className="w-full px-3 py-2.5 text-sm rounded-lg border-2 transition-all"
                      style={{
                        backgroundColor: 'var(--color-background)',
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-primary)',
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Content Type Filters */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Filter size={16} style={{ color: 'var(--color-accent)' }} />
              <h4
                className="font-medium text-sm"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Content Type Filters
              </h4>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Code Files */}
              <button
                onClick={() => updateConfig('contentTypes', { codeFiles: !config.contentTypes.codeFiles })}
                className="group relative p-4 rounded-lg border-2 transition-all duration-200 text-left"
                style={{
                  borderColor: config.contentTypes.codeFiles
                    ? 'var(--color-primary)'
                    : 'var(--color-border)',
                  backgroundColor: config.contentTypes.codeFiles
                    ? 'rgba(59, 130, 246, 0.08)'
                    : 'var(--color-background)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <div
                    className="p-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: config.contentTypes.codeFiles
                        ? 'var(--color-primary)'
                        : 'rgba(59, 130, 246, 0.1)',
                    }}
                  >
                    <Code2
                      size={18}
                      style={{
                        color: config.contentTypes.codeFiles
                          ? 'white'
                          : 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <div
                      className="font-medium text-sm mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Code Files
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      .py, .ts, .tsx, .js, etc.
                    </div>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border-2 transition-all ${
                      config.contentTypes.codeFiles ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {config.contentTypes.codeFiles && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
              </button>

              {/* Documentation */}
              <button
                onClick={() => updateConfig('contentTypes', { documentation: !config.contentTypes.documentation })}
                className="group relative p-4 rounded-lg border-2 transition-all duration-200 text-left"
                style={{
                  borderColor: config.contentTypes.documentation
                    ? 'var(--color-primary)'
                    : 'var(--color-border)',
                  backgroundColor: config.contentTypes.documentation
                    ? 'rgba(59, 130, 246, 0.08)'
                    : 'var(--color-background)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <div
                    className="p-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: config.contentTypes.documentation
                        ? 'var(--color-primary)'
                        : 'rgba(59, 130, 246, 0.1)',
                    }}
                  >
                    <BookOpen
                      size={18}
                      style={{
                        color: config.contentTypes.documentation
                          ? 'white'
                          : 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <div
                      className="font-medium text-sm mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Documentation
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      Markdown (.md) files
                    </div>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border-2 transition-all ${
                      config.contentTypes.documentation ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {config.contentTypes.documentation && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
              </button>

              {/* Recent Changes */}
              <button
                onClick={() => updateConfig('contentTypes', { recentChanges: !config.contentTypes.recentChanges })}
                className="group relative p-4 rounded-lg border-2 transition-all duration-200 text-left"
                style={{
                  borderColor: config.contentTypes.recentChanges
                    ? 'var(--color-primary)'
                    : 'var(--color-border)',
                  backgroundColor: config.contentTypes.recentChanges
                    ? 'rgba(59, 130, 246, 0.08)'
                    : 'var(--color-background)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <div
                    className="p-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: config.contentTypes.recentChanges
                        ? 'var(--color-primary)'
                        : 'rgba(59, 130, 246, 0.1)',
                    }}
                  >
                    <GitCommit
                      size={18}
                      style={{
                        color: config.contentTypes.recentChanges
                          ? 'white'
                          : 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <div
                      className="font-medium text-sm mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Recent Changes
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      File diffs and modifications
                    </div>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border-2 transition-all ${
                      config.contentTypes.recentChanges ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {config.contentTypes.recentChanges && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
              </button>

              {/* Existing Content */}
              <button
                onClick={() => updateConfig('contentTypes', { existingContent: !config.contentTypes.existingContent })}
                className="group relative p-4 rounded-lg border-2 transition-all duration-200 text-left"
                style={{
                  borderColor: config.contentTypes.existingContent
                    ? 'var(--color-primary)'
                    : 'var(--color-border)',
                  backgroundColor: config.contentTypes.existingContent
                    ? 'rgba(59, 130, 246, 0.08)'
                    : 'var(--color-background)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <div
                    className="p-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: config.contentTypes.existingContent
                        ? 'var(--color-primary)'
                        : 'rgba(59, 130, 246, 0.1)',
                    }}
                  >
                    <FileCode
                      size={18}
                      style={{
                        color: config.contentTypes.existingContent
                          ? 'white'
                          : 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <div
                      className="font-medium text-sm mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Existing Content
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      Current note content
                    </div>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border-2 transition-all ${
                      config.contentTypes.existingContent ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {config.contentTypes.existingContent && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
              </button>

              {/* Previous Summaries */}
              <button
                onClick={() => setConfig({ ...config, includePreviousSummaries: !config.includePreviousSummaries })}
                className="group relative p-4 rounded-lg border-2 transition-all duration-200 text-left"
                style={{
                  borderColor: config.includePreviousSummaries
                    ? 'var(--color-primary)'
                    : 'var(--color-border)',
                  backgroundColor: config.includePreviousSummaries
                    ? 'rgba(59, 130, 246, 0.08)'
                    : 'var(--color-background)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <div
                    className="p-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: config.includePreviousSummaries
                        ? 'var(--color-primary)'
                        : 'rgba(59, 130, 246, 0.1)',
                    }}
                  >
                    <History
                      size={18}
                      style={{
                        color: config.includePreviousSummaries
                          ? 'white'
                          : 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <div
                      className="font-medium text-sm mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Previous Summaries
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      For contextual analysis
                    </div>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border-2 transition-all ${
                      config.includePreviousSummaries ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {config.includePreviousSummaries && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
              </button>

              {/* Deleted Files */}
              <button
                onClick={() => updateConfig('contentTypes', { deletedFiles: !config.contentTypes.deletedFiles })}
                className="group relative p-4 rounded-lg border-2 transition-all duration-200 text-left"
                style={{
                  borderColor: config.contentTypes.deletedFiles
                    ? 'var(--color-primary)'
                    : 'var(--color-border)',
                  backgroundColor: config.contentTypes.deletedFiles
                    ? 'rgba(59, 130, 246, 0.08)'
                    : 'var(--color-background)',
                }}
              >
                <div className="flex items-start space-x-3">
                  <div
                    className="p-2 rounded-md transition-colors"
                    style={{
                      backgroundColor: config.contentTypes.deletedFiles
                        ? 'var(--color-primary)'
                        : 'rgba(59, 130, 246, 0.1)',
                    }}
                  >
                    <Trash2
                      size={18}
                      style={{
                        color: config.contentTypes.deletedFiles
                          ? 'white'
                          : 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <div
                      className="font-medium text-sm mb-1"
                      style={{ color: 'var(--color-text-primary)' }}
                    >
                      Deleted Files
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      Track removed files
                    </div>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border-2 transition-all ${
                      config.contentTypes.deletedFiles ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {config.contentTypes.deletedFiles && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Scope Controls */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Layers size={16} style={{ color: 'var(--color-accent)' }} />
              <h4
                className="font-medium text-sm"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Scope Controls
              </h4>
            </div>


            {/* Detail Level */}
            <div className="space-y-3">
              <label
                className="block text-sm font-medium"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Detail Level
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { level: 'brief' as const, icon: Zap, label: 'Brief', sublabel: 'Quick overview' },
                  { level: 'standard' as const, icon: FileStack, label: 'Standard', sublabel: 'Balanced detail' },
                  { level: 'detailed' as const, icon: Sparkles, label: 'Detailed', sublabel: 'Comprehensive' },
                ].map(({ level, icon: Icon, label, sublabel }) => (
                  <button
                    key={level}
                    onClick={() => updateConfig('scope', { detailLevel: level })}
                    className="group relative p-3 rounded-lg border-2 transition-all duration-200 text-left"
                    style={{
                      borderColor:
                        config.scope.detailLevel === level
                          ? 'var(--color-primary)'
                          : 'var(--color-border)',
                      backgroundColor:
                        config.scope.detailLevel === level
                          ? 'rgba(59, 130, 246, 0.08)'
                          : 'var(--color-background)',
                    }}
                  >
                    <div className="flex flex-col items-center text-center space-y-2">
                      <div
                        className="p-2 rounded-md transition-colors"
                        style={{
                          backgroundColor:
                            config.scope.detailLevel === level
                              ? 'var(--color-primary)'
                              : 'rgba(59, 130, 246, 0.1)',
                        }}
                      >
                        <Icon
                          size={18}
                          style={{
                            color:
                              config.scope.detailLevel === level
                                ? 'white'
                                : 'var(--color-primary)',
                          }}
                        />
                      </div>
                      <div>
                        <div
                          className="font-medium text-sm mb-0.5"
                          style={{ color: 'var(--color-text-primary)' }}
                        >
                          {label}
                        </div>
                        <div
                          className="text-xs"
                          style={{ color: 'var(--color-text-secondary)' }}
                        >
                          {sublabel}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Focus Areas */}
            <div className="space-y-3">
              <label
                className="block text-sm font-medium"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Focus Areas
              </label>
              <div className="flex space-x-2">
                <div className="relative flex-1">
                  <Tag
                    size={16}
                    className="absolute left-3 top-1/2 transform -translate-y-1/2"
                    style={{ color: 'var(--color-text-secondary)' }}
                  />
                  <input
                    type="text"
                    value={focusInput}
                    onChange={(e) => setFocusInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addFocusArea()}
                    placeholder="authentication, database, UI..."
                    className="w-full pl-10 pr-3 py-2.5 text-sm rounded-lg border-2 transition-all"
                    style={{
                      backgroundColor: 'var(--color-background)',
                      borderColor: focusInput ? 'var(--color-primary)' : 'var(--color-border)',
                      color: 'var(--color-text-primary)',
                    }}
                  />
                </div>
                <button
                  onClick={addFocusArea}
                  disabled={!focusInput.trim()}
                  className="px-5 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: 'white',
                  }}
                >
                  Add
                </button>
              </div>

              {config.scope.focusAreas.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {config.scope.focusAreas.map((area) => (
                    <span
                      key={area}
                      className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg border-2 transition-all hover:shadow-sm"
                      style={{
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderColor: 'var(--color-primary)',
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      <Tag size={12} className="mr-1.5" style={{ color: 'var(--color-primary)' }} />
                      {area}
                      <button
                        onClick={() => removeFocusArea(area)}
                        className="ml-2 hover:opacity-70 transition-opacity"
                        style={{ color: 'var(--color-text-secondary)' }}
                      >
                        <X size={14} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Add Notes to Context */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileText size={16} style={{ color: 'var(--color-accent)' }} />
                <h4
                  className="font-medium text-sm"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  Add Notes to Context
                </h4>
              </div>
              {config.selectedNotes.length > 0 && (
                <span
                  className="px-3 py-1 text-xs font-semibold rounded-full"
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: 'white',
                  }}
                >
                  {config.selectedNotes.length} selected
                </span>
              )}
            </div>

            <div className="space-y-3">
              {/* Search Input */}
              <div className="relative">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 transform -translate-y-1/2"
                  style={{ color: 'var(--color-text-secondary)' }}
                />
                <input
                  type="text"
                  value={noteSearchQuery}
                  onChange={(e) => setNoteSearchQuery(e.target.value)}
                  placeholder="Search notes..."
                  className="w-full pl-10 pr-3 py-2.5 text-sm rounded-lg border-2 transition-all"
                  style={{
                    backgroundColor: 'var(--color-background)',
                    borderColor: noteSearchQuery ? 'var(--color-primary)' : 'var(--color-border)',
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>

              {/* Notes List */}
              <div
                className="rounded-lg border-2 overflow-hidden"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-border)',
                  maxHeight: '400px',
                  overflowY: 'auto',
                }}
              >
                {notesLoading ? (
                  <div className="p-4 text-center text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    Loading notes...
                  </div>
                ) : filteredNotes.length === 0 ? (
                  <div className="p-4 text-center text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    {noteSearchQuery ? 'No notes found matching your search.' : 'No notes available.'}
                  </div>
                ) : (
                  <div className="p-2">
                    {filteredNotes.map((directory) => (
                      <div key={directory.path} className="mb-2">
                        {/* Directory Header */}
                        <button
                          onClick={() => toggleDirectory(directory.path)}
                          className="w-full flex items-center space-x-2 px-2 py-1.5 rounded hover:bg-opacity-50 transition-colors text-left"
                          style={{
                            backgroundColor: expandedDirectories.has(directory.path)
                              ? 'rgba(59, 130, 246, 0.1)'
                              : 'transparent',
                          }}
                        >
                          {expandedDirectories.has(directory.path) ? (
                            <ChevronDownIcon size={14} style={{ color: 'var(--color-text-secondary)' }} />
                          ) : (
                            <ChevronRight size={14} style={{ color: 'var(--color-text-secondary)' }} />
                          )}
                          <Folder size={14} style={{ color: 'var(--color-accent)' }} />
                          <span className="text-sm font-medium flex-1" style={{ color: 'var(--color-text-primary)' }}>
                            {directory.name}
                          </span>
                          <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            {directory.children?.length || 0} files
                          </span>
                        </button>

                        {/* Directory Files */}
                        {expandedDirectories.has(directory.path) && directory.children && (
                          <div className="ml-6 mt-1 space-y-1">
                            {directory.children.map((file) => {
                              const isSelected = config.selectedNotes.includes(file.path)
                              return (
                                <button
                                  key={file.path}
                                  onClick={() => toggleNoteSelection(file.path)}
                                  className="w-full flex items-center space-x-2 px-2 py-1.5 rounded hover:bg-opacity-50 transition-all text-left group"
                                  style={{
                                    backgroundColor: isSelected
                                      ? 'rgba(59, 130, 246, 0.15)'
                                      : 'transparent',
                                  }}
                                >
                                  {isSelected ? (
                                    <CheckSquare
                                      size={16}
                                      style={{ color: 'var(--color-primary)' }}
                                    />
                                  ) : (
                                    <Square
                                      size={16}
                                      style={{ color: 'var(--color-text-secondary)' }}
                                      className="group-hover:opacity-70"
                                    />
                                  )}
                                  <FileText size={14} style={{ color: 'var(--color-text-secondary)' }} />
                                  <span
                                    className="text-sm flex-1 truncate"
                                    style={{
                                      color: isSelected
                                        ? 'var(--color-text-primary)'
                                        : 'var(--color-text-secondary)',
                                      fontWeight: isSelected ? '500' : '400',
                                    }}
                                  >
                                    {file.name}
                                  </span>
                                  {file.size && (
                                    <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                                      {formatFileSize(file.size)}
                                    </span>
                                  )}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Selected Notes Summary */}
              {config.selectedNotes.length > 0 && (
                <div className="space-y-3">
                  <div className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    Selected Notes ({config.selectedNotes.length})
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {config.selectedNotes.map((notePath) => {
                      const noteName = notePath.split('/').pop() || notePath
                      return (
                        <span
                          key={notePath}
                          className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg border-2 transition-all hover:shadow-sm"
                          style={{
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            borderColor: 'var(--color-primary)',
                            color: 'var(--color-text-primary)',
                          }}
                        >
                          <FileText size={12} className="mr-1.5" style={{ color: 'var(--color-primary)' }} />
                          {noteName}
                          <button
                            onClick={() => toggleNoteSelection(notePath)}
                            className="ml-2 hover:opacity-70 transition-opacity"
                            style={{ color: 'var(--color-text-secondary)' }}
                          >
                            <X size={14} />
                          </button>
                        </span>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
