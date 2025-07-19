import { Link, useLocation } from 'react-router-dom'
import { 
  Home, 
  FolderTree, 
  GitBranch, 
  FileText, 
  Settings, 
  Menu,
  Activity
} from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'File Explorer', href: '/files', icon: FolderTree },
  { name: 'Diff Viewer', href: '/diffs', icon: GitBranch },
  { name: 'Living Note', href: '/living-note', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const location = useLocation()

  return (
    <div className={`fixed inset-y-0 left-0 z-50 ${isOpen ? 'w-64' : 'w-16'} bg-white border-r border-gray-200 transition-all duration-300`}>
      <div className="flex h-16 items-center justify-between px-4 border-b border-gray-200">
        {isOpen && (
          <div className="flex items-center">
            <Activity className="h-8 w-8 text-primary-600" />
            <span className="ml-2 text-lg font-semibold text-gray-900">Obby</span>
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-2 rounded-md hover:bg-gray-100 transition-colors"
        >
          <Menu className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      <nav className="mt-8 px-4">
        <ul className="space-y-2">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  to={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-600'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                  title={!isOpen ? item.name : undefined}
                >
                  <item.icon className={`h-5 w-5 ${isActive ? 'text-primary-600' : ''}`} />
                  {isOpen && <span className="ml-3">{item.name}</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </div>
  )
}