import { useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Filter,
  AlertCircle,
  ExternalLink,
  Tag,
} from 'lucide-react'
import { SummaryGenerationPlan, MatchedFile } from '../../types'

interface GenerationPreviewProps {
  previewData: SummaryGenerationPlan
  isLoading?: boolean
  onGenerate: () => void
  onAdjustFilters: () => void
  summaryType?: 'session' | 'note'
}

export default function GenerationPreview({
  previewData,
  isLoading = false,
  onGenerate,
  onAdjustFilters,
  summaryType = 'note',
}: GenerationPreviewProps) {
  const [filesExpanded, setFilesExpanded] = useState(false)
  const [showAllFiles, setShowAllFiles] = useState(false)

  // Helper functions
  const formatDate = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes === 0) return 'N/A'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${Math.round((bytes / Math.pow(k, i)) * 10) / 10} ${sizes[i]}`
  }

  const getNetChange = () => {
    return previewData.total_lines_added - previewData.total_lines_removed
  }

  const truncatePath = (path: string, maxLength: number = 60) => {
    if (path.length <= maxLength) return path
    const parts = path.split('/')
    if (parts.length <= 2) return path

    // Show first and last parts
    return `${parts[0]}/.../${parts[parts.length - 1]}`
  }

  // Display logic
  const displayedFiles = showAllFiles
    ? previewData.matched_files
    : previewData.matched_files.slice(0, 5)
  const hasMoreFiles = previewData.matched_files.length > 5

  if (isLoading) {
    return (
      <div
        className="rounded-lg border shadow-sm p-8 flex items-center justify-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
        }}
      >
        <div className="text-center space-y-3">
          <div className="shimmer-loading rounded-full w-12 h-12 mx-auto" />
          <p
            className="text-sm font-medium"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Analyzing files and generating preview...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      className="rounded-lg border shadow-sm overflow-hidden"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Header */}
      <div
        className="p-4 border-b"
        style={{
          backgroundColor: 'var(--color-background)',
          borderColor: 'var(--color-border)',
        }}
      >
        <h3
          className="font-semibold text-lg flex items-center"
          style={{ color: 'var(--color-text-primary)' }}
        >
          <CheckCircle
            size={20}
            className="mr-2"
            style={{ color: 'var(--color-success)' }}
          />
          Generation Preview Ready
        </h3>
        <p
          className="text-sm mt-1"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Review what will be included in your {summaryType === 'session' ? 'session summary' : 'summary note'}
        </p>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* 1. Time Range Summary */}
        <div
          className="p-4 rounded-lg border-l-4"
          style={{
            backgroundColor: 'var(--color-background)',
            borderLeftColor: 'var(--color-primary)',
          }}
        >
          <div className="flex items-center space-x-2">
            <Clock size={18} style={{ color: 'var(--color-primary)' }} />
            <h4
              className="font-semibold text-sm"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Time Range
            </h4>
          </div>
          <p
            className="mt-2 text-base font-medium"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Analyzing changes from {previewData.time_range_description}
          </p>
        </div>

        {/* 2. Statistics Box */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {/* Total Files */}
          <div
            className="p-4 rounded-lg text-center"
            style={{
              backgroundColor: 'var(--color-info)',
              color: 'white',
            }}
          >
            <FileText size={24} className="mx-auto mb-2" />
            <div className="text-2xl font-bold">{previewData.total_files}</div>
            <div className="text-xs font-medium opacity-90 mt-1">
              {previewData.total_files === 1 ? 'File' : 'Files'} Matched
            </div>
          </div>

          {/* Total Changes */}
          <div
            className="p-4 rounded-lg text-center"
            style={{
              backgroundColor: 'var(--color-warning)',
              color: 'white',
            }}
          >
            <Tag size={24} className="mx-auto mb-2" />
            <div className="text-2xl font-bold">{previewData.total_changes}</div>
            <div className="text-xs font-medium opacity-90 mt-1">
              Total Changes
            </div>
          </div>

          {/* Lines Added */}
          <div
            className="p-4 rounded-lg text-center"
            style={{
              backgroundColor: 'var(--color-success)',
              color: 'white',
            }}
          >
            <TrendingUp size={24} className="mx-auto mb-2" />
            <div className="text-2xl font-bold">+{previewData.total_lines_added}</div>
            <div className="text-xs font-medium opacity-90 mt-1">
              Lines Added
            </div>
          </div>

          {/* Lines Removed */}
          <div
            className="p-4 rounded-lg text-center"
            style={{
              backgroundColor: 'var(--color-error)',
              color: 'white',
            }}
          >
            <TrendingDown size={24} className="mx-auto mb-2" />
            <div className="text-2xl font-bold">-{previewData.total_lines_removed}</div>
            <div className="text-xs font-medium opacity-90 mt-1">
              Lines Removed
            </div>
          </div>

          {/* Net Change */}
          <div
            className="p-4 rounded-lg text-center col-span-2 md:col-span-1"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: 'white',
            }}
          >
            <Minus size={24} className="mx-auto mb-2" />
            <div className="text-2xl font-bold">
              {getNetChange() > 0 ? '+' : ''}
              {getNetChange()}
            </div>
            <div className="text-xs font-medium opacity-90 mt-1">Net Change</div>
          </div>
        </div>

        {/* 3. Matched Files List */}
        <div
          className="border rounded-lg overflow-hidden"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <button
            onClick={() => setFilesExpanded(!filesExpanded)}
            className="w-full p-3 flex items-center justify-between hover:bg-opacity-50 transition-colors"
            style={{ backgroundColor: 'var(--color-background)' }}
          >
            <div className="flex items-center space-x-2">
              <FileText size={16} style={{ color: 'var(--color-accent)' }} />
              <span
                className="font-medium text-sm"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Matched Files
              </span>
              <span
                className="px-2 py-0.5 text-xs font-medium rounded-full"
                style={{
                  backgroundColor: 'var(--color-primary)',
                  color: 'white',
                }}
              >
                {previewData.total_files}
              </span>
            </div>
            {filesExpanded ? (
              <ChevronUp size={18} style={{ color: 'var(--color-text-secondary)' }} />
            ) : (
              <ChevronDown size={18} style={{ color: 'var(--color-text-secondary)' }} />
            )}
          </button>

          {filesExpanded && (
            <div
              className="max-h-96 overflow-y-auto"
              style={{ backgroundColor: 'var(--color-surface)' }}
            >
              {displayedFiles.length === 0 ? (
                <div className="p-4 text-center">
                  <p
                    className="text-sm"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    No files matched the current filters
                  </p>
                </div>
              ) : (
                <div className="divide-y" style={{ borderColor: 'var(--color-divider)' }}>
                  {displayedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="p-3 hover:bg-opacity-50 transition-colors"
                      style={{ backgroundColor: 'var(--color-background)' }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0 mr-2">
                          <div className="flex items-center space-x-2">
                            <p
                              className="text-sm font-medium truncate"
                              style={{ color: 'var(--color-text-primary)' }}
                              title={file.path}
                            >
                              {truncatePath(file.path)}
                            </p>
                            {file.is_deleted && (
                              <span
                                className="px-2 py-0.5 text-xs font-medium rounded"
                                style={{
                                  backgroundColor: 'var(--color-error)',
                                  color: 'white',
                                }}
                              >
                                Deleted
                              </span>
                            )}
                          </div>
                          <p
                            className="text-xs mt-1"
                            style={{ color: 'var(--color-text-secondary)' }}
                          >
                            {file.change_summary}
                          </p>
                          <div className="flex items-center space-x-3 mt-1 text-xs">
                            <span style={{ color: 'var(--color-text-secondary)' }}>
                              {formatDate(file.last_modified)}
                            </span>
                            {file.size_bytes !== undefined && (
                              <span style={{ color: 'var(--color-text-secondary)' }}>
                                {formatFileSize(file.size_bytes)}
                              </span>
                            )}
                          </div>
                        </div>
                        <button
                          className="p-1.5 rounded hover:bg-opacity-50 transition-colors"
                          style={{ backgroundColor: 'var(--color-surface)' }}
                          title="View file"
                        >
                          <ExternalLink
                            size={14}
                            style={{ color: 'var(--color-primary)' }}
                          />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* View All Toggle */}
              {hasMoreFiles && (
                <div
                  className="p-3 border-t text-center"
                  style={{ borderColor: 'var(--color-border)' }}
                >
                  <button
                    onClick={() => setShowAllFiles(!showAllFiles)}
                    className="text-sm font-medium px-4 py-2 rounded-md hover:bg-opacity-80 transition-colors"
                    style={{
                      color: 'var(--color-primary)',
                      backgroundColor: 'var(--color-background)',
                    }}
                  >
                    {showAllFiles
                      ? 'Show Less'
                      : `View All ${previewData.matched_files.length} Files`}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 4. Filters Applied */}
        {previewData.filters_applied.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Filter size={16} style={{ color: 'var(--color-accent)' }} />
              <h4
                className="font-medium text-sm"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Filters Applied
              </h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {previewData.filters_applied.map((filter, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 text-xs font-medium rounded-full"
                  style={{
                    backgroundColor: 'var(--color-background)',
                    color: 'var(--color-text-secondary)',
                    border: '1px solid var(--color-border)',
                  }}
                >
                  {filter}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 5. Warnings Section */}
        {previewData.warnings.length > 0 && (
          <div
            className="p-4 rounded-lg border-l-4"
            style={{
              backgroundColor: 'var(--color-background)',
              borderLeftColor: 'var(--color-warning)',
            }}
          >
            <div className="flex items-start space-x-3">
              <AlertTriangle
                size={20}
                className="flex-shrink-0 mt-0.5"
                style={{ color: 'var(--color-warning)' }}
              />
              <div className="flex-1">
                <h4
                  className="font-semibold text-sm mb-2"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  Warnings
                </h4>
                <ul className="space-y-1">
                  {previewData.warnings.map((warning, index) => (
                    <li
                      key={index}
                      className="text-sm flex items-start space-x-2"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      <AlertCircle
                        size={14}
                        className="flex-shrink-0 mt-0.5"
                        style={{ color: 'var(--color-warning)' }}
                      />
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <button
            onClick={onGenerate}
            disabled={previewData.total_files === 0}
            className="flex-1 px-6 py-3 text-sm font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg"
            style={{
              backgroundColor: 'var(--color-primary)',
              color: 'white',
            }}
          >
            <span className="flex items-center justify-center space-x-2">
              <CheckCircle size={18} />
              <span>Generate with this Context</span>
            </span>
          </button>
          <button
            onClick={onAdjustFilters}
            className="px-6 py-3 text-sm font-semibold rounded-lg transition-all duration-200 hover:shadow-md"
            style={{
              backgroundColor: 'var(--color-background)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)',
            }}
          >
            <span className="flex items-center justify-center space-x-2">
              <Filter size={18} />
              <span>Adjust Filters</span>
            </span>
          </button>
        </div>
      </div>
    </div>
  )
}
