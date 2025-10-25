import { Cpu, MemoryStick, HardDrive, Activity, Database, Download, Trash2, RefreshCw } from 'lucide-react'
import StatCard from '../../components/admin/StatCard'
import ActionButton from '../../components/admin/ActionButton'
import type { SystemStats } from '../../types/admin'

interface OverviewTabProps {
  systemStats: SystemStats | null
  loading: boolean
  onOptimizeDatabase: () => void
  onClearLogs: () => void
  onClearDashboardData: () => void
}

export default function OverviewTab({ systemStats, loading, onOptimizeDatabase, onClearLogs, onClearDashboardData }: OverviewTabProps) {
  return (
    <div>
      <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0, marginBottom: 'var(--spacing-lg)' }}>System Overview</h2>

      {systemStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-xl)' }}>
          <StatCard title="CPU Cores" value={systemStats.stats.system.cpu_count} icon={Activity} color="green" />
          <StatCard title="Memory Usage" value={`${Math.round(systemStats.stats.system.memory_percent)}%`} icon={MemoryStick} color="blue" percentage={systemStats.stats.system.memory_percent} />
          <StatCard title="CPU Usage" value={`${Math.round(systemStats.stats.system.cpu_percent)}%`} icon={Cpu} color="orange" percentage={systemStats.stats.system.cpu_percent} />
          <StatCard title="Disk Usage" value={`${Math.round(systemStats.stats.system.disk_percent)}%`} icon={HardDrive} color="purple" percentage={systemStats.stats.system.disk_percent} />
          <StatCard title="Process PID" value={systemStats.stats.process.pid} icon={Activity} color="green" />
          <StatCard title="Process Memory" value={`${Math.round(systemStats.stats.process.memory_percent)}%`} icon={Database} color="blue" percentage={systemStats.stats.process.memory_percent} />
        </div>
      )}

      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--border-radius-lg)',
        padding: 'var(--spacing-lg)'
      }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--spacing-md)' }}>Quick Actions</h3>
        <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
          <ActionButton onClick={onOptimizeDatabase} icon={Database} busy={loading}>
            Optimize Database
          </ActionButton>
          <ActionButton onClick={onClearLogs} icon={Trash2} variant="danger" busy={loading}>
            Clear Logs
          </ActionButton>
          <ActionButton onClick={onClearDashboardData} icon={Trash2} variant="danger" busy={loading}>
            Clear Dashboard Data
          </ActionButton>
          <ActionButton onClick={() => alert('Export feature coming soon!')} icon={Download} variant="secondary" busy={loading}>
            Export Data
          </ActionButton>
        </div>
      </div>
    </div>
  )
}


