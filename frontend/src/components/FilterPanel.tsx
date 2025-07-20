import React, { useState, useEffect } from 'react'
import { Calendar, Trash2, Plus, X, Sliders, Tag, Hash } from 'lucide-react'
import { SearchFilters } from '../types'

interface FilterPanelProps {
  filters: SearchFilters
  availableTopics: Record<string, number>
  availableKeywords: Record<string, number>
  onFilterChange: (filters: Partial<SearchFilters>) => void
  onClearFilters: () => void
}

const IMPACT_LEVELS = [
  { value: 'brief', label: 'Brief', description: 'Minor updates or small changes' },
  { value: 'moderate', label: 'Moderate', description: 'Notable changes with some significance' },
  { value: 'significant', label: 'Significant', description: 'Major updates or important changes' }
]

export default function FilterPanel({
  filters,
  availableTopics,
  availableKeywords,
  onFilterChange,
  onClearFilters
}: FilterPanelProps) {
  const [topicSearch, setTopicSearch] = useState('')
  const [keywordSearch, setKeywordSearch] = useState('')
  const [showAllTopics, setShowAllTopics] = useState(false)
  const [showAllKeywords, setShowAllKeywords] = useState(false)

  // Filter and sort available options
  const filteredTopics = Object.entries(availableTopics)
    .filter(([topic]) => topic.toLowerCase().includes(topicSearch.toLowerCase()))
    .sort(([, a], [, b]) => b - a)
    .slice(0, showAllTopics ? undefined : 10)

  const filteredKeywords = Object.entries(availableKeywords)
    .filter(([keyword]) => keyword.toLowerCase().includes(keywordSearch.toLowerCase()))
    .sort(([, a], [, b]) => b - a)
    .slice(0, showAllKeywords ? undefined : 10)

  const handleTopicToggle = (topic: string) => {
    const currentTopics = filters.topics || []
    const newTopics = currentTopics.includes(topic)
      ? currentTopics.filter(t => t !== topic)
      : [...currentTopics, topic]
    
    onFilterChange({ topics: newTopics })
  }

  const handleKeywordToggle = (keyword: string) => {
    const currentKeywords = filters.keywords || []
    const newKeywords = currentKeywords.includes(keyword)
      ? currentKeywords.filter(k => k !== keyword)
      : [...currentKeywords, keyword]
    
    onFilterChange({ keywords: newKeywords })
  }

  const handleDateFromChange = (date: string) => {
    onFilterChange({ dateFrom: date })
  }

  const handleDateToChange = (date: string) => {
    onFilterChange({ dateTo: date })
  }

  const handleRelevanceChange = (relevance: number) => {
    onFilterChange({ minRelevance: relevance })
  }

  const getFilterCount = () => {
    let count = 0
    if (filters.topics?.length) count += filters.topics.length
    if (filters.keywords?.length) count += filters.keywords.length
    if (filters.dateFrom || filters.dateTo) count += 1
    if (filters.minRelevance && filters.minRelevance > 0) count += 1
    return count
  }

  return (
    <div className="card bg-gray-50 border-2 border-dashed border-gray-300">
      <div className="space-y-6">
        {/* Filter Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Sliders className="h-5 w-5 text-gray-600 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Advanced Filters</h3>
            {getFilterCount() > 0 && (
              <span className="ml-2 inline-flex items-center justify-center w-6 h-6 text-xs font-medium text-white bg-primary-600 rounded-full">
                {getFilterCount()}
              </span>
            )}
          </div>
          
          <button
            onClick={onClearFilters}
            className="flex items-center px-3 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Clear All
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Topics Filter */}
          <div className="space-y-3">
            <div className="flex items-center">
              <Tag className="h-4 w-4 text-blue-600 mr-2" />
              <label className="block text-sm font-medium text-gray-700">
                Topics ({Object.keys(availableTopics).length} available)
              </label>
            </div>
            
            <input
              type="text"
              placeholder="Search topics..."
              value={topicSearch}
              onChange={(e) => setTopicSearch(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            
            <div className="max-h-48 overflow-y-auto space-y-2">
              {filteredTopics.map(([topic, count]) => (
                <label
                  key={topic}
                  className="flex items-center p-2 hover:bg-gray-100 rounded-md cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.topics?.includes(topic) || false}
                    onChange={() => handleTopicToggle(topic)}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="ml-3 text-sm text-gray-700 flex-1">{topic}</span>
                  <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded-full">
                    {count}
                  </span>
                </label>
              ))}
              
              {Object.keys(availableTopics).length > 10 && !showAllTopics && (
                <button
                  onClick={() => setShowAllTopics(true)}
                  className="w-full text-sm text-primary-600 hover:text-primary-800 py-2"
                >
                  Show all {Object.keys(availableTopics).length} topics
                </button>
              )}
            </div>
            
            {filters.topics && filters.topics.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Selected topics:</p>
                <div className="flex flex-wrap gap-1">
                  {filters.topics.map(topic => (
                    <span
                      key={topic}
                      className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-md"
                    >
                      {topic}
                      <button
                        onClick={() => handleTopicToggle(topic)}
                        className="ml-1 text-blue-500 hover:text-blue-700"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Keywords Filter */}
          <div className="space-y-3">
            <div className="flex items-center">
              <Hash className="h-4 w-4 text-green-600 mr-2" />
              <label className="block text-sm font-medium text-gray-700">
                Keywords ({Object.keys(availableKeywords).length} available)
              </label>
            </div>
            
            <input
              type="text"
              placeholder="Search keywords..."
              value={keywordSearch}
              onChange={(e) => setKeywordSearch(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            
            <div className="max-h-48 overflow-y-auto space-y-2">
              {filteredKeywords.map(([keyword, count]) => (
                <label
                  key={keyword}
                  className="flex items-center p-2 hover:bg-gray-100 rounded-md cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.keywords?.includes(keyword) || false}
                    onChange={() => handleKeywordToggle(keyword)}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="ml-3 text-sm text-gray-700 flex-1">{keyword}</span>
                  <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded-full">
                    {count}
                  </span>
                </label>
              ))}
              
              {Object.keys(availableKeywords).length > 10 && !showAllKeywords && (
                <button
                  onClick={() => setShowAllKeywords(true)}
                  className="w-full text-sm text-primary-600 hover:text-primary-800 py-2"
                >
                  Show all {Object.keys(availableKeywords).length} keywords
                </button>
              )}
            </div>
            
            {filters.keywords && filters.keywords.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Selected keywords:</p>
                <div className="flex flex-wrap gap-1">
                  {filters.keywords.map(keyword => (
                    <span
                      key={keyword}
                      className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-700 rounded-md"
                    >
                      {keyword}
                      <button
                        onClick={() => handleKeywordToggle(keyword)}
                        className="ml-1 text-green-500 hover:text-green-700"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Date Range and Relevance Filters */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Date Range Filter */}
          <div className="space-y-3">
            <div className="flex items-center">
              <Calendar className="h-4 w-4 text-purple-600 mr-2" />
              <label className="block text-sm font-medium text-gray-700">Date Range</label>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">From</label>
                <input
                  type="date"
                  value={filters.dateFrom || ''}
                  onChange={(e) => handleDateFromChange(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">To</label>
                <input
                  type="date"
                  value={filters.dateTo || ''}
                  onChange={(e) => handleDateToChange(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
            
            {(filters.dateFrom || filters.dateTo) && (
              <button
                onClick={() => onFilterChange({ dateFrom: '', dateTo: '' })}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Clear date range
              </button>
            )}
          </div>

          {/* Relevance Filter */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Minimum Relevance Score
            </label>
            
            <div className="space-y-2">
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={filters.minRelevance || 0}
                onChange={(e) => handleRelevanceChange(parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              
              <div className="flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span className="font-medium text-gray-700">
                  {Math.round((filters.minRelevance || 0) * 100)}%
                </span>
                <span>100%</span>
              </div>
              
              <p className="text-xs text-gray-500">
                Only show results with at least {Math.round((filters.minRelevance || 0) * 100)}% relevance
              </p>
            </div>
            
            {filters.minRelevance && filters.minRelevance > 0 && (
              <button
                onClick={() => handleRelevanceChange(0)}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Reset relevance filter
              </button>
            )}
          </div>
        </div>

        {/* Impact Level Filter */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">Impact Level</label>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {IMPACT_LEVELS.map(level => (
              <label
                key={level.value}
                className="flex items-start p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={filters.impact?.includes(level.value) || false}
                  onChange={(e) => {
                    const currentImpacts = filters.impact || []
                    const newImpacts = e.target.checked
                      ? [...currentImpacts, level.value]
                      : currentImpacts.filter(i => i !== level.value)
                    
                    onFilterChange({ impact: newImpacts })
                  }}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded mt-0.5"
                />
                <div className="ml-3">
                  <div className="text-sm font-medium text-gray-900">{level.label}</div>
                  <div className="text-xs text-gray-500">{level.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}