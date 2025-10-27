import { Database, Activity, HardDrive, Cpu, Settings } from 'lucide-react'
import ActionButton from '../../components/admin/ActionButton'

interface ConfigTabProps {
  config: any
  configLoading: boolean
  models: Record<string, string>
  currentModel: string
}

export default function ConfigTab({ config, configLoading, models, currentModel }: ConfigTabProps) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
        <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>System Configuration</h2>
      </div>

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>Monitoring Settings</h3>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: '1.5' }}>
          These settings control how Obby monitors your files and detects changes in real-time.
        </p>
        <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--spacing-sm) 0' }}>
            <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Auto-monitoring</span>
            {configLoading ? (
              <div style={{
                width: '1rem',
                height: '1rem',
                border: '2px solid var(--color-border)',
                borderTopColor: 'var(--color-primary)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
            ) : (
              <div style={{
                width: '3rem',
                height: '1.5rem',
                backgroundColor: config?.periodicCheckEnabled ? 'var(--color-primary)' : 'var(--color-border)',
                borderRadius: '0.75rem',
                position: 'relative'
              }}>
                <div style={{
                  width: '1.25rem',
                  height: '1.25rem',
                  backgroundColor: 'white',
                  borderRadius: '50%',
                  position: 'absolute',
                  top: '0.125rem',
                  right: config?.periodicCheckEnabled ? '0.125rem' : 'auto',
                  left: config?.periodicCheckEnabled ? 'auto' : '0.125rem',
                  transition: 'all 0.2s ease'
                }} />
              </div>
            )}
          </div>
          <div style={{
            paddingLeft: 'var(--spacing-md)',
            paddingBottom: 'var(--spacing-sm)',
            borderBottom: '1px solid var(--color-border)'
          }}>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              When enabled, Obby automatically starts monitoring files in directories specified in <code style={{
                backgroundColor: 'var(--color-border)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>.obbywatch</code>. Uses watchdog library for real-time file change detection with zero latency. Excludes patterns from <code style={{
                backgroundColor: 'var(--color-border)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>.obbyignore</code>. Recommended: Keep enabled for active development.
            </p>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--spacing-sm) 0' }}>
            <span style={{ fontWeight: 'var(--font-weight-medium)' }}>Real-time updates</span>
            {configLoading ? (
              <div style={{
                width: '1rem',
                height: '1rem',
                border: '2px solid var(--color-border)',
                borderTopColor: 'var(--color-primary)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
            ) : (
              <div style={{
                width: '3rem',
                height: '1.5rem',
                backgroundColor: 'var(--color-primary)',
                borderRadius: '0.75rem',
                position: 'relative'
              }}>
                <div style={{
                  width: '1.25rem',
                  height: '1.25rem',
                  backgroundColor: 'white',
                  borderRadius: '50%',
                  position: 'absolute',
                  top: '0.125rem',
                  right: '0.125rem',
                  transition: 'all 0.2s ease'
                }} />
              </div>
            )}
          </div>
          <div style={{
            paddingLeft: 'var(--spacing-md)',
            paddingBottom: 'var(--spacing-sm)'
          }}>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              Enables Server-Sent Events (SSE) to push updates to the frontend instantly at <code style={{
                backgroundColor: 'var(--color-border)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>/api/session-summary/events</code> and <code style={{
                backgroundColor: 'var(--color-border)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>/api/summary-notes/events</code>. When disabled, the dashboard will only refresh on page reload. Essential for collaborative environments.
            </p>
          </div>
        </div>
      </div>

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>File Tracking</h3>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: '1.5' }}>
          Configuration for how Obby tracks file changes, generates diffs, and manages file versions.
        </p>
        <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
          <div style={{
            padding: 'var(--spacing-md)',
            backgroundColor: 'rgba(var(--color-primary-rgb), 0.05)',
            borderRadius: 'var(--border-radius-md)',
            border: '1px solid var(--color-border)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
              <Database style={{ width: '1rem', height: '1rem', color: 'var(--color-primary)' }} />
              <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Content Hashing</span>
            </div>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              Uses SHA-256 hashing to detect actual content changes rather than relying solely on modification timestamps. Prevents false positives from tools that touch files without changing content. Implemented via <code style={{
                backgroundColor: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>FileContentTracker</code> in <code style={{
                backgroundColor: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>core/file_tracker.py</code>.
            </p>
          </div>

          <div style={{
            padding: 'var(--spacing-md)',
            backgroundColor: 'rgba(var(--color-primary-rgb), 0.05)',
            borderRadius: 'var(--border-radius-md)',
            border: '1px solid var(--color-border)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
              <Activity style={{ width: '1rem', height: '1rem', color: 'var(--color-primary)' }} />
              <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Diff Generation</span>
            </div>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              Creates native unified diffs showing line-by-line changes between file versions. Pure file-system based diff generation without git dependencies. Stored in <code style={{
                backgroundColor: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>ContentDiffModel</code> table with FTS5 search indexing for fast retrieval.
            </p>
          </div>

          <div style={{
            padding: 'var(--spacing-md)',
            backgroundColor: 'rgba(var(--color-primary-rgb), 0.05)',
            borderRadius: 'var(--border-radius-md)',
            border: '1px solid var(--color-border)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
              <HardDrive style={{ width: '1rem', height: '1rem', color: 'var(--color-primary)' }} />
              <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Version History</span>
            </div>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              Maintains complete version history for every tracked file. Each version includes content hash, timestamp, and full diff. Enables time-travel queries and comprehensive change analysis. Stored via <code style={{
                backgroundColor: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>FileVersionModel</code> with connection pooling for thread-safe access.
            </p>
          </div>
        </div>
      </div>

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>AI Processing</h3>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: '1.5' }}>
          Settings for Claude-powered summaries and semantic analysis.
        </p>
        <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
          <div style={{
            padding: 'var(--spacing-md)',
            backgroundColor: 'rgba(59, 130, 246, 0.05)',
            borderRadius: 'var(--border-radius-md)',
            border: '1px solid rgba(59, 130, 246, 0.2)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
              <Cpu style={{ width: '1rem', height: '1rem', color: 'rgb(59, 130, 246)' }} />
              <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Session Summaries</span>
            </div>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: '0 0 var(--spacing-sm) 0',
              lineHeight: '1.5'
            }}>
              Generates rolling project summaries using the Claude Agent SDK. Changes are aggregated and summarized on a schedule to keep the session overview up to date. Configure cadence and automation in the Settings page. Requires <code style={{
                backgroundColor: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>ANTHROPIC_API_KEY</code> in the environment.
            </p>
            {configLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--spacing-sm)' }}>
                <div style={{
                  width: '1rem',
                  height: '1rem',
                  border: '2px solid var(--color-border)',
                  borderTopColor: 'var(--color-primary)',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 'var(--spacing-sm)',
                marginTop: 'var(--spacing-sm)'
              }}>
                <div style={{ fontSize: 'var(--font-size-xs)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>AI Update Interval:</span>
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', marginLeft: 'var(--spacing-xs)' }}>
                    {config?.aiUpdateInterval || 12} hours
                  </span>
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Auto Updates:</span>
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', marginLeft: 'var(--spacing-xs)' }}>
                    {config?.aiAutoUpdateEnabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>
            )}
          </div>

          <div style={{
            padding: 'var(--spacing-md)',
            backgroundColor: 'rgba(59, 130, 246, 0.05)',
            borderRadius: 'var(--border-radius-md)',
            border: '1px solid rgba(59, 130, 246, 0.2)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xs)' }}>
              <Activity style={{ width: '1rem', height: '1rem', color: 'rgb(59, 130, 246)' }} />
              <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>Semantic Analysis</span>
            </div>
            <p style={{
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
              margin: '0 0 var(--spacing-sm) 0',
              lineHeight: '1.5'
            }}>
              Extracts topics, keywords, and impact levels from file changes using Claude models. Enables powerful search and filtering by semantic content. Results are stored in <code style={{
                backgroundColor: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: 'var(--font-size-xs)'
              }}>SemanticModel</code> with FTS5 indexing for fast semantic search.
            </p>
            {configLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--spacing-sm)' }}>
                <div style={{
                  width: '1rem',
                  height: '1rem',
                  border: '2px solid var(--color-border)',
                  borderTopColor: 'var(--color-primary)',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
              </div>
            ) : (
              <div>
                <div style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--spacing-xs)'
                }}>
                  Current Model: <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                    {currentModel || config?.aiModel || 'Not configured'}
                  </span>
                </div>
                {Object.keys(models).length > 0 && (
                  <div style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-secondary)'
                  }}>
                    Available Models: <span style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>
                      {Object.keys(models).join(', ')}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)'
      }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-sm)' }}>Advanced Configuration</h3>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-lg)', fontSize: 'var(--font-size-sm)', lineHeight: '1.6' }}>
          Fine-tune monitoring behavior, configure AI processing models, manage watch directories, and set output paths.
          These settings are stored in <code style={{
            backgroundColor: 'var(--color-border)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: 'var(--font-size-xs)'
          }}>config.json</code> and <code style={{
            backgroundColor: 'var(--color-border)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: 'var(--font-size-xs)'
          }}>config/settings.py</code>.
        </p>
        <ActionButton onClick={() => window.location.href = '/settings'} icon={Settings} variant="secondary">
          Go to Settings
        </ActionButton>
      </div>
    </div>
  )
}
