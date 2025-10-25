import { Shield, RefreshCw } from 'lucide-react'

interface AdminHeaderProps {
  systemOnline: boolean
  loading: boolean
  onRefresh: () => void
}

export default function AdminHeader({ systemOnline, loading, onRefresh }: AdminHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
      background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
    }}>
      <div className="absolute inset-0 bg-black/10"></div>
      <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
      <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

      <div className="relative z-10 flex items-center justify-between">
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
              <Shield className="h-6 w-6" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Administration Panel</h1>
          </div>
          <p className="text-blue-100 text-lg">Manage system settings, monitor performance, and maintain your Obby instance</p>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-4 py-2 rounded-full backdrop-blur-sm border border-white/30 bg-white/10">
            <div className={`w-2 h-2 rounded-full ${systemOnline ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`}></div>
            <span className="text-sm font-medium">
              {systemOnline ? 'System Online' : 'Loading Status'}
            </span>
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="relative overflow-hidden px-6 py-3 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group bg-white/20 hover:bg-white/30 border border-white/30 text-white"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
            <div className="relative flex items-center space-x-2">
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                  <span>Refreshing...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  <span>Refresh Stats</span>
                </>
              )}
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}


