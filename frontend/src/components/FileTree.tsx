import { useState } from 'react'
import { ChevronRight, ChevronDown, Folder, FolderOpen, FileText } from 'lucide-react'
import { FileTreeNode } from '../utils/fileOperations'

interface FileTreeProps {
  tree: FileTreeNode
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
  depth?: number
}

interface TreeNodeProps {
  node: FileTreeNode
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
  depth: number
}

function TreeNode({ node, onFileSelect, selectedFile, depth }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2) // Auto-expand first 2 levels

  const isDirectory = node.type === 'directory'
  const isSelected = selectedFile === node.path || selectedFile === node.relativePath
  const hasChildren = node.children && node.children.length > 0

  const handleClick = () => {
    if (isDirectory) {
      setIsExpanded(!isExpanded)
    } else {
      onFileSelect(node.relativePath || node.path)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    } else if (isDirectory && hasChildren) {
      if (e.key === 'ArrowRight' && !isExpanded) {
        e.preventDefault()
        setIsExpanded(true)
      } else if (e.key === 'ArrowLeft' && isExpanded) {
        e.preventDefault()
        setIsExpanded(false)
      }
    }
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={`
          flex items-center px-2 py-1.5 cursor-pointer rounded-md group
          transition-colors duration-150
          ${isSelected
            ? 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100'
            : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
          }
        `}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {/* Expand/collapse icon for directories */}
        {isDirectory && hasChildren && (
          <span className="mr-1 flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-500" />
            )}
          </span>
        )}

        {/* Spacer for files or empty directories */}
        {(!isDirectory || !hasChildren) && <span className="w-5 flex-shrink-0" />}

        {/* File/folder icon */}
        <span className="mr-2 flex-shrink-0">
          {isDirectory ? (
            isExpanded ? (
              <FolderOpen className="h-4 w-4 text-blue-500" />
            ) : (
              <Folder className="h-4 w-4 text-blue-500" />
            )
          ) : (
            <FileText className="h-4 w-4 text-gray-500" />
          )}
        </span>

        {/* File/folder name */}
        <span className="text-sm truncate flex-1" title={node.name}>
          {node.name}
        </span>

        {/* File count badge for directories */}
        {isDirectory && hasChildren && (
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
            {node.childCount || node.children?.length}
          </span>
        )}
      </div>

      {/* Render children if expanded */}
      {isDirectory && isExpanded && hasChildren && (
        <div>
          {node.children!.map((child, index) => (
            <TreeNode
              key={`${child.path}-${index}`}
              node={child}
              onFileSelect={onFileSelect}
              selectedFile={selectedFile}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function FileTree({ tree, onFileSelect, selectedFile, depth = 0 }: FileTreeProps) {
  if (!tree) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-400">
        <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No files found</p>
      </div>
    )
  }

  return (
    <div className="overflow-auto h-full">
      <TreeNode
        node={tree}
        onFileSelect={onFileSelect}
        selectedFile={selectedFile}
        depth={depth}
      />
    </div>
  )
}
