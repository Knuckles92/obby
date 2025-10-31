import { useState, useEffect } from 'react'
import { FileText, Clock, Hash, RefreshCw, Trash2, Archive, Copy } from 'lucide-react'
import { ContentDiff, FileChange, FileMonitoringStatus, PaginatedDiffsResponse, PaginatedChangesResponse, PaginationMetadata } from '../types'
import { apiFetch } from '../utils/api'
import ConfirmationDialog from '../components/ConfirmationDialog'

type DiffLine = {
  type: 'addition' | 'deletion' | 'hunk'
  content: string
}

type DiffChunk = {
  type: 'addition' | 'deletion' | 'hunk'
  lines: string[]
}

export default function DiffViewer() {
  const [diffs, setDiffs] = useState<ContentDiff[]>([])
  const [fileChanges, setFileChanges] = useState<FileChange[]>([])
  const [selectedDiff, setSelectedDiff] = useState<ContentDiff | null>(null)
  const [selectedChange, setSelectedChange] = useState<FileChange | null>(null)
  const [monitoringStatus, setMonitoringStatus] = useState<FileMonitoringStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showClearDialog, setShowClearDialog] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState<'diffs' | 'changes'>('diffs')
  const [copied, setCopied] = useState(false)

  // Pagination state
  const [diffsPagination, setDiffsPagination] = useState<PaginationMetadata | null>(null)
  const [changesPagination, setChangesPagination] = useState<PaginationMetadata | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    fetchFileData()
  }, [])

  const fetchFileData = async (reset: boolean = true) => {
    try {
      setError(null)
      
      // Reset pagination and data if this is a fresh fetch
      if (reset) {
        setDiffs([])
        setFileChanges([])
        setDiffsPagination(null)
        setChangesPagination(null)
      }
      
      // Fetch recent diffs
      const diffsResponse = await apiFetch('/api/files/diffs?limit=50')
      if (!diffsResponse.ok) {
        throw new Error(`Failed to fetch diffs: ${diffsResponse.status}`)
      }
      const diffsResponseData: PaginatedDiffsResponse = await diffsResponse.json()
      
      // Fetch recent file changes
      const changesResponse = await apiFetch('/api/files/changes?limit=50')
      if (!changesResponse.ok) {
        throw new Error(`Failed to fetch changes: ${changesResponse.status}`)
      }
      const changesResponseData: PaginatedChangesResponse = await changesResponse.json()
      
      // Fetch file monitoring status
      const statusResponse = await apiFetch('/api/files/monitoring-status') 
      const statusData = statusResponse.ok ? await statusResponse.json() : null
      
      setDiffs(diffsResponseData.diffs || [])
      setDiffsPagination(diffsResponseData.pagination)
      setFileChanges(changesResponseData.changes || [])
      setChangesPagination(changesResponseData.pagination)
      setMonitoringStatus(statusData)
      
    } catch (error) {
      console.error('Error fetching file data:', error)
      setError(error instanceof Error ? error.message : 'Failed to load file data')
      setDiffs([])
      setFileChanges([])
      setDiffsPagination(null)
      setChangesPagination(null)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await fetchFileData()
    } finally {
      setRefreshing(false)
    }
  }

  const loadMoreDiffs = async () => {
    if (!diffsPagination?.hasMore || loadingMore) return
    
    setLoadingMore(true)
    try {
      const offset = diffsPagination.offset + diffsPagination.limit
      const response = await apiFetch(`/api/files/diffs?limit=50&offset=${offset}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch more diffs: ${response.status}`)
      }
      
      const responseData: PaginatedDiffsResponse = await response.json()
      
      // Append new diffs to existing ones
      setDiffs(prevDiffs => [...prevDiffs, ...(responseData.diffs || [])])
      setDiffsPagination(responseData.pagination)
      
    } catch (error) {
      console.error('Error loading more diffs:', error)
      setError(error instanceof Error ? error.message : 'Failed to load more diffs')
    } finally {
      setLoadingMore(false)
    }
  }

  const loadMoreChanges = async () => {
    if (!changesPagination?.hasMore || loadingMore) return
    
    setLoadingMore(true)
    try {
      const offset = changesPagination.offset + changesPagination.limit
      const response = await apiFetch(`/api/files/changes?limit=50&offset=${offset}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch more changes: ${response.status}`)
      }
      
      const responseData: PaginatedChangesResponse = await response.json()
      
      // Append new changes to existing ones
      setFileChanges(prevChanges => [...prevChanges, ...(responseData.changes || [])])
      setChangesPagination(responseData.pagination)
      
    } catch (error) {
      console.error('Error loading more changes:', error)
      setError(error instanceof Error ? error.message : 'Failed to load more changes')
    } finally {
      setLoadingMore(false)
    }
  }

  const handleDiffSelection = (diff: ContentDiff) => {
    setSelectedDiff(diff)
    setSelectedChange(null)
  }

  const handleChangeSelection = (change: FileChange) => {
    setSelectedChange(change)
    setSelectedDiff(null)
  }

  const resetSelection = () => {
    setSelectedDiff(null)
    setSelectedChange(null)
  }

  const handleClearAllData = async () => {
    try {
      setClearing(true)
      // Note: This endpoint may need to be implemented
      const response = await apiFetch('/api/files/clear', {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error(`Failed to clear data: ${response.status}`)
      }
      
      await fetchFileData()
      setSelectedDiff(null)
      setSelectedChange(null)
      setShowClearDialog(false)
      
    } catch (error) {
      console.error('Error clearing data:', error)
      setError(error instanceof Error ? error.message : 'Failed to clear data')
    } finally {
      setClearing(false)
    }
  }

  const formatTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return `${Math.floor(diffMins / 1440)}d ago`
  }

  const getChangeTypeColor = (type: string) => {
    switch (type) {
      case 'created': return 'text-green-600 bg-green-50'
      case 'modified': return 'text-blue-600 bg-blue-50'
      case 'deleted': return 'text-red-600 bg-red-50'
      case 'moved': return 'text-purple-600 bg-purple-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const buildDiffLines = (diffContent: string): DiffLine[] => {
    if (!diffContent) return []

    const rawLines = diffContent.split('\n')
    const diffLines: DiffLine[] = []

    rawLines.forEach(rawLine => {
      if (!rawLine || rawLine.startsWith('\\ No newline at end of file')) {
        return
      }

      if (rawLine.startsWith('@@')) {
        diffLines.push({ type: 'hunk', content: rawLine })
        return
      }

      if (rawLine.startsWith('+++') || rawLine.startsWith('---') || rawLine.startsWith('diff ') || rawLine.startsWith('index ')) {
        return
      }

      if (rawLine.startsWith('+') && !rawLine.startsWith('+++')) {
        diffLines.push({ type: 'addition', content: rawLine.slice(1) })
        return
      }

      if (rawLine.startsWith('-') && !rawLine.startsWith('---')) {
        diffLines.push({ type: 'deletion', content: rawLine.slice(1) })
      }
    })

    return diffLines
  }

  const parseHunkHeader = (hunkLine: string): string => {
    // Format: @@ -old_start,old_count +new_start,new_count @@
    const match = hunkLine.match(/@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@/)

    if (!match) {
      return 'Changed section'
    }

    const oldStart = parseInt(match[1])
    const oldCount = match[2] ? parseInt(match[2]) : 1
    const newStart = parseInt(match[3])
    const newCount = match[4] ? parseInt(match[4]) : 1

    const oldEnd = oldStart + oldCount - 1
    const newEnd = newStart + newCount - 1

    // Create a readable description
    if (oldCount === 0) {
      return `Lines ${newStart}-${newEnd} added`
    } else if (newCount === 0) {
      return `Lines ${oldStart}-${oldEnd} removed`
    } else {
      return `Lines ${oldStart}-${oldEnd} → ${newStart}-${newEnd}`
    }
  }

  const chunkDiffLines = (diffLines: DiffLine[]): DiffChunk[] => {
    if (diffLines.length === 0) return []

    const chunks: DiffChunk[] = []
    let currentChunk: DiffChunk | null = null

    diffLines.forEach(line => {
      // Hunk headers always get their own chunk
      if (line.type === 'hunk') {
        if (currentChunk) {
          chunks.push(currentChunk)
          currentChunk = null
        }
        chunks.push({ type: 'hunk', lines: [line.content] })
        return
      }

      // If we don't have a current chunk or the type changed, start a new chunk
      if (!currentChunk || currentChunk.type !== line.type) {
        if (currentChunk) {
          chunks.push(currentChunk)
        }
        currentChunk = { type: line.type, lines: [line.content] }
      } else {
        // Same type, add to current chunk
        currentChunk.lines.push(line.content)
      }
    })

    // Don't forget the last chunk
    if (currentChunk) {
      chunks.push(currentChunk)
    }

    return chunks
  }

  const renderDiffDisplay = (diffContent: string) => {
    const diffLines = buildDiffLines(diffContent)
    const diffChunks = chunkDiffLines(diffLines)

    if (diffChunks.length === 0) {
      return (
        <p className="px-6 py-5 text-sm text-slate-500">
          No added or deleted lines were captured in this diff.
        </p>
      )
    }

    return (
      <div className="space-y-2.5 px-6 py-5">
        {diffChunks.map((chunk, chunkIndex) => {
          if (chunk.type === 'hunk') {
            return (
              <div
                key={`hunk-${chunkIndex}`}
                className="rounded-xl border border-indigo-200/60 bg-indigo-50 px-4 py-2.5 text-xs font-medium text-indigo-700 flex items-center gap-2"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400"></div>
                {parseHunkHeader(chunk.lines[0])}
              </div>
            )
          }

          const isAddition = chunk.type === 'addition'

          return (
            <div
              key={`chunk-${chunkIndex}`}
              className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-[13px] font-mono leading-relaxed shadow-sm ${isAddition
                ? 'border-emerald-200/80 bg-emerald-50 text-emerald-900'
                : 'border-rose-200/80 bg-rose-50 text-rose-900'
              }`}
            >
              <span className="mt-1 font-semibold select-none">
                {isAddition ? '+' : '-'}
              </span>
              <div className="flex-1">
                {chunk.lines.map((line, lineIndex) => (
                  <div key={`line-${lineIndex}`} className="whitespace-pre">
                    {line || ' '}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  const handleCopyDiff = async (diffContent: string) => {
    try {
      await navigator.clipboard.writeText(diffContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy diff content:', error)
    }
  }

  const renderSelectedContent = () => {
    if (selectedDiff) {
      const formattedTimestamp = new Date(selectedDiff.timestamp).toLocaleString()
      const netChange = selectedDiff.linesAdded - selectedDiff.linesRemoved
      const netChangePrefix = netChange >= 0 ? '+' : ''
      const netChangeColor = netChange >= 0 ? 'text-emerald-600' : 'text-rose-600'
      const diffIdentifier = String(selectedDiff.id)
      
      // Extract filename from path (handle both Unix and Windows paths)
      const fileName = selectedDiff.filePath.split(/[/\\]/).pop() || selectedDiff.filePath
      const filePath = selectedDiff.filePath

      return (
        <div className="flex flex-col gap-6">
          <section className="rounded-2xl border border-slate-200 bg-slate-50/80 px-6 py-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className={`inline-flex items-center rounded-full border border-transparent px-2.5 py-1 text-xs font-semibold capitalize ${getChangeTypeColor(selectedDiff.changeType)}`}>
                    {selectedDiff.changeType}
                  </span>
                  <code className="inline-flex items-center rounded-full bg-slate-900/90 px-2.5 py-1 text-xs font-mono text-white shadow-sm">
                    #{diffIdentifier.length > 10 ? `${diffIdentifier.slice(0, 10)}…` : diffIdentifier}
                  </code>
                </div>
                <div className="relative group">
                  <h2 className="text-xl font-semibold leading-snug text-slate-900 break-words pr-2 cursor-help">
                    {fileName}
                  </h2>
                  {/* Hover tooltip with full path */}
                  <div className="absolute left-0 top-full mt-2 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                    <div className="bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl max-w-md break-words whitespace-normal relative">
                      {/* Arrow pointing up */}
                      <div className="absolute -top-1 left-4 w-2 h-2 bg-slate-900 rotate-45"></div>
                      <div className="font-semibold mb-1">Full Path:</div>
                      <div className="font-mono text-slate-300 break-all">{filePath}</div>
                      <div className="mt-2 pt-2 border-t border-slate-700">
                        <div className="text-slate-400">Recorded: {formatTimeAgo(selectedDiff.timestamp)}</div>
                        <div className="text-slate-400 text-xs mt-1">{formattedTimestamp}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-slate-500">{formatTimeAgo(selectedDiff.timestamp)}</span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/80 bg-white px-4 py-3 shadow-sm">
                <span className="text-xs uppercase tracking-wide text-slate-500">Lines Added</span>
                <span className="mt-1 block text-lg font-semibold text-emerald-600">
                  +{selectedDiff.linesAdded}
                </span>
              </div>
              <div className="rounded-xl border border-white/80 bg-white px-4 py-3 shadow-sm">
                <span className="text-xs uppercase tracking-wide text-slate-500">Lines Removed</span>
                <span className="mt-1 block text-lg font-semibold text-rose-600">
                  -{selectedDiff.linesRemoved}
                </span>
              </div>
              <div className="rounded-xl border border-white/80 bg-white px-4 py-3 shadow-sm">
                <span className="text-xs uppercase tracking-wide text-slate-500">Net Change</span>
                <span className={`mt-1 block text-lg font-semibold ${netChangeColor}`}>
                  {netChangePrefix}{netChange}
                </span>
              </div>
            </div>
          </section>

          {selectedDiff.diffContent && (
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Diff Preview</p>
                  <p className="text-xs text-slate-500">Only added and removed lines are shown below.</p>
                </div>
                <button
                  onClick={() => handleCopyDiff(selectedDiff.diffContent)}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 transition-colors hover:border-slate-300 hover:text-slate-900"
                  title="Copy diff content"
                >
                  <Copy className="h-3.5 w-3.5" />
                  {copied ? 'Copied!' : 'Copy Lines'}
                </button>
              </div>
              <div className="max-h-[520px] overflow-auto bg-white">
                {renderDiffDisplay(selectedDiff.diffContent)}
              </div>
            </section>
          )}
        </div>
      )
    }

    if (selectedChange) {
      return (
        <div className="flex flex-col gap-6">
          <section className="rounded-2xl border border-slate-200 bg-slate-50/80 px-6 py-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-3">
                <span className={`inline-flex items-center rounded-full border border-transparent px-3 py-1 text-xs font-semibold capitalize ${getChangeTypeColor(selectedChange.changeType)}`}>
                  {selectedChange.changeType}
                </span>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">File</p>
                  <h2 className="mt-2 text-2xl font-semibold leading-snug text-slate-900 break-words">
                    {selectedChange.filePath}
                  </h2>
                </div>
              </div>
              <div className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-right shadow-sm">
                <span className="text-xs uppercase tracking-wide text-slate-500">Occurred</span>
                <span className="text-sm font-semibold text-slate-900">{formatTimeAgo(selectedChange.timestamp)}</span>
                <span className="text-xs text-slate-500">{new Date(selectedChange.timestamp).toLocaleString()}</span>
              </div>
            </div>

            {selectedChange.newContentHash && (
              <div className="mt-6 rounded-2xl border border-white/80 bg-white px-4 py-3 shadow-sm">
                <span className="text-xs uppercase tracking-wide text-slate-500">Latest Hash</span>
                <code className="mt-2 block text-sm font-medium text-slate-900">
                  {selectedChange.newContentHash}
                </code>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-blue-50 px-6 py-6 shadow-inner">
            <h3 className="text-sm font-semibold text-blue-900">Change captured</h3>
            <p className="mt-2 text-sm leading-relaxed text-blue-800">
              This file change was recorded without content diff details. Select a diff from the list to review content-level changes when available.
            </p>
          </section>
        </div>
      )
    }

    return (
      <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-8 py-16 text-center">
        <FileText className="h-10 w-10 text-slate-400" />
        <h3 className="mt-6 text-lg font-semibold text-slate-800">Choose an item to inspect</h3>
        <p className="mt-2 max-w-md text-sm text-slate-500">
          Select a content diff or file change from the activity panel to view detailed metadata and highlighted code updates here.
        </p>
      </div>
    )
  }

  return (
    <div className="min-h-screen space-y-6">
      {/* Modern Header */}
      <div className="relative overflow-hidden rounded-2xl mb-2 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
      }}>
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

        <div className="relative z-10 flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                <Archive className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">File History</h1>
            </div>
            <p className="text-blue-100 text-lg">Browse recent diffs and file change events</p>
          </div>

          {monitoringStatus && (
            <div className={`flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border transition-all duration-300 ${
              monitoringStatus.monitoring_active
                ? 'bg-green-500/20 border-green-400/30 text-green-100'
                : 'bg-red-500/20 border-red-400/30 text-red-100'
            }`}>
              <div className={`w-2 h-2 rounded-full animate-pulse ${
                monitoringStatus.monitoring_active ? 'bg-green-400' : 'bg-red-400'
              }`}></div>
              <span className="text-sm font-medium">
                {monitoringStatus.monitoring_active ? 'Monitoring Active' : 'Monitoring Inactive'}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <section className="flex min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl lg:col-span-2">
          <div className="border-b border-slate-200 bg-slate-50 px-6 py-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Detail View</p>
                <h3 className="mt-1 text-2xl font-semibold text-slate-900">
                  {selectedDiff ? 'Content Diff Details' : selectedChange ? 'File Change Details' : 'Details'}
                </h3>
              </div>
              {(selectedDiff || selectedChange) && (
                <button
                  onClick={resetSelection}
                  className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-slate-300 hover:text-slate-900"
                >
                  Clear selection
                </button>
              )}
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="h-full overflow-y-auto px-6 py-6">
              {renderSelectedContent()}
            </div>
          </div>
        </section>

        <section className="flex min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-slate-50 shadow-xl lg:col-span-1">
          <div className="border-b border-slate-200 bg-white px-5 py-5">
            <div className="space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Activity Feed</p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">Tracked updates</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setActiveTab('diffs')}
                  className={`inline-flex flex-1 items-center justify-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                    activeTab === 'diffs'
                      ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-sm'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:text-blue-700'
                  }`}
                >
                  Content Diffs ({diffsPagination?.total ?? diffs.length})
                </button>
                <button
                  onClick={() => setActiveTab('changes')}
                  className={`inline-flex flex-1 items-center justify-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                    activeTab === 'changes'
                      ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-sm'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:text-blue-700'
                  }`}
                >
                  File Changes ({changesPagination?.total ?? fileChanges.length})
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleRefresh}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={loading || refreshing}
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
                {(diffs.length > 0 || fileChanges.length > 0) && (
                  <button
                    onClick={() => setShowClearDialog(true)}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={loading || clearing}
                  >
                    <Trash2 className="h-4 w-4" />
                    Clear All
                  </button>
                )}
              </div>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="h-full overflow-y-auto px-5 py-4">
              {loading ? (
                <div className="flex h-full items-center justify-center">
                  <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-blue-500"></div>
                </div>
              ) : error ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-5 text-center">
                  <p className="text-sm font-semibold text-rose-600">Error loading file activity</p>
                  <p className="mt-2 text-xs text-rose-500">{error}</p>
                  <button
                    onClick={() => fetchFileData()}
                    className="mt-4 inline-flex items-center justify-center rounded-full bg-rose-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-rose-700"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {activeTab === 'diffs' && diffs.length > 0 && diffs.map((diff) => (
                    <div
                      key={diff.id}
                      onClick={() => handleDiffSelection(diff)}
                      className={`relative cursor-pointer rounded-2xl border px-4 py-4 transition ${
                        selectedDiff?.id === diff.id
                          ? 'border-blue-400 bg-white shadow-sm'
                          : 'border-transparent bg-white/70 hover:border-slate-300 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-3">
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span className={`inline-flex items-center rounded-full border border-transparent px-2.5 py-1 font-semibold capitalize ${getChangeTypeColor(diff.changeType)}`}>
                              {diff.changeType}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatTimeAgo(diff.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm font-semibold leading-snug text-slate-900 break-words">
                            {diff.filePath}
                          </p>
                          <div className="flex items-center gap-4 text-xs font-mono">
                            <span className="text-emerald-600">+{diff.linesAdded}</span>
                            <span className="text-rose-600">-{diff.linesRemoved}</span>
                          </div>
                        </div>
                        <code className="rounded-md bg-slate-900/80 px-2 py-1 text-[10px] font-mono text-white shadow-sm">
                          {String(diff.id).slice(0, 10)}
                        </code>
                      </div>
                    </div>
                  ))}

                  {activeTab === 'changes' && fileChanges.length > 0 && fileChanges.map((change) => (
                    <div
                      key={change.id}
                      onClick={() => handleChangeSelection(change)}
                      className={`relative cursor-pointer rounded-2xl border px-4 py-4 transition ${
                        selectedChange?.id === change.id
                          ? 'border-blue-400 bg-white shadow-sm'
                          : 'border-transparent bg-white/70 hover:border-slate-300 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-3">
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span className={`inline-flex items-center rounded-full border border-transparent px-2.5 py-1 font-semibold capitalize ${getChangeTypeColor(change.changeType)}`}>
                              {change.changeType}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatTimeAgo(change.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm font-semibold leading-snug text-slate-900 break-words">
                            {change.filePath}
                          </p>
                          {change.newContentHash && (
                            <code className="block truncate text-xs font-mono text-slate-600">
                              hash {change.newContentHash.substring(0, 18)}…
                            </code>
                          )}
                        </div>
                        <div className="flex items-center">
                          <Hash className="h-4 w-4 text-slate-300" />
                        </div>
                      </div>
                    </div>
                  ))}

                  {activeTab === 'diffs' && diffs.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-white/70 px-4 py-10 text-center text-sm text-slate-500">
                      No content diffs found
                    </div>
                  )}

                  {activeTab === 'changes' && fileChanges.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-white/70 px-4 py-10 text-center text-sm text-slate-500">
                      No file changes found
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="border-t border-slate-200 bg-white px-5 py-4">
            {!loading && !error && (
              <div className="flex flex-col gap-3">
                {activeTab === 'diffs' && diffsPagination?.hasMore && (
                  <button
                    onClick={loadMoreDiffs}
                    disabled={loadingMore}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-primary-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loadingMore ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                        Loading…
                      </>
                    ) : (
                      <>
                        Load more
                        {typeof diffsPagination.total === 'number' && (
                          <span className="font-normal text-white/80">
                            ({Math.max(diffsPagination.total - diffs.length, 0)} remaining)
                          </span>
                        )}
                      </>
                    )}
                  </button>
                )}
                {activeTab === 'changes' && changesPagination?.hasMore && (
                  <button
                    onClick={loadMoreChanges}
                    disabled={loadingMore}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-primary-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loadingMore ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                        Loading…
                      </>
                    ) : (
                      <>
                        Load more
                        {typeof changesPagination.total === 'number' && (
                          <span className="font-normal text-white/80">
                            ({Math.max(changesPagination.total - fileChanges.length, 0)} remaining)
                          </span>
                        )}
                      </>
                    )}
                  </button>
                )}
                {activeTab === 'diffs' && diffsPagination && diffs.length > 0 && (
                  <p className="text-center text-xs text-slate-500">
                    Showing {diffs.length} of {diffsPagination.total} content diffs
                  </p>
                )}
                {activeTab === 'changes' && changesPagination && fileChanges.length > 0 && (
                  <p className="text-center text-xs text-slate-500">
                    Showing {fileChanges.length} of {changesPagination.total} file changes
                  </p>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      <ConfirmationDialog
        isOpen={showClearDialog}
        onClose={() => setShowClearDialog(false)}
        onConfirm={handleClearAllData}
        title="Clear All File History"
        message={`Are you sure you want to clear all ${diffs.length} diff(s) and ${fileChanges.length} file change(s) from the database? This will not affect your actual files.`}
        confirmText="Clear All"
        cancelText="Cancel"
        danger={true}
        loading={clearing}
        extraWarning="This will only clear Obby's database records, not your actual files."
      />
    </div>
  )
}
