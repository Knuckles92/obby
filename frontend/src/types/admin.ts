export interface SystemStats {
  stats: {
    system: {
      cpu_percent: number
      cpu_count: number
      memory_total: number
      memory_available: number
      memory_percent: number
      disk_total: number
      disk_used: number
      disk_free: number
      disk_percent: number
    }
    process: {
      memory_rss: number
      memory_vms: number
      memory_percent: number
      cpu_percent: number
      pid: number
      num_threads: number
    }
  }
  timestamp: number
}

export interface DatabaseStats {
  database_stats: {
    total_records: number
    total_diffs: number
    index_size: string
    last_optimized: string
    query_performance: number
  }
  success: boolean
}


