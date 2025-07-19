import { useState, useEffect } from 'react'
import { FolderTree, File, Folder } from 'lucide-react'
import { apiFetch } from '../utils/api'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
}

export default function FileExplorer() {
  const [fileTree, setFileTree] = useState<FileNode | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFileTree()
  }, [])

  const fetchFileTree = async () => {
    try {
      const response = await apiFetch('/api/files/tree')
      const data = await response.json()
      setFileTree(data)
    } catch (error) {
      console.error('Error fetching file tree:', error)
    } finally {
      setLoading(false)
    }
  }

  const renderNode = (node: FileNode, depth = 0) => (
    <div key={node.path} className={`ml-${depth * 4}`}>
      <div className="flex items-center p-2 hover:bg-gray-50 rounded-md cursor-pointer">
        {node.type === 'directory' ? (
          <Folder className="h-4 w-4 text-blue-500 mr-2" />
        ) : (
          <File className="h-4 w-4 text-gray-500 mr-2" />
        )}
        <span className="text-sm text-gray-700">{node.name}</span>
      </div>
      {node.children && (
        <div className="ml-4">
          {node.children.map(child => renderNode(child, depth + 1))}
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <FolderTree className="h-6 w-6 text-gray-600 mr-3" />
        <h1 className="text-2xl font-bold text-gray-900">File Explorer</h1>
      </div>

      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : fileTree ? (
          renderNode(fileTree)
        ) : (
          <p className="text-gray-600 text-center py-8">No files found</p>
        )}
      </div>
    </div>
  )
}