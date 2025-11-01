import { Sparkles } from 'lucide-react'

export default function Insights() {
  return (
    <div className="h-full flex items-center justify-center">
      <div
        className="max-w-lg w-full p-8 rounded-xl border text-center"
        style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
      >
        <div className="flex items-center justify-center mb-4">
          <Sparkles size={32} style={{ color: 'var(--color-primary)' }} />
        </div>
        <h1 className="text-2xl font-bold mb-2">Insights</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Coming soon...
        </p>
      </div>
    </div>
  )
}
