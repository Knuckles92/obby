import { useState, useEffect } from 'react'
import { Search as SearchIcon, Database, TrendingUp, Tag, Calendar } from 'lucide-react'
import Search from '../components/Search'
import { SemanticMetadata } from '../types'
import { getTopics, getKeywords } from '../utils/api'

export default function SearchPage() {
  const [metadata, setMetadata] = useState<SemanticMetadata>({
    topics: {},
    keywords: {},
    totalEntries: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetadata()
  }, [])

  const fetchMetadata = async () => {
    try {
      setLoading(true)
      const [topicsData, keywordsData] = await Promise.all([
        getTopics(),
        getKeywords()
      ])

      setMetadata({
        topics: topicsData.topics?.reduce((acc: Record<string, number>, topic: string) => {
          acc[topic] = 1
          return acc
        }, {}) || {},
        keywords: keywordsData.keywords?.reduce((acc: Record<string, number>, keyword: any) => {
          acc[keyword.keyword || keyword] = keyword.count || 1
          return acc
        }, {}) || {},
        totalEntries: topicsData.total || 0
      })
    } catch (error) {
      console.error('Error fetching search metadata:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <SearchIcon className="h-6 w-6 text-gray-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Semantic Search</h1>
            <p className="text-gray-600">Search through your structured living notes</p>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-md">
                <Database className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Entries</p>
                <p className="text-lg font-semibold text-gray-900">{metadata.totalEntries}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-md">
                <Tag className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Topics</p>
                <p className="text-lg font-semibold text-gray-900">{Object.keys(metadata.topics).length}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-md">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Keywords</p>
                <p className="text-lg font-semibold text-gray-900">{Object.keys(metadata.keywords).length}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="p-2 bg-orange-100 rounded-md">
                <Calendar className="h-6 w-6 text-orange-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Searchable</p>
                <p className="text-lg font-semibold text-gray-900">Ready</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search Interface */}
      <div className="space-y-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <Search />
        )}
      </div>

      {/* Help Section */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Search Tips</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-gray-600">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Search Syntax</h4>
            <ul className="space-y-1">
              <li><code className="bg-gray-100 px-2 py-1 rounded">topic:name</code> - Search by specific topic</li>
              <li><code className="bg-gray-100 px-2 py-1 rounded">keyword:term</code> - Search by specific keyword</li>
              <li><code className="bg-gray-100 px-2 py-1 rounded">impact:significant</code> - Filter by impact level</li>
              <li><code className="bg-gray-100 px-2 py-1 rounded">"exact phrase"</code> - Search for exact phrases</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Filter Options</h4>
            <ul className="space-y-1">
              <li>• Use topic and keyword chips for quick filtering</li>
              <li>• Date range picker for time-based searches</li>
              <li>• Impact level filters for importance-based results</li>
              <li>• Sort by relevance, newest, or oldest</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}