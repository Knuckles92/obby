import React, { useState, useEffect, useCallback } from 'react'
import { Search as SearchIcon, X, Calendar, Filter, SortAsc, SortDesc } from 'lucide-react'
import { SearchFilters, SearchResult, SemanticMetadata } from '../types'
import { searchSemanticIndex, getTopics, getKeywords } from '../utils/api'
import SearchResults from './SearchResults'
import FilterPanel from './FilterPanel'

interface SearchProps {
  className?: string
}

const IMPACT_LEVELS = [
  { value: 'brief', label: 'Brief', color: 'bg-gray-100 text-gray-700' },
  { value: 'moderate', label: 'Moderate', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'significant', label: 'Significant', color: 'bg-red-100 text-red-700' }
]

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance', icon: SortDesc },
  { value: 'date_desc', label: 'Newest First', icon: SortDesc },
  { value: 'date_asc', label: 'Oldest First', icon: SortAsc }
]

export default function Search({ className = '' }: SearchProps) {
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    topics: [],
    keywords: [],
    dateFrom: '',
    dateTo: '',
    minRelevance: 0,
    limit: 20,
    offset: 0
  })
  
  const [results, setResults] = useState<SearchResult[]>([])
  const [metadata, setMetadata] = useState<SemanticMetadata | null>(null)
  const [totalResults, setTotalResults] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [sortBy, setSortBy] = useState('relevance')
  const [availableTopics, setAvailableTopics] = useState<Record<string, number>>({})
  const [availableKeywords, setAvailableKeywords] = useState<Record<string, number>>({})

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchFilters: SearchFilters) => {
      try {
        setLoading(true)
        setError(null)
        
        const response = await searchSemanticIndex(searchFilters)
        setResults(response.results)
        setTotalResults(response.total)
        setMetadata(response.metadata)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred while searching')
        setResults([])
        setTotalResults(0)
      } finally {
        setLoading(false)
      }
    }, 300),
    []
  )

  // Load available topics and keywords on component mount
  useEffect(() => {
    const loadFilterOptions = async () => {
      try {
        const [topics, keywords] = await Promise.all([
          getTopics(),
          getKeywords()
        ])
        setAvailableTopics(topics)
        setAvailableKeywords(keywords)
      } catch (err) {
        console.error('Failed to load filter options:', err)
      }
    }
    
    loadFilterOptions()
  }, [])

  // Trigger search when filters change
  useEffect(() => {
    const searchFilters = { ...filters }
    
    // Apply sorting logic
    if (sortBy === 'date_desc' || sortBy === 'date_asc') {
      // Server should handle date sorting
      searchFilters.sortBy = sortBy
    }
    
    debouncedSearch(searchFilters)
  }, [filters, sortBy, debouncedSearch])

  // Load filters from URL parameters on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const newFilters: SearchFilters = { ...filters }
    
    if (urlParams.has('q')) newFilters.query = urlParams.get('q') || ''
    if (urlParams.has('topics')) newFilters.topics = urlParams.get('topics')?.split(',') || []
    if (urlParams.has('keywords')) newFilters.keywords = urlParams.get('keywords')?.split(',') || []
    if (urlParams.has('dateFrom')) newFilters.dateFrom = urlParams.get('dateFrom') || ''
    if (urlParams.has('dateTo')) newFilters.dateTo = urlParams.get('dateTo') || ''
    if (urlParams.has('sort')) setSortBy(urlParams.get('sort') || 'relevance')
    
    setFilters(newFilters)
  }, [])

  // Update URL parameters when filters change
  useEffect(() => {
    const urlParams = new URLSearchParams()
    
    if (filters.query) urlParams.set('q', filters.query)
    if (filters.topics?.length) urlParams.set('topics', filters.topics.join(','))
    if (filters.keywords?.length) urlParams.set('keywords', filters.keywords.join(','))
    if (filters.dateFrom) urlParams.set('dateFrom', filters.dateFrom)
    if (filters.dateTo) urlParams.set('dateTo', filters.dateTo)
    if (sortBy !== 'relevance') urlParams.set('sort', sortBy)
    
    const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : window.location.pathname
    window.history.replaceState({}, '', newUrl)
  }, [filters, sortBy])

  const handleQueryChange = (query: string) => {
    setFilters(prev => ({ ...prev, query, offset: 0 }))
  }

  const handleFilterChange = (newFilters: Partial<SearchFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters, offset: 0 }))
  }

  const handleClearFilters = () => {
    setFilters({
      query: '',
      topics: [],
      keywords: [],
      dateFrom: '',
      dateTo: '',
      minRelevance: 0,
      limit: 20,
      offset: 0
    })
    setSortBy('relevance')
  }

  const handlePageChange = (offset: number) => {
    setFilters(prev => ({ ...prev, offset }))
  }

  const removeFilter = (type: string, value: string) => {
    if (type === 'topic') {
      setFilters(prev => ({
        ...prev,
        topics: prev.topics?.filter(t => t !== value) || []
      }))
    } else if (type === 'keyword') {
      setFilters(prev => ({
        ...prev,
        keywords: prev.keywords?.filter(k => k !== value) || []
      }))
    }
  }

  const hasActiveFilters = filters.query || 
    (filters.topics && filters.topics.length > 0) || 
    (filters.keywords && filters.keywords.length > 0) || 
    filters.dateFrom || 
    filters.dateTo ||
    filters.minRelevance > 0

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Search Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <SearchIcon className="h-6 w-6 text-gray-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Semantic Search</h1>
            <p className="text-gray-600">Search through your living notes with AI-powered understanding</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              showFilters 
                ? 'bg-primary-100 text-primary-700' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
            {hasActiveFilters && (
              <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-white bg-primary-600 rounded-full">
                {(filters.topics?.length || 0) + (filters.keywords?.length || 0) + (filters.query ? 1 : 0)}
              </span>
            )}
          </button>
          
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            {SORT_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Search Input */}
      <div className="card">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search for topics, keywords, or specific content..."
            value={filters.query || ''}
            onChange={(e) => handleQueryChange(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-lg"
          />
          {filters.query && (
            <button
              onClick={() => handleQueryChange('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Active Filter Chips */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm font-medium text-gray-700">Active filters:</span>
          
          {filters.topics?.map(topic => (
            <div
              key={topic}
              className="inline-flex items-center px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full"
            >
              <span className="mr-1">Topic:</span>
              {topic}
              <button
                onClick={() => removeFilter('topic', topic)}
                className="ml-2 text-blue-500 hover:text-blue-700"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          
          {filters.keywords?.map(keyword => (
            <div
              key={keyword}
              className="inline-flex items-center px-3 py-1 text-sm bg-green-100 text-green-700 rounded-full"
            >
              <span className="mr-1">Keyword:</span>
              {keyword}
              <button
                onClick={() => removeFilter('keyword', keyword)}
                className="ml-2 text-green-500 hover:text-green-700"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
          
          {(filters.dateFrom || filters.dateTo) && (
            <div className="inline-flex items-center px-3 py-1 text-sm bg-purple-100 text-purple-700 rounded-full">
              <Calendar className="h-3 w-3 mr-1" />
              {filters.dateFrom && filters.dateTo 
                ? `${filters.dateFrom} to ${filters.dateTo}`
                : filters.dateFrom 
                  ? `From ${filters.dateFrom}`
                  : `Until ${filters.dateTo}`
              }
              <button
                onClick={() => handleFilterChange({ dateFrom: '', dateTo: '' })}
                className="ml-2 text-purple-500 hover:text-purple-700"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          
          <button
            onClick={handleClearFilters}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Filter Panel */}
      {showFilters && (
        <FilterPanel
          filters={filters}
          availableTopics={availableTopics}
          availableKeywords={availableKeywords}
          onFilterChange={handleFilterChange}
          onClearFilters={handleClearFilters}
        />
      )}

      {/* Search Results */}
      <SearchResults
        results={results}
        total={totalResults}
        loading={loading}
        error={error}
        query={filters.query || ''}
        currentPage={Math.floor((filters.offset || 0) / (filters.limit || 20))}
        pageSize={filters.limit || 20}
        onPageChange={handlePageChange}
        sortBy={sortBy}
      />

      {/* Search Metadata */}
      {metadata && !loading && (
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Search Statistics</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Entries</p>
              <p className="text-2xl font-semibold text-gray-900">{metadata.totalEntries}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Unique Topics</p>
              <p className="text-2xl font-semibold text-gray-900">{Object.keys(metadata.topics).length}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Unique Keywords</p>
              <p className="text-2xl font-semibold text-gray-900">{Object.keys(metadata.keywords).length}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Utility function for debouncing
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}