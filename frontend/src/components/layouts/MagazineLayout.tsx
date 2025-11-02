import { Award, TrendingUp, Zap, FileText, Star, Activity } from 'lucide-react'

export default function MagazineLayout() {
  return (
    <div className="min-h-screen p-6">
      {/* Compact Header */}
      <div className="mb-6">
        <h1 className="text-4xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
          Discovery Digest
        </h1>
        <p style={{ color: 'var(--color-text-secondary)' }}>
          Weekly patterns and findings from the agent
        </p>
      </div>

      {/* Asymmetric Grid */}
      <div className="grid grid-cols-12 gap-4 auto-rows-fr" style={{ gridAutoFlow: 'dense' }}>
        {/* Featured Insight - Large 6x2 */}
        <div
          className="col-span-12 md:col-span-6 row-span-2 relative overflow-hidden rounded-2xl p-8 text-white shadow-2xl group cursor-pointer transform transition-all duration-300 hover:scale-[1.02]"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            minHeight: '300px'
          }}
        >
          <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-all"></div>
          <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>

          <div className="relative z-10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Star className="h-6 w-6" />
                <span className="text-sm font-semibold uppercase tracking-wider">Featured</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold mb-4 leading-tight">
                Consistent Patterns<br />Detected
              </h2>
              <p className="text-lg text-white/90">
                Agent detected 95% activity consistency across all 7 days this week
              </p>
            </div>
            <div className="flex items-end justify-between mt-6">
              <div>
                <p className="text-5xl font-bold">95%</p>
                <p className="text-sm text-white/80">Consistency Score</p>
              </div>
              <TrendingUp className="h-12 w-12 text-white/40" />
            </div>
          </div>
        </div>

        {/* Top Achievement - Tall 3x2 */}
        <div
          className="col-span-12 md:col-span-3 row-span-2 relative overflow-hidden rounded-2xl p-6 text-white shadow-xl group cursor-pointer transform transition-all duration-300 hover:scale-[1.02]"
          style={{
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            minHeight: '300px'
          }}
        >
          <div className="absolute -top-6 -right-6 w-24 h-24 bg-white/20 rounded-full blur-2xl"></div>
          <div className="relative z-10 h-full flex flex-col">
            <Award className="h-10 w-10 mb-4" />
            <h3 className="text-2xl font-bold mb-3">Notable Finding</h3>
            <p className="text-white/90 text-sm mb-4 flex-grow">
              Agent identified major refactoring pattern across multiple modules
            </p>
            <div className="border-t border-white/20 pt-4">
              <p className="text-3xl font-bold">+47</p>
              <p className="text-xs text-white/80">Files Modified</p>
            </div>
          </div>
        </div>

        {/* Quick Stats - 3x1 Cards */}
        <div
          className="col-span-6 md:col-span-3 rounded-xl p-5 shadow-lg border group cursor-pointer transform transition-all duration-300 hover:scale-105"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <Zap className="h-6 w-6 mb-3" style={{ color: 'var(--color-warning)' }} />
          <p className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>128</p>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Active Time (hrs)</p>
          <div className="mt-3 flex items-center gap-2 text-xs" style={{ color: 'var(--color-success)' }}>
            <TrendingUp className="h-3 w-3" />
            <span>+18% from last week</span>
          </div>
        </div>

        <div
          className="col-span-6 md:col-span-3 rounded-xl p-5 shadow-lg border group cursor-pointer transform transition-all duration-300 hover:scale-105"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <FileText className="h-6 w-6 mb-3" style={{ color: 'var(--color-info)' }} />
          <p className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>342</p>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Files Changed</p>
          <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-divider)' }}>
            <div className="h-full rounded-full" style={{ width: '73%', backgroundColor: 'var(--color-info)' }}></div>
          </div>
        </div>

        <div
          className="col-span-6 md:col-span-3 rounded-xl p-5 shadow-lg border group cursor-pointer transform transition-all duration-300 hover:scale-105"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <Activity className="h-6 w-6 mb-3" style={{ color: 'var(--color-success)' }} />
          <p className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>4.2</p>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Changes/Hour</p>
          <div className="mt-3 flex gap-1">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="flex-1 h-1 rounded-full" style={{ backgroundColor: i <= 4 ? 'var(--color-success)' : 'var(--color-divider)' }}></div>
            ))}
          </div>
        </div>

        {/* Trending Topic - Wide 6x1 */}
        <div
          className="col-span-12 md:col-span-6 relative overflow-hidden rounded-xl p-6 text-white shadow-xl group cursor-pointer transform transition-all duration-300 hover:scale-[1.02]"
          style={{
            background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            minHeight: '140px'
          }}
        >
          <div className="absolute -right-8 -bottom-8 w-32 h-32 bg-white/20 rounded-full blur-2xl"></div>
          <div className="relative z-10">
            <p className="text-sm font-semibold uppercase tracking-wider mb-2">Trending This Week</p>
            <h3 className="text-2xl font-bold mb-2">Documentation Sprint</h3>
            <div className="flex items-center gap-4">
              <p className="text-4xl font-bold">28%</p>
              <p className="text-sm">of all changes focused on improving docs and comments</p>
            </div>
          </div>
        </div>

        {/* Change Highlights - 4x1 */}
        <div
          className="col-span-12 md:col-span-4 rounded-xl p-5 shadow-lg border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <h4 className="font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>Change Highlights</h4>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Lines Added</span>
              <span className="text-lg font-bold text-green-600">+2,847</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Lines Deleted</span>
              <span className="text-lg font-bold text-red-600">-1,234</span>
            </div>
            <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Net Change</span>
              <span className="text-xl font-bold text-blue-600">+1,613</span>
            </div>
          </div>
        </div>

        {/* Favorite Files - 4x1 */}
        <div
          className="col-span-12 md:col-span-4 rounded-xl p-5 shadow-lg border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <h4 className="font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>Most Edited Files</h4>
          <div className="space-y-2">
            {[
              { name: 'Dashboard.tsx', changes: 45 },
              { name: 'api.ts', changes: 32 },
              { name: 'theme.css', changes: 28 }
            ].map((file, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm truncate" style={{ color: 'var(--color-text-secondary)' }}>{file.name}</span>
                <span className="text-sm font-bold px-2 py-1 rounded" style={{
                  backgroundColor: 'var(--color-primary)',
                  color: 'var(--color-text-inverse)'
                }}>
                  {file.changes}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Pattern - 4x1 */}
        <div
          className="col-span-12 md:col-span-4 rounded-xl p-5 shadow-lg border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)'
          }}
        >
          <h4 className="font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>Activity Pattern</h4>
          <div className="flex items-end justify-between h-20 gap-1">
            {[65, 82, 45, 92, 78, 38, 22].map((value, i) => (
              <div
                key={i}
                className="flex-1 rounded-t"
                style={{
                  height: `${value}%`,
                  background: 'linear-gradient(180deg, var(--color-primary), var(--color-accent))',
                  opacity: 0.8
                }}
              ></div>
            ))}
          </div>
          <div className="flex items-center justify-between mt-3 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <span>Mon</span>
            <span>Sun</span>
          </div>
        </div>

        {/* Key Insight - Full width 12x1 */}
        <div
          className="col-span-12 relative overflow-hidden rounded-2xl p-8 text-white shadow-2xl"
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)',
            minHeight: '120px'
          }}
        >
          <div className="absolute inset-0 bg-black/10"></div>
          <div className="relative z-10 text-center">
            <p className="text-sm font-semibold uppercase tracking-wider mb-2">Key Insight</p>
            <p className="text-2xl md:text-3xl font-bold">
              Agent detected peak activity on Thursday afternoons at 3 PM - highest change volume consistently occurs during this window
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
