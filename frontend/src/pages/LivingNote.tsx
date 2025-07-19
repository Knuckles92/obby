import { useState, useEffect } from 'react'
import { FileText, Clock, BarChart3 } from 'lucide-react'
import { LivingNote as LivingNoteType } from '../types'

export default function LivingNote() {
  const [note, setNote] = useState<LivingNoteType>({
    content: '',
    lastUpdated: '',
    wordCount: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLivingNote()
  }, [])

  const fetchLivingNote = async () => {
    try {
      const response = await fetch('/api/living-note')
      const data = await response.json()
      setNote(data)
    } catch (error) {
      console.error('Error fetching living note:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <FileText className="h-6 w-6 text-gray-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Living Note</h1>
            <p className="text-gray-600">AI-generated summary of your note changes</p>
          </div>
        </div>
        
        <button
          onClick={fetchLivingNote}
          className="btn-secondary"
        >
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-md">
              <BarChart3 className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Word Count</p>
              <p className="text-lg font-semibold text-gray-900">{note.wordCount}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-md">
              <Clock className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Last Updated</p>
              <p className="text-sm font-semibold text-gray-900">
                {note.lastUpdated ? formatDate(note.lastUpdated) : 'Never'}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-md">
              <FileText className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Status</p>
              <p className="text-sm font-semibold text-gray-900">
                {note.content ? 'Active' : 'Empty'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Note Content */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">AI Summary</h3>
        
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : note.content ? (
          <div className="prose max-w-none">
            <div className="bg-gray-50 p-6 rounded-md">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                {note.content}
              </pre>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No living note content yet</p>
            <p className="text-sm text-gray-500 mt-2">
              The AI will generate summaries as you make changes to your notes
            </p>
          </div>
        )}
      </div>
    </div>
  )
}