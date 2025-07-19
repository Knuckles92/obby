import { useState, useEffect } from 'react'
import { FileText, Clock, BarChart3, Trash2 } from 'lucide-react'
import { LivingNote as LivingNoteType } from '../types'
import ConfirmationDialog from '../components/ConfirmationDialog'
import { apiFetch } from '../utils/api'

export default function LivingNote() {
  const [note, setNote] = useState<LivingNoteType>({
    content: '',
    lastUpdated: '',
    wordCount: 0
  })
  const [loading, setLoading] = useState(true)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)

  useEffect(() => {
    fetchLivingNote()
  }, [])

  const fetchLivingNote = async () => {
    try {
      setLoading(true)
      const response = await apiFetch('/api/living-note')
      const data = await response.json()
      setNote(data)
    } catch (error) {
      console.error('Error fetching living note:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClearNote = async () => {
    try {
      setClearLoading(true)
      const response = await apiFetch('/api/living-note/clear', {
        method: 'POST'
      })
      
      if (response.ok) {
        const result = await response.json()
        console.log(result.message)
        // Refresh the note content
        await fetchLivingNote()
        setClearDialogOpen(false)
      } else {
        const error = await response.json()
        console.error('Error clearing living note:', error.error)
        alert('Failed to clear living note: ' + error.error)
      }
    } catch (error) {
      console.error('Error clearing living note:', error)
      alert('Failed to clear living note. Please try again.')
    } finally {
      setClearLoading(false)
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
        
        <div className="flex space-x-3">
          <button
            onClick={fetchLivingNote}
            disabled={loading}
            className="btn-secondary flex items-center"
          >
            {loading && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
            )}
            Refresh
          </button>
          
          {note.content && (
            <button
              onClick={() => setClearDialogOpen(true)}
              className="flex items-center px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Clear Note
            </button>
          )}
        </div>
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

      {/* Clear Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={clearDialogOpen}
        onClose={() => setClearDialogOpen(false)}
        onConfirm={handleClearNote}
        title="Clear Living Note"
        message="Are you sure you want to clear the living note? This will permanently delete all AI-generated content."
        confirmText="Clear Note"
        cancelText="Cancel"
        danger={true}
        loading={clearLoading}
        extraWarning="This action cannot be undone. A backup will be created automatically."
      />
    </div>
  )
}