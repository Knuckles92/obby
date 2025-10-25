import { useState, useEffect, useCallback, useRef } from 'react'
import { Eye, Edit3, Save, Loader2, AlertCircle, FileText, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { fetchFileContent, saveFileContent, formatFileDate } from '../utils/fileOperations'

interface NoteEditorProps {
  filePath: string | null
  onClose?: () => void
  onSave?: (filePath: string) => void
}

type EditorMode = 'preview' | 'edit'

export default function NoteEditor({ filePath, onClose, onSave }: NoteEditorProps) {
  const [mode, setMode] = useState<EditorMode>('preview')
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [fileName, setFileName] = useState('')
  const [lastModified, setLastModified] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Derived state
  const isDirty = content !== originalContent
  const hasUnsavedChanges = isDirty && mode === 'edit'

  // Load file content when filePath changes
  useEffect(() => {
    if (!filePath) {
      setContent('')
      setOriginalContent('')
      setFileName('')
      setLastModified(null)
      setError(null)
      return
    }

    const loadFile = async () => {
      setLoading(true)
      setError(null)

      try {
        const fileData = await fetchFileContent(filePath)
        setContent(fileData.content)
        setOriginalContent(fileData.content)
        setFileName(fileData.name)
        setLastModified(fileData.lastModified)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load file')
        setContent('')
        setOriginalContent('')
      } finally {
        setLoading(false)
      }
    }

    loadFile()
  }, [filePath])

  // Handle save
  const handleSave = useCallback(async () => {
    if (!filePath || !isDirty) return

    setSaving(true)
    setError(null)
    setSaveSuccess(false)

    try {
      const result = await saveFileContent(filePath, content, true)
      setOriginalContent(content)
      setLastModified(result.lastModified)
      setSaveSuccess(true)

      // Call onSave callback
      if (onSave) {
        onSave(filePath)
      }

      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save file')
    } finally {
      setSaving(false)
    }
  }, [filePath, content, isDirty, onSave])

  // Handle mode toggle
  const handleModeToggle = useCallback(() => {
    setMode(prevMode => prevMode === 'preview' ? 'edit' : 'preview')
  }, [])

  // Focus textarea when switching to edit mode
  useEffect(() => {
    if (mode === 'edit' && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [mode])

  // Custom markdown components for syntax highlighting
  const components = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '')
      return !inline && match ? (
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      )
    }
  }

  // Empty state
  if (!filePath) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
        <FileText className="h-16 w-16 mb-4 opacity-50" />
        <p className="text-lg font-medium">No file selected</p>
        <p className="text-sm mt-2">Select a file from the sidebar to view or edit</p>
      </div>
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm text-gray-500">Loading file...</p>
      </div>
    )
  }

  // Error state
  if (error && !content) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-lg font-medium text-gray-900 dark:text-gray-100">Failed to load file</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">{error}</p>
        {onClose && (
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Close
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="px-6 py-4">
          {/* File info */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
                {fileName}
              </h2>
              {lastModified && (
                <div className="flex items-center mt-1 text-sm text-gray-500 dark:text-gray-400">
                  <Clock className="h-3.5 w-3.5 mr-1" />
                  <span>Modified {formatFileDate(lastModified)}</span>
                </div>
              )}
            </div>

            {/* Unsaved indicator */}
            {isDirty && (
              <div className="ml-4 px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full">
                Unsaved changes
              </div>
            )}
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {/* Mode toggle */}
              <button
                onClick={handleModeToggle}
                className={`
                  flex items-center px-3 py-1.5 rounded-md text-sm font-medium
                  transition-colors duration-150
                  ${mode === 'preview'
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-100'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }
                `}
              >
                {mode === 'preview' ? (
                  <>
                    <Eye className="h-4 w-4 mr-1.5" />
                    Preview
                  </>
                ) : (
                  <>
                    <Edit3 className="h-4 w-4 mr-1.5" />
                    Edit
                  </>
                )}
              </button>
            </div>

            {/* Save button */}
            <div className="flex items-center space-x-2">
              {saveSuccess && (
                <span className="text-sm text-green-600 dark:text-green-400 font-medium">
                  Saved!
                </span>
              )}
              {error && content && (
                <span className="text-sm text-red-600 dark:text-red-400">
                  {error}
                </span>
              )}
              <button
                onClick={handleSave}
                disabled={!isDirty || saving}
                className={`
                  flex items-center px-4 py-2 rounded-md text-sm font-medium
                  transition-colors duration-150
                  ${isDirty && !saving
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-1.5" />
                    Save
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto">
        {mode === 'edit' ? (
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-full p-6 font-mono text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 resize-none focus:outline-none"
            spellCheck={false}
            placeholder="Start writing..."
          />
        ) : (
          <div className="prose prose-sm sm:prose lg:prose-lg dark:prose-invert max-w-none p-6">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
              {content || '*No content*'}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
