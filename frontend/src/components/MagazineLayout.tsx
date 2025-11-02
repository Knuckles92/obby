import { Sparkles, TrendingUp, FileText, Target, Zap, BookOpen, Calendar, Award, ArrowUp, ArrowDown, BarChart3, PieChart } from 'lucide-react'

interface MagazineLayoutProps {
  className?: string
}

export default function MagazineLayout({ className = '' }: MagazineLayoutProps) {
  const containerClass = `
    grid gap-6
    ${className}
  `

  const gridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gridAutoRows: 'auto',
    gridAutoFlow: 'dense',
  }

  // Define CSS variables for the grid
  const magazineGridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(12, 1fr)',
    gridAutoRows: '280px',
    gap: '24px',
    gridAutoFlow: 'dense',
  }

  const largeCardStyle: React.CSSProperties = {
    gridColumn: 'span 6',
    gridRow: 'span 2',
  }

  const mediumCardStyle: React.CSSProperties = {
    gridColumn: 'span 4',
    gridRow: 'span 1',
  }

  const smallCardStyle: React.CSSProperties = {
    gridColumn: 'span 4',
    gridRow: 'span 1',
  }

  const wideCardStyle: React.CSSProperties = {
    gridColumn: 'span 6',
    gridRow: 'span 1',
  }

  const CardContainer = ({ children, style }: { children: React.ReactNode; style: React.CSSProperties }) => (
    <div style={style} className="h-full">
      {children}
    </div>
  )

  return (
    <div className="min-h-screen">
      {/* Header */}
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
                <Sparkles className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Insights Magazine</h1>
            </div>
            <p className="text-blue-100 text-lg">Explore your work patterns in a visual journey</p>
          </div>

          <div className="flex items-center space-x-4 px-6 py-3 rounded-full backdrop-blur-sm border border-white/20 bg-white/10">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
            <span className="text-sm font-medium">Last 7 days</span>
          </div>
        </div>
      </div>

      {/* Magazine Grid Layout */}
      <div style={magazineGridStyle}>
        {/* Featured Insight Card - Large 2x2 */}
        <CardContainer style={largeCardStyle}>
          <div className="group/card relative overflow-hidden rounded-3xl h-full shadow-2xl border-2 hover:shadow-3xl transition-all duration-300 hover:-translate-y-2" style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderColor: 'rgba(255, 255, 255, 0.2)',
          }}>
            <div className="absolute inset-0 bg-black/20"></div>
            <div className="absolute -top-20 -right-20 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
            <div className="absolute -bottom-20 -left-20 w-32 h-32 bg-white/20 rounded-full blur-2xl"></div>

            <div className="relative p-8 h-full flex flex-col justify-between text-white">
              <div>
                <div className="flex items-center space-x-2 mb-4">
                  <div className="px-3 py-1 rounded-full bg-white/20 backdrop-blur-sm text-xs font-semibold">
                    Featured
                  </div>
                  <div className="px-3 py-1 rounded-full bg-green-400/30 backdrop-blur-sm text-xs font-semibold flex items-center space-x-1">
                    <TrendingUp className="h-3 w-3" />
                    <span>+18%</span>
                  </div>
                </div>
                <h2 className="text-3xl font-bold mb-3 leading-tight">Peak Productivity Week</h2>
                <p className="text-blue-100 text-sm leading-relaxed">Your most productive week with 1,284 changes across 47 files. Documentation and bug fixes led the charge.</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="opacity-90">Consistency Score</span>
                  <span className="font-bold text-lg">94%</span>
                </div>
                <div className="w-full h-2 bg-white/20 rounded-full overflow-hidden">
                  <div className="h-full bg-green-400 rounded-full" style={{ width: '94%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Top Achievement Card - Medium 1x2 */}
        <CardContainer style={{
          gridColumn: 'span 3',
          gridRow: 'span 2',
        }}>
          <div className="group/card relative overflow-hidden rounded-3xl h-full shadow-xl border hover:shadow-2xl transition-all duration-300 hover:-translate-y-2" style={{
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="absolute inset-0 bg-black/10"></div>
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-white/20 rounded-full blur-2xl"></div>

            <div className="relative p-6 h-full flex flex-col justify-between text-white">
              <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm">
                <Award className="h-6 w-6" />
              </div>

              <div>
                <p className="text-sm font-semibold opacity-90 mb-2">Top Achievement</p>
                <h3 className="text-2xl font-bold">Bug Fixer</h3>
                <p className="text-xs opacity-75 mt-2">124 fixes in this cycle</p>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Quick Stat 1 - Small */}
        <CardContainer style={{
          gridColumn: 'span 3',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="relative p-6 h-full flex flex-col justify-between">
              <div className="p-3 rounded-xl shadow-lg w-fit" style={{
                backgroundColor: '#3b82f6',
              }}>
                <BarChart3 className="h-5 w-5 text-white" />
              </div>

              <div>
                <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Total Changes</p>
                <p className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>1.2K</p>
                <div className="flex items-center space-x-1 mt-2 text-xs text-green-600">
                  <ArrowUp className="h-3 w-3" />
                  <span>+12%</span>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Trending Topic Card - Wide */}
        <CardContainer style={wideCardStyle}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="absolute inset-0 bg-black/10"></div>
            <div className="relative p-6 h-full flex items-center justify-between text-white">
              <div>
                <p className="text-sm font-semibold opacity-90 mb-1">Trending This Week</p>
                <h3 className="text-2xl font-bold">Documentation</h3>
                <p className="text-xs opacity-75 mt-1">28% of all changes</p>
              </div>
              <div className="text-4xl font-bold opacity-20">📚</div>
            </div>
          </div>
        </CardContainer>

        {/* Quick Stat 2 - Small */}
        <CardContainer style={{
          gridColumn: 'span 3',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="relative p-6 h-full flex flex-col justify-between">
              <div className="p-3 rounded-xl shadow-lg w-fit" style={{
                backgroundColor: '#8b5cf6',
              }}>
                <FileText className="h-5 w-5 text-white" />
              </div>

              <div>
                <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Files Modified</p>
                <p className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>47</p>
                <div className="flex items-center space-x-1 mt-2 text-xs text-green-600">
                  <ArrowUp className="h-3 w-3" />
                  <span>+5%</span>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Quick Stat 3 - Small */}
        <CardContainer style={{
          gridColumn: 'span 3',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="relative p-6 h-full flex flex-col justify-between">
              <div className="p-3 rounded-xl shadow-lg w-fit" style={{
                backgroundColor: '#ec4899',
              }}>
                <Zap className="h-5 w-5 text-white" />
              </div>

              <div>
                <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>Peak Activity</p>
                <p className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>2:45 PM</p>
                <div className="flex items-center space-x-1 mt-2 text-xs text-green-600">
                  <ArrowUp className="h-3 w-3" />
                  <span>+8%</span>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Change Highlights - Medium */}
        <CardContainer style={{
          gridColumn: 'span 4',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="relative p-6 h-full flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold mb-3 px-3 py-1 rounded-full w-fit" style={{
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-primary)'
                }}>Change Highlights</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>Additions</span>
                  <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                    <div className="h-full rounded-full" style={{
                      width: '65%',
                      backgroundColor: '#10b981'
                    }}></div>
                  </div>
                  <span className="text-xs font-bold text-green-600">2.3K</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>Deletions</span>
                  <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                    <div className="h-full rounded-full" style={{
                      width: '35%',
                      backgroundColor: '#ef4444'
                    }}></div>
                  </div>
                  <span className="text-xs font-bold text-red-600">1.2K</span>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Favorite Files - Medium */}
        <CardContainer style={{
          gridColumn: 'span 4',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="relative p-6 h-full flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold mb-3 px-3 py-1 rounded-full w-fit" style={{
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-warning)'
                }}>Favorite Files</p>
              </div>

              <div className="space-y-2">
                {[
                  { name: 'App.tsx', changes: 34 },
                  { name: 'types.ts', changes: 28 },
                  { name: 'styles.css', changes: 19 }
                ].map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-lg" style={{ backgroundColor: 'var(--color-background)' }}>
                    <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>{file.name}</span>
                    <span className="text-xs font-bold" style={{ color: 'var(--color-warning)' }}>{file.changes}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Recent Patterns - Medium */}
        <CardContainer style={{
          gridColumn: 'span 4',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-background) 100%)',
            borderColor: 'var(--color-border)',
          }}>
            <div className="relative p-6 h-full flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold mb-3 px-3 py-1 rounded-full w-fit" style={{
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-success)'
                }}>Pattern This Week</p>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>Morning Rush</span>
                    <span className="text-xs font-bold text-blue-600">8-10 AM</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                    <div className="h-full rounded-full" style={{
                      width: '85%',
                      backgroundColor: '#3b82f6'
                    }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>Afternoon Focus</span>
                    <span className="text-xs font-bold text-purple-600">2-4 PM</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-border)' }}>
                    <div className="h-full rounded-full" style={{
                      width: '72%',
                      backgroundColor: '#8b5cf6'
                    }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>

        {/* Bottom Wide Insights - Full Width */}
        <CardContainer style={{
          gridColumn: 'span 12',
          gridRow: 'span 1',
        }}>
          <div className="group/card relative overflow-hidden rounded-2xl h-full shadow-lg border hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)',
            borderColor: 'rgba(255, 255, 255, 0.2)',
          }}>
            <div className="absolute inset-0 bg-black/10"></div>

            <div className="relative p-8 h-full flex items-center justify-between text-white">
              <div className="flex-1">
                <p className="text-sm font-semibold opacity-90 mb-2">Key Insight</p>
                <h3 className="text-2xl font-bold mb-2">Your work maintains excellent consistency</h3>
                <p className="text-blue-100 text-sm max-w-2xl">95+ changes per day on average with peak productivity Thursday afternoons. JavaScript and TypeScript dominate 65% of your changes.</p>
              </div>

              <div className="flex items-center space-x-6 ml-8">
                <div className="text-center">
                  <p className="text-4xl font-bold">94%</p>
                  <p className="text-xs opacity-75 mt-1">Consistency</p>
                </div>
                <div className="text-center">
                  <p className="text-4xl font-bold">7/7</p>
                  <p className="text-xs opacity-75 mt-1">Active Days</p>
                </div>
              </div>
            </div>
          </div>
        </CardContainer>
      </div>
    </div>
  )
}
