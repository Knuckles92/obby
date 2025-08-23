import { ChevronLeft, ChevronRight, FileText, Trash2, CheckSquare, Square } from 'lucide-react'
import { SummaryNote, SummaryPaginationInfo } from '../types'
import SummaryCard from './SummaryCard'

interface SummaryGridProps {
  summaries: SummaryNote[]
  pagination: SummaryPaginationInfo
  loading: boolean
  onPageChange: (page: number) => void
  onViewSummary: (filename: string) => void
  onDeleteSummary: (filename: string) => void
  selectedSummary?: string | null
  isSelectMode?: boolean
  selectedItems?: Set<string>
  onSelectItem?: (filename: string) => void
  onSelectAll?: () => void
  onClearSelection?: () => void
  onBulkDelete?: () => void
}

export default function SummaryGrid({ 
  summaries, 
  pagination, 
  loading, 
  onPageChange, 
  onViewSummary, 
  onDeleteSummary,
  selectedSummary,
  isSelectMode = false,
  selectedItems = new Set(),
  onSelectItem,
  onSelectAll,
  onClearSelection,
  onBulkDelete
}: SummaryGridProps) {
  
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.total_pages && newPage !== pagination.current_page) {
      onPageChange(newPage)
    }
  }

  const generatePageNumbers = () => {
    const pages = []
    const current = pagination.current_page
    const total = pagination.total_pages
    
    // Always show first page
    if (total > 0) pages.push(1)
    
    // Show ellipsis if needed
    if (current > 4) pages.push('...')
    
    // Show pages around current page
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
      if (!pages.includes(i)) pages.push(i)
    }
    
    // Show ellipsis if needed
    if (current < total - 3) pages.push('...')
    
    // Always show last page
    if (total > 1 && !pages.includes(total)) pages.push(total)
    
    return pages
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (summaries.length === 0) {
    return (
      <div className="card">
        <div className="text-center py-12">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">No summary notes found</p>
          <p className="text-sm text-gray-500 mt-2">
            AI-generated summaries will appear here as you make changes to your notes
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Bulk Action Toolbar - Only show when items are selected */}
      {isSelectMode && selectedItems.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-sm font-medium text-blue-900">
                {selectedItems.size} {selectedItems.size === 1 ? 'item' : 'items'} selected
              </div>
              <div className="hidden sm:block text-xs text-blue-600">
                Press <kbd className="px-1 py-0.5 bg-white border border-blue-200 rounded text-xs">Ctrl+A</kbd> to select all, 
                <kbd className="px-1 py-0.5 bg-white border border-blue-200 rounded text-xs ml-1">Del</kbd> to delete, 
                <kbd className="px-1 py-0.5 bg-white border border-blue-200 rounded text-xs ml-1">Esc</kbd> to exit
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={onSelectAll}
                  className="flex items-center px-3 py-1 text-sm text-blue-700 hover:bg-blue-100 rounded-md transition-colors"
                  title={selectedItems.size === summaries.length ? "Clear selection" : "Select all on page"}
                >
                  {selectedItems.size === summaries.length ? (
                    <>
                      <Square className="h-4 w-4 mr-1" />
                      Clear All
                    </>
                  ) : (
                    <>
                      <CheckSquare className="h-4 w-4 mr-1" />
                      Select All
                    </>
                  )}
                </button>
                <button
                  onClick={onClearSelection}
                  className="flex items-center px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                  title="Clear selection"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={onBulkDelete}
                className="flex items-center px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
                title={`Delete ${selectedItems.size} selected ${selectedItems.size === 1 ? 'item' : 'items'}`}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete {selectedItems.size}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Grid of summary cards */}
      <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {summaries.map((summary) => (
          <div key={summary.filename} className="group">
            <SummaryCard
              summary={summary}
              onView={onViewSummary}
              onDelete={onDeleteSummary}
              isSelected={selectedSummary === summary.filename}
              isSelectMode={isSelectMode}
              isItemSelected={selectedItems.has(summary.filename)}
              onSelect={onSelectItem}
            />
          </div>
        ))}
      </div>

      {/* Pagination controls */}
      {pagination.total_pages > 1 && (
        <div className="card">
          <div className="flex flex-col sm:flex-row items-center justify-between space-y-4 sm:space-y-0">
            {/* Previous button */}
            <button
              onClick={() => handlePageChange(pagination.current_page - 1)}
              disabled={!pagination.has_previous}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--color-surface)',
                color: 'var(--color-text-secondary)',
                borderRadius: 'var(--border-radius-md)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 'var(--font-weight-medium)',
                transition: 'background-color 0.2s ease'
              }}
            >
              <ChevronLeft className="h-5 w-5 mr-2" />
              Previous
            </button>

            {/* Page numbers */}
            <div className="flex items-center space-x-2">
              {generatePageNumbers().map((page, index) => (
                <div key={index}>
                  {page === '...' ? (
                    <span 
                      className="px-3 py-1 text-gray-500"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      ...
                    </span>
                  ) : (
                    <button
                      onClick={() => handlePageChange(page as number)}
                      className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                        pagination.current_page === page
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                      style={{
                        backgroundColor: pagination.current_page === page 
                          ? 'var(--color-primary)' 
                          : 'transparent',
                        color: pagination.current_page === page 
                          ? 'var(--color-text-inverse)' 
                          : 'var(--color-text-secondary)',
                        borderRadius: 'var(--border-radius-md)',
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 'var(--font-weight-medium)',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        if (pagination.current_page !== page) {
                          e.currentTarget.style.backgroundColor = 'var(--color-hover)'
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (pagination.current_page !== page) {
                          e.currentTarget.style.backgroundColor = 'transparent'
                        }
                      }}
                    >
                      {page}
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Next button */}
            <button
              onClick={() => handlePageChange(pagination.current_page + 1)}
              disabled={!pagination.has_next}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--color-surface)',
                color: 'var(--color-text-secondary)',
                borderRadius: 'var(--border-radius-md)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 'var(--font-weight-medium)',
                transition: 'background-color 0.2s ease'
              }}
            >
              Next
              <ChevronRight className="h-5 w-5 ml-2" />
            </button>
          </div>

          {/* Page info */}
          <div 
            className="mt-4 text-center text-sm text-gray-500"
            style={{ 
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)'
            }}
          >
            Showing {summaries.length} of {pagination.total_count} summaries
            (Page {pagination.current_page} of {pagination.total_pages})
          </div>
        </div>
      )}
    </div>
  )
}