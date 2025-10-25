import { useState } from 'react'
import { AlertTriangle, Database, Activity, HardDrive, RefreshCw, Download, Upload, Trash2 } from 'lucide-react'
import StatCard from '../../components/admin/StatCard'
import ActionButton from '../../components/admin/ActionButton'
import type { DatabaseStats } from '../../types/admin'
import { apiRequest } from '../../utils/api'

interface DatabaseTabProps {
  databaseStats: DatabaseStats | null
  loading: boolean
  onOptimizeDatabase: () => void
}

export default function DatabaseTab({ databaseStats, loading, onOptimizeDatabase }: DatabaseTabProps) {
  // Reset database state
  const [resetSliderConfirmed, setResetSliderConfirmed] = useState(false)
  const [resetConfirmationPhrase, setResetConfirmationPhrase] = useState('')
  const [resetLoading, setResetLoading] = useState(false)
  const [resetSuccess, setResetSuccess] = useState<any>(null)
  const [resetError, setResetError] = useState<string | null>(null)

  const resetDatabase = async () => {
    if (!resetSliderConfirmed || resetConfirmationPhrase.trim().toLowerCase() !== 'if i ruin my database it is my fault') {
      setResetError('Please complete both safety confirmations before proceeding.')
      return
    }

    try {
      setResetLoading(true)
      setResetError(null)
      setResetSuccess(null)

      const response = await apiRequest('/api/admin/database/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          confirmationPhrase: resetConfirmationPhrase.trim(),
          sliderConfirmed: resetSliderConfirmed,
          enableBackup: true
        })
      })

      if (response.success) {
        setResetSuccess(response)
        setResetSliderConfirmed(false)
        setResetConfirmationPhrase('')
      } else {
        setResetError(response.error || 'Database reset failed')
      }
    } catch (err: any) {
      setResetError(err.message || 'Failed to reset database')
      console.error('Error resetting database:', err)
    } finally {
      setResetLoading(false)
    }
  }

  const handleResetSliderToggle = () => {
    setResetSliderConfirmed(!resetSliderConfirmed)
    if (resetError) setResetError(null)
  }

  const handlePhraseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setResetConfirmationPhrase(e.target.value)
    if (resetError) setResetError(null)
  }

  const isResetEnabled = () => {
    return resetSliderConfirmed && 
           resetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' &&
           !resetLoading
  }

  return (
    <div>
      <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-lg)' }}>Database Management</h2>
      
      {databaseStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-xl)' }}>
          <StatCard title="Total Records" value={databaseStats.database_stats.total_records?.toLocaleString() || 'N/A'} icon={Database} color="info" />
          <StatCard title="Total Diffs" value={databaseStats.database_stats.total_diffs?.toLocaleString() || 'N/A'} icon={Activity} color="success" />
          <StatCard title="Index Size" value={databaseStats.database_stats.index_size || 'N/A'} icon={HardDrive} color="primary" />
        </div>
      )}

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Database Operations</h3>
        <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
          <ActionButton onClick={onOptimizeDatabase} icon={RefreshCw} busy={loading}>
            Optimize Database
          </ActionButton>
          <ActionButton onClick={() => alert('Backup feature coming soon!')} icon={Download} variant="secondary" busy={loading}>
            Create Backup
          </ActionButton>
          <ActionButton onClick={() => alert('Restore feature coming soon!')} icon={Upload} variant="secondary" busy={loading}>
            Restore Backup
          </ActionButton>
        </div>
      </div>

      {databaseStats && (
        <div style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--border-radius-lg)',
          padding: 'var(--spacing-lg)'
        }}>
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Database Information</h3>
          <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Last Optimized:</span>
              <span>{databaseStats.database_stats.last_optimized || 'Never'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Total Records:</span>
              <span>{databaseStats.database_stats.total_records?.toLocaleString() || 'N/A'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Index Size:</span>
              <span>{databaseStats.database_stats.index_size || 'N/A'}</span>
            </div>
          </div>
        </div>
      )}

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '2px solid var(--color-error)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)',
        marginTop: 'var(--spacing-xl)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-md)' }}>
          <AlertTriangle style={{ width: '1.5rem', height: '1.5rem', color: 'var(--color-error)' }} />
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-error)', margin: 0 }}>
            Danger Zone
          </h3>
        </div>
        
        <div style={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--color-error)',
          borderRadius: 'var(--border-radius-md)',
          padding: 'var(--spacing-md)',
          marginBottom: 'var(--spacing-lg)'
        }}>
          <h4 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-error)', margin: '0 0 var(--spacing-sm) 0' }}>
            Reset Database
          </h4>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', margin: '0 0 var(--spacing-md) 0' }}>
            This will permanently delete ALL data from the database including file tracking history, semantic analysis, session summaries, and all other stored information. 
            A backup will be created automatically before the reset.
          </p>

          {resetSuccess && (
            <div style={{
              backgroundColor: 'var(--color-success)',
              color: 'white',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--border-radius-md)',
              marginBottom: 'var(--spacing-md)',
              fontSize: 'var(--font-size-sm)'
            }}>
              <strong>Database Reset Successful!</strong>
              <br />
              {resetSuccess.message}
              {resetSuccess.recovery_info?.backup_available && (
                <>
                  <br />
                  <strong>Backup saved:</strong> {resetSuccess.recovery_info.backup_location}
                </>
              )}
            </div>
          )}

          {resetError && (
            <div style={{
              backgroundColor: 'var(--color-error)',
              color: 'white',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--border-radius-md)',
              marginBottom: 'var(--spacing-md)',
              fontSize: 'var(--font-size-sm)'
            }}>
              <strong>Error:</strong> {resetError}
            </div>
          )}

          <div style={{ marginBottom: 'var(--spacing-md)' }}>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 'var(--spacing-md)', 
              cursor: 'pointer',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              <span>I understand the risks and consequences</span>
              <div 
                onClick={handleResetSliderToggle}
                style={{
                  width: '3.5rem',
                  height: '1.75rem',
                  backgroundColor: resetSliderConfirmed ? 'var(--color-error)' : 'var(--color-border)',
                  borderRadius: '0.875rem',
                  position: 'relative',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s ease'
                }}
              >
                <div style={{
                  width: '1.5rem',
                  height: '1.5rem',
                  backgroundColor: 'white',
                  borderRadius: '50%',
                  position: 'absolute',
                  top: '0.125rem',
                  left: resetSliderConfirmed ? '1.875rem' : '0.125rem',
                  transition: 'left 0.2s ease',
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
                }} />
              </div>
            </label>
          </div>

          <div style={{ marginBottom: 'var(--spacing-lg)' }}>
            <label style={{ 
              display: 'block', 
              fontSize: 'var(--font-size-sm)', 
              fontWeight: 'var(--font-weight-medium)',
              marginBottom: 'var(--spacing-xs)'
            }}>
              Type the following phrase to confirm: <span style={{ color: 'var(--color-error)', fontWeight: 'var(--font-weight-bold)' }}>
                if i ruin my database it is my fault
              </span>
            </label>
            <input
              type="text"
              value={resetConfirmationPhrase}
              onChange={handlePhraseChange}
              placeholder="Type the confirmation phrase exactly..."
              disabled={resetLoading}
              style={{
                width: '100%',
                padding: 'var(--spacing-sm)',
                border: `1px solid ${resetConfirmationPhrase.trim().toLowerCase() === 'if i ruin my database it is my fault' ? 'var(--color-success)' : 'var(--color-border)'}`,
                borderRadius: 'var(--border-radius-md)',
                fontSize: 'var(--font-size-sm)',
                backgroundColor: resetLoading ? 'var(--color-surface)' : 'white',
                color: 'var(--color-text-primary)'
              }}
            />
          </div>

          <button
            onClick={resetDatabase}
            disabled={!isResetEnabled()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-sm)',
              padding: 'var(--spacing-md) var(--spacing-lg)',
              backgroundColor: isResetEnabled() ? 'var(--color-error)' : 'var(--color-border)',
              color: isResetEnabled() ? 'white' : 'var(--color-text-secondary)',
              border: 'none',
              borderRadius: 'var(--border-radius-md)',
              cursor: isResetEnabled() ? 'pointer' : 'not-allowed',
              opacity: isResetEnabled() ? 1 : 0.6,
              transition: 'all 0.2s ease',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-semibold)'
            }}
          >
            <Trash2 style={{ width: '1rem', height: '1rem' }} />
            {resetLoading ? 'Resetting Database...' : 'Reset Database'}
          </button>
        </div>
      </div>
    </div>
  )
}
