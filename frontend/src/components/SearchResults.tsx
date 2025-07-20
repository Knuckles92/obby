import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Clock, Star, Tag, Hash, AlertCircle, FileText, ChevronLeft, ChevronRight } from 'lucide-react'
import { SearchResult } from '../types'

interface SearchResultsProps {
  results: SearchResult[]
  total: number
  loading: boolean
  error: string | null
  query: string
  currentPage: number
  pageSize: number
  onPageChange: (offset: number) => void
  sortBy: string
}

const IMPACT_COLORS = {
  brief: 'bg-gray-100 text-gray-700 border-gray-200',
  moderate: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  significant: 'bg-red-100 text-red-700 border-red-200'
}

const IMPACT_ICONS = {
  brief: AlertCircle,
  moderate: AlertCircle,
  significant: AlertCircle
}

export default function SearchResults({
  results: rawResults,
  total,
  loading,
  error,
  query,
  currentPage,
  pageSize,
  onPageChange,
  sortBy
}: SearchResultsProps) {
  // Ensure results is always an array
  const results = Array.isArray(rawResults) ? rawResults : []
  
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())

  // Debug logging to diagnose the issue
  try {
    console.log('[SearchResults] Component rendered with:', {
      rawResultsType: rawResults === null ? 'null' : rawResults === undefined ? 'undefined' : Array.isArray(rawResults) ? 'array' : typeof rawResults,
      resultsCount: results.length,
      total,
      loading,
      error,
      hasResults: results.length > 0,
      firstResult: results.length > 0 ? results[0] : null
    })
    
    if (results.length > 0) {
      console.log('[SearchResults] First result structure:', {
        id: results[0]?.id,
        hasTopics: results[0]?.topics !== undefined,
        topicsType: Array.isArray(results[0]?.topics) ? 'array' : typeof results[0]?.topics,
        hasKeywords: results[0]?.keywords !== undefined,
        keywordsType: Array.isArray(results[0]?.keywords) ? 'array' : typeof results[0]?.keywords,
        impact: results[0]?.impact,
        relevance_score: results[0]?.relevance_score
      })
    }
  } catch (logError) {
    console.error('[SearchResults] Error in debug logging:', logError)
  }

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedResults)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedResults(newExpanded)
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const highlightText = (text: string, query: string) => {
    if (!query) return text
    
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    const parts = text.split(regex)
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 text-yellow-900 rounded px-1">
          {part}
        </mark>
      ) : part
    )
  }

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-gray-600'
  }

  const totalPages = Math.ceil(total / pageSize)
  const startIndex = currentPage * pageSize + 1
  const endIndex = Math.min((currentPage + 1) * pageSize, total)

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Searching through your notes...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600 font-medium">Search Error</p>
          <p className="text-gray-600 mt-2">{error}</p>
        </div>
      </div>
    )
  }

  if (results.length === 0) {
    return (
      <div className="card">
        <div className="text-center py-12">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">No results found</p>
          <p className="text-gray-500 mt-2">
            Try adjusting your search terms or filters to find what you're looking for
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Results Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <p className="text-gray-600">
            Showing {startIndex}-{endIndex} of {total} results
            {query && (
              <span className="ml-2">
                for "<span className="font-medium">{query}</span>"
              </span>
            )}
          </p>
          <span className="text-sm text-gray-500">
            Sorted by {sortBy === 'relevance' ? 'relevance' : sortBy.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        {results.map((result) => {
          const isExpanded = expandedResults.has(result.id)
          // Add defensive check for impact
          const safeImpact = result.impact || 'brief'
          const ImpactIcon = IMPACT_ICONS[safeImpact as keyof typeof IMPACT_ICONS] || AlertCircle
          
          return (
            <div key={result.id} className="card hover:shadow-md transition-shadow">
              <div className="space-y-4">
                {/* Result Header */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full border ${
                        IMPACT_COLORS[safeImpact as keyof typeof IMPACT_COLORS] || IMPACT_COLORS.brief
                      }`}>
                        <ImpactIcon className="h-3 w-3 mr-1" />
                        {safeImpact}
                      </span>
                      
                      <div className="flex items-center space-x-1">
                        <Star className={`h-4 w-4 ${getRelevanceColor(result.relevance_score)}`} />
                        <span className={`text-sm font-medium ${getRelevanceColor(result.relevance_score)}`}>
                          {Math.round(result.relevance_score * 100)}%
                        </span>
                      </div>
                      
                      <div className="flex items-center text-gray-500">
                        <Clock className="h-4 w-4 mr-1" />
                        <span className="text-sm">{formatDate(result.timestamp)}</span>
                      </div>
                    </div>
                    
                    <div className="prose prose-sm max-w-none">
                      <p className="text-gray-700 leading-relaxed">
                        {highlightText(result.summary, query)}
                      </p>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => toggleExpanded(result.id)}
                    className="ml-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                    aria-label={isExpanded ? 'Collapse' : 'Expand'}
                  >
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
                  </button>
                </div>

                {/* Tags Section */}
                <div className="flex flex-wrap gap-2">
                  {(result.topics || []).map((topic, index) => (
                    <span
                      key={`topic-${index}`}
                      className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-md"
                    >
                      <Tag className="h-3 w-3 mr-1" />
                      {highlightText(topic, query)}
                    </span>
                  ))}
                  
                  {(result.keywords || []).map((keyword, index) => (
                    <span
                      key={`keyword-${index}`}
                      className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-md"
                    >
                      <Hash className="h-3 w-3 mr-1" />
                      {highlightText(keyword, query)}
                    </span>
                  ))}
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="border-t border-gray-200 pt-4 mt-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-2">Full Details</h4>
                      <div className="space-y-3">
                        <div>
                          <span className="text-sm font-medium text-gray-600">Entry ID:</span>
                          <span className="ml-2 text-sm text-gray-900 font-mono">{result.id}</span>
                        </div>
                        
                        <div>
                          <span className="text-sm font-medium text-gray-600">Relevance Score:</span>
                          <span className="ml-2 text-sm text-gray-900">
                            {result.relevance_score.toFixed(3)} 
                            <span className="text-gray-500 ml-1">
                              ({Math.round(result.relevance_score * 100)}% match)
                            </span>
                          </span>
                        </div>
                        
                        <div>
                          <span className="text-sm font-medium text-gray-600">Created:</span>
                          <span className="ml-2 text-sm text-gray-900">{formatDate(result.timestamp)}</span>
                        </div>
                        
                        {(result.topics || []).length > 0 && (
                          <div>
                            <span className="text-sm font-medium text-gray-600">Related Topics:</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {(result.topics || []).map((topic, index) => (
                                <span
                                  key={index}
                                  className="inline-block px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded"
                                >
                                  {topic}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {(result.keywords || []).length > 0 && (
                          <div>
                            <span className="text-sm font-medium text-gray-600">Keywords:</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {(result.keywords || []).map((keyword, index) => (
                                <span
                                  key={index}
                                  className="inline-block px-2 py-1 text-xs bg-green-50 text-green-700 rounded"
                                >
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="card">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onPageChange((currentPage - 1) * pageSize)}
                disabled={currentPage === 0}
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </button>
              
              <span className="text-sm text-gray-700">
                Page {currentPage + 1} of {totalPages}
              </span>
              
              <button
                onClick={() => onPageChange((currentPage + 1) * pageSize)}
                disabled={currentPage >= totalPages - 1}
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </button>
            </div>
            
            <div className="text-sm text-gray-500">
              {total} total results
            </div>
          </div>
        </div>
      )}
    </div>
  )
}