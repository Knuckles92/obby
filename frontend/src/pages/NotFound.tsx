import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="h-full flex items-center justify-center">
      <div
        className="max-w-lg w-full p-8 rounded-xl border text-center"
        style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
      >
        <div className="flex items-center justify-center mb-4">
          <Search size={28} style={{ color: 'var(--color-primary)' }} />
        </div>
        <h1 className="text-2xl font-bold mb-2">Page Not Found</h1>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-secondary)' }}>
          We couldn’t find the page you were looking for.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            to="/"
            className="px-4 py-2 rounded-md"
            style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}
          >
            Go to Dashboard
          </Link>
          <Link
            to="/queries"
            className="px-4 py-2 rounded-md border"
            style={{ backgroundColor: 'var(--color-background)', color: 'var(--color-text-primary)', borderColor: 'var(--color-border)' }}
          >
            Open Queries
          </Link>
        </div>
      </div>
    </div>
  )
}

