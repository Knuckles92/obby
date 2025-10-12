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
      <div className="group relative overflow-hidden rounded-2xl p-16 shadow-lg border transition-all duration-300" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="flex flex-col items-center justify-center">
          <div className="relative">
            <div className="absolute inset-0 rounded-full" style={{
              background: 'radial-gradient(circle, var(--color-primary)30, transparent)'
            }}></div>
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-t-transparent" style={{
              borderColor: 'var(--color-primary)',
              borderTopColor: 'transparent'
            }}></div>
          </div>
          <p className="mt-4 text-lg font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
            Loading summaries...
          </p>
        </div>
      </div>
    )
  }

  if (summaries.length === 0) {
    return (
      <div className="group relative overflow-hidden rounded-2xl p-16 shadow-lg border transition-all duration-300" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
        borderColor: 'var(--color-border)'
      }}>
        <div className="absolute inset-0 opacity-50" style={{
          background: 'radial-gradient(circle at center, var(--color-info)10, transparent)'
        }}></div>
        <div className="relative text-center">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl shadow-lg mb-6" style={{
            background: 'linear-gradient(135deg, var(--color-info), var(--color-primary))'
          }}>
            <FileText className="h-12 w-12 text-white" />
          </div>
          <h3 className="text-2xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
            No Summary Notes Found
          </h3>
          <p className="text-base" style={{ color: 'var(--color-text-secondary)' }}>
            AI-generated summaries will appear here as you make changes to your notes
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Bulk Action Toolbar - Modern Design */}
      {isSelectMode && selectedItems.size > 0 && (
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-xl border transition-all duration-300 animate-in fade-in slide-in-from-top-2" style={{
          background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
          borderColor: '#60a5fa'
        }}>
          <div className="absolute inset-0 opacity-50" style={{
            background: 'radial-gradient(circle at top left, #60a5fa20, transparent)'
          }}></div>
          
          <div className="relative flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 flex-1">
              <div className="flex items-center">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl shadow-lg mr-3" style={{
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)'
                }}>
                  <CheckSquare className="h-5 w-5 text-white" />
                </div>
                <div>
                  <div className="text-base font-bold text-blue-900">
                    {selectedItems.size} {selectedItems.size === 1 ? 'item' : 'items'} selected
                  </div>
                  <div className="hidden lg:block text-xs text-blue-700 mt-0.5">
                    <kbd className="px-2 py-0.5 bg-white/80 border border-blue-300 rounded text-xs font-semibold">Ctrl+A</kbd> select all · 
                    <kbd className="px-2 py-0.5 bg-white/80 border border-blue-300 rounded text-xs font-semibold ml-1">Del</kbd> delete · 
                    <kbd className="px-2 py-0.5 bg-white/80 border border-blue-300 rounded text-xs font-semibold ml-1">Esc</kbd> exit
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={onSelectAll}
                  className="relative overflow-hidden flex items-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 bg-white/80 text-blue-700 hover:bg-white border border-blue-300"
                  title={selectedItems.size === summaries.length ? "Clear selection" : "Select all on page"}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/40 to-white/0 translate-x-[-100%] hover:translate-x-[100%] transition-transform duration-700"></div>
                  <div className="relative flex items-center">
                    {selectedItems.size === summaries.length ? (
                      <>
                        <Square className="h-4 w-4 mr-2" />
                        Clear All
                      </>
                    ) : (
                      <>
                        <CheckSquare className="h-4 w-4 mr-2" />
                        Select All
                      </>
                    )}
                  </div>
                </button>
                <button
                  onClick={onClearSelection}
                  className="relative overflow-hidden flex items-center px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 bg-white/60 text-gray-700 hover:bg-white/80 border border-blue-200"
                  title="Clear selection"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/40 to-white/0 translate-x-[-100%] hover:translate-x-[100%] transition-transform duration-700"></div>
                  <span className="relative">Clear</span>
                </button>
              </div>
            </div>
            
            <button
              onClick={onBulkDelete}
              className="group/del relative overflow-hidden flex items-center px-6 py-3 text-sm font-bold rounded-xl transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl text-white border-2 border-red-700 shadow-lg" style={{
                background: 'linear-gradient(135deg, #ef4444, #dc2626)'
              }}
              title={`Delete ${selectedItems.size} selected ${selectedItems.size === 1 ? 'item' : 'items'}`}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover/del:translate-x-[100%] transition-transform duration-700"></div>
              <Trash2 className="h-5 w-5 mr-2 relative" />
              <span className="relative">Delete {selectedItems.size}</span>
            </button>
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

      {/* Pagination controls - Modern Design */}
      {pagination.total_pages > 1 && (
        <div className="group relative overflow-hidden rounded-2xl p-6 shadow-lg border transition-all duration-300" style={{
          background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
          borderColor: 'var(--color-border)'
        }}>
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
            background: 'linear-gradient(135deg, var(--color-info) 3%, var(--color-primary) 3%)'
          }}></div>
          
          <div className="relative flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Previous button */}
            <button
              onClick={() => handlePageChange(pagination.current_page - 1)}
              disabled={!pagination.has_previous}
              className="group/btn relative overflow-hidden flex items-center px-5 py-3 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0" style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)'
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></div>
              <ChevronLeft className="h-5 w-5 mr-2 relative" />
              <span className="relative">Previous</span>
            </button>

            {/* Page numbers */}
            <div className="flex items-center gap-2">
              {generatePageNumbers().map((page, index) => (
                <div key={index}>
                  {page === '...' ? (
                    <span 
                      className="px-3 py-2 text-sm font-medium"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      ···
                    </span>
                  ) : (
                    <button
                      onClick={() => handlePageChange(page as number)}
                      className={`relative overflow-hidden px-4 py-2 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 min-w-[44px] ${
                        pagination.current_page === page
                          ? 'shadow-md'
                          : ''
                      }`}
                      style={{
                        backgroundColor: pagination.current_page === page 
                          ? 'var(--color-primary)' 
                          : 'var(--color-surface)',
                        color: pagination.current_page === page 
                          ? 'var(--color-text-inverse)' 
                          : 'var(--color-text-secondary)'
                      }}
                    >
                      {pagination.current_page !== page && (
                        <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] hover:translate-x-[100%] transition-transform duration-700"></div>
                      )}
                      <span className="relative">{page}</span>
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Next button */}
            <button
              onClick={() => handlePageChange(pagination.current_page + 1)}
              disabled={!pagination.has_next}
              className="group/btn relative overflow-hidden flex items-center px-5 py-3 text-sm font-semibold rounded-xl transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0" style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)'
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></div>
              <span className="relative">Next</span>
              <ChevronRight className="h-5 w-5 ml-2 relative" />
            </button>
          </div>

          {/* Page info */}
          <div className="mt-4 pt-4 text-center text-sm" style={{ 
            color: 'var(--color-text-secondary)',
            borderTop: `1px solid var(--color-divider)`
          }}>
            <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {summaries.length}
            </span> of <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {pagination.total_count}
            </span> summaries · Page <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {pagination.current_page}
            </span> of <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {pagination.total_pages}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}