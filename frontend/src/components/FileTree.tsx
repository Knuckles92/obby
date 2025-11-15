import { useState } from 'react'
import { ChevronRight, ChevronDown, Folder, FolderOpen, FileText } from 'lucide-react'
import { FileTreeNode } from '../utils/fileOperations'

interface FileTreeProps {
  tree: FileTreeNode
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
  contextFiles: string[]
  onContextToggle?: (filePath: string, isSelected: boolean) => void
  depth?: number
}

interface TreeNodeProps {
  node: FileTreeNode
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
  contextFiles: string[]
  onContextToggle?: (filePath: string, isSelected: boolean) => void
  depth: number
}

function TreeNode({ node, onFileSelect, selectedFile, contextFiles, onContextToggle, depth }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2) // Auto-expand first 2 levels

  const isDirectory = node.type === 'directory'
  const isSelected = selectedFile === node.path || selectedFile === node.relativePath
  const hasChildren = node.children && node.children.length > 0
  const isInContext = contextFiles.includes(node.path) || contextFiles.includes(node.relativePath || '')

  const handleFileClick = (e: React.MouseEvent) => {
    if (isDirectory) {
      setIsExpanded(!isExpanded)
    } else {
      onFileSelect(node.relativePath || node.path)
    }
  }

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!isDirectory && onContextToggle) {
      const filePath = node.relativePath || node.path
      onContextToggle(filePath, !isInContext)
    }
  }

  const handleClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget || (e.target as HTMLElement).closest('.file-content')) {
      handleFileClick(e)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleFileClick(e)
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
            ? 'bg-[color-mix(in_srgb,var(--color-primary)_20%,transparent)] text-[var(--color-primary)]'
            : 'hover:bg-[var(--color-hover)] text-[var(--color-text-primary)]'
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

        {/* Checkbox for files */}
        {!isDirectory && onContextToggle && (
          <input
            type="checkbox"
            checked={isInContext}
            onChange={handleCheckboxClick}
            onClick={handleCheckboxClick}
            className="mr-2 w-3 h-3 text-blue-600 rounded border-gray-300 focus:ring-blue-500 cursor-pointer flex-shrink-0"
            title="Toggle context inclusion"
          />
        )}

        {/* File/folder icon */}
        <span className="mr-2 flex-shrink-0">
          {isDirectory ? (
            isExpanded ? (
              <FolderOpen className="h-4 w-4 text-blue-500" />
            ) : (
              <Folder className="h-4 w-4 text-blue-500" />
            )
          ) : (
            <FileText className={`h-4 w-4 ${isInContext ? 'text-blue-600' : 'text-gray-500'}`} />
          )}
        </span>

        {/* File/folder name */}
        <span className="file-content text-sm truncate flex-1" title={node.name}>
          {node.name}
        </span>

        {/* Context indicator for files */}
        {!isDirectory && isInContext && (
          <span className="ml-2 text-xs bg-[color-mix(in_srgb,var(--color-info)_20%,transparent)] text-[var(--color-info)] px-2 py-0.5 rounded flex-shrink-0">
            Context
          </span>
        )}

        {/* File count badge for directories */}
        {isDirectory && hasChildren && (
          <span className="ml-2 text-xs text-[var(--color-text-secondary)] flex-shrink-0">
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
              contextFiles={contextFiles}
              onContextToggle={onContextToggle}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function FileTree({ tree, onFileSelect, selectedFile, contextFiles = [], onContextToggle, depth = 0 }: FileTreeProps) {
  if (!tree) {
    return (
      <div className="p-4 text-center text-[var(--color-text-secondary)]">
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
        contextFiles={contextFiles}
        onContextToggle={onContextToggle}
        depth={depth}
      />
    </div>
  )
}
