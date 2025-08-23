import { useState, useEffect } from 'react'
import { Search, Filter, X, Calendar, SortAsc } from 'lucide-react'
import { SummarySearchFilters } from '../types'

interface SearchFiltersProps {
  filters: SummarySearchFilters
  onFiltersChange: (filters: SummarySearchFilters) => void
  isExpanded?: boolean
  onToggleExpanded?: () => void
}

export default function SearchFilters({ 
  filters, 
  onFiltersChange, 
  isExpanded = false, 
  onToggleExpanded 
}: SearchFiltersProps) {
  const [localSearchTerm, setLocalSearchTerm] = useState(filters.searchTerm)
  const [showDateRange, setShowDateRange] = useState(false)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearchTerm !== filters.searchTerm) {
        onFiltersChange({ ...filters, searchTerm: localSearchTerm })
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [localSearchTerm, filters, onFiltersChange])

  const handleSortChange = (sortBy: 'newest' | 'oldest' | 'word_count') => {
    onFiltersChange({ ...filters, sortBy })
  }

  const handleDateRangeChange = (field: 'start' | 'end', value: string) => {
    const dateRange = filters.dateRange || { start: '', end: '' }
    onFiltersChange({
      ...filters,
      dateRange: { ...dateRange, [field]: value }
    })
  }

  const clearDateRange = () => {
    onFiltersChange({ ...filters, dateRange: undefined })
    setShowDateRange(false)
  }

  const clearAllFilters = () => {
    setLocalSearchTerm('')
    onFiltersChange({
      searchTerm: '',
      sortBy: 'newest',
      dateRange: undefined
    })
    setShowDateRange(false)
  }

  const hasActiveFilters = filters.searchTerm || filters.dateRange || filters.sortBy !== 'newest'

  return (
    <div className="card">
      {/* Main search bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center space-y-3 sm:space-y-0 sm:space-x-3 mb-4">
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search summaries by full content, topics, and keywords..."
            value={localSearchTerm}
            onChange={(e) => setLocalSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            style={{
              borderColor: 'var(--color-border)',
              borderRadius: 'var(--border-radius-md)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-primary)',
              backgroundColor: 'var(--color-background)',
              transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-primary)'
              e.currentTarget.style.boxShadow = '0 0 0 2px var(--color-primary)25'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-border)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          />
          {localSearchTerm && (
            <button
              onClick={() => setLocalSearchTerm('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
            >
              <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
            </button>
          )}
        </div>

        {/* Filter toggle button */}
        <div className="flex items-center space-x-2">
        <button
          onClick={onToggleExpanded}
          className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
            isExpanded || hasActiveFilters
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
          style={{
            backgroundColor: isExpanded || hasActiveFilters ? 'var(--color-primary)15' : 'var(--color-surface)',
            color: isExpanded || hasActiveFilters ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            borderRadius: 'var(--border-radius-md)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-medium)',
            transition: 'all 0.2s ease'
          }}
        >
          <Filter className="h-4 w-4 mr-1" />
          Filters
          {hasActiveFilters && (
            <span 
              className="ml-1 px-1.5 py-0.5 text-xs bg-blue-600 text-white rounded-full"
              style={{
                backgroundColor: 'var(--color-primary)',
                color: 'var(--color-text-inverse)',
                fontSize: 'var(--font-size-xs)',
                borderRadius: 'var(--border-radius-full)'
              }}
            >
              !
            </span>
          )}
        </button>

        {/* Clear all filters button */}
        {hasActiveFilters && (
          <button
            onClick={clearAllFilters}
            className="flex items-center px-3 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200 transition-colors"
            style={{
              backgroundColor: 'var(--color-error)15',
              color: 'var(--color-error)',
              borderRadius: 'var(--border-radius-md)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-medium)',
              transition: 'background-color 0.2s ease'
            }}
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </button>
        )}
        </div>
      </div>

      {/* Expanded filter options */}
      {isExpanded && (
        <div className="border-t pt-4 space-y-4" style={{ borderColor: 'var(--color-border)' }}>
          {/* Sort options */}
          <div>
            <label 
              className="block text-sm font-medium text-gray-700 mb-2"
              style={{ 
                color: 'var(--color-text-primary)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 'var(--font-weight-medium)'
              }}
            >
              <SortAsc className="h-4 w-4 inline mr-1" />
              Sort by
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                { value: 'newest', label: 'Newest First' },
                { value: 'oldest', label: 'Oldest First' },
                { value: 'word_count', label: 'Word Count' }
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleSortChange(option.value as any)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    filters.sortBy === option.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  style={{
                    backgroundColor: filters.sortBy === option.value 
                      ? 'var(--color-primary)' 
                      : 'var(--color-surface)',
                    color: filters.sortBy === option.value 
                      ? 'var(--color-text-inverse)' 
                      : 'var(--color-text-secondary)',
                    borderRadius: 'var(--border-radius-md)',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-medium)',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label 
                className="block text-sm font-medium text-gray-700"
                style={{ 
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 'var(--font-weight-medium)'
                }}
              >
                <Calendar className="h-4 w-4 inline mr-1" />
                Date Range
              </label>
              <button
                onClick={() => setShowDateRange(!showDateRange)}
                className="text-sm text-blue-600 hover:text-blue-800"
                style={{ 
                  color: 'var(--color-primary)',
                  fontSize: 'var(--font-size-sm)'
                }}
              >
                {showDateRange ? 'Hide' : 'Show'}
              </button>
            </div>
            
            {showDateRange && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">From</label>
                  <input
                    type="date"
                    value={filters.dateRange?.start || ''}
                    onChange={(e) => handleDateRangeChange('start', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    style={{
                      borderColor: 'var(--color-border)',
                      borderRadius: 'var(--border-radius-md)',
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-text-primary)',
                      backgroundColor: 'var(--color-background)'
                    }}
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">To</label>
                  <input
                    type="date"
                    value={filters.dateRange?.end || ''}
                    onChange={(e) => handleDateRangeChange('end', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    style={{
                      borderColor: 'var(--color-border)',
                      borderRadius: 'var(--border-radius-md)',
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-text-primary)',
                      backgroundColor: 'var(--color-background)'
                    }}
                  />
                </div>
              </div>
            )}
            
            {filters.dateRange && (
              <button
                onClick={clearDateRange}
                className="mt-2 text-sm text-red-600 hover:text-red-800"
                style={{ 
                  color: 'var(--color-error)',
                  fontSize: 'var(--font-size-sm)'
                }}
              >
                Clear date range
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}