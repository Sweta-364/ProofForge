import { useState } from 'react'
import { ChevronRight, ChevronDown, FileCode, Folder, FolderOpen } from 'lucide-react'

interface TreeNode {
  type: 'file' | 'folder'
  name: string
  path: string
  children: TreeNode[]
}

function buildTree(files: Map<string, string>): TreeNode[] {
  const root: TreeNode[] = []
  const folderMap = new Map<string, TreeNode>()

  for (const path of [...files.keys()].sort()) {
    const parts = path.split('/')
    let currentLevel = root
    let currentPath = ''

    for (let i = 0; i < parts.length - 1; i++) {
      currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i]
      let folder = folderMap.get(currentPath)
      if (!folder) {
        folder = { type: 'folder', name: parts[i], path: currentPath, children: [] }
        folderMap.set(currentPath, folder)
        currentLevel.push(folder)
      }
      currentLevel = folder.children
    }

    const fileName = parts[parts.length - 1]
    currentLevel.push({ type: 'file', name: fileName, path, children: [] })
  }

  return root
}

interface FileNodeProps {
  node: TreeNode
  activeFile: string
  onSelect: (path: string) => void
  depth: number
}

function FileNode({ node, activeFile, onSelect, depth }: FileNodeProps) {
  const [open, setOpen] = useState(true)

  if (node.type === 'folder') {
    return (
      <div>
        <button
          className="flex items-center gap-1 w-full px-2 py-0.5 hover:bg-[#1c2128] text-[#8b949e] hover:text-[#e6edf3] transition-colors text-left"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
          onClick={() => setOpen(!open)}
        >
          {open ? (
            <ChevronDown size={12} className="shrink-0" />
          ) : (
            <ChevronRight size={12} className="shrink-0" />
          )}
          {open ? (
            <FolderOpen size={13} className="shrink-0 text-[#58a6ff]" />
          ) : (
            <Folder size={13} className="shrink-0 text-[#58a6ff]" />
          )}
          <span className="text-xs truncate">{node.name}</span>
        </button>
        {open && node.children.map((child) => (
          <FileNode
            key={child.path}
            node={child}
            activeFile={activeFile}
            onSelect={onSelect}
            depth={depth + 1}
          />
        ))}
      </div>
    )
  }

  const isActive = node.path === activeFile
  return (
    <button
      className={`flex items-center gap-1.5 w-full px-2 py-0.5 text-xs truncate text-left transition-colors ${
        isActive
          ? 'bg-[#1f6feb] text-white'
          : 'text-[#8b949e] hover:bg-[#1c2128] hover:text-[#e6edf3]'
      }`}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
      onClick={() => onSelect(node.path)}
    >
      <FileCode size={13} className="shrink-0" />
      <span className="truncate">{node.name}</span>
    </button>
  )
}

interface FileTreeProps {
  files: Map<string, string>
  activeFile: string
  onSelect: (path: string) => void
}

export default function FileTree({ files, activeFile, onSelect }: FileTreeProps) {
  const tree = buildTree(files)
  return (
    <div className="py-1">
      {tree.map((node) => (
        <FileNode
          key={node.path}
          node={node}
          activeFile={activeFile}
          onSelect={onSelect}
          depth={0}
        />
      ))}
    </div>
  )
}
