/**
 * Service Management Types
 */

export interface Service {
  id: number
  name: string
  service_type: 'python' | 'go'
  description: string
  binary_path?: string
  grpc_port?: number
  http_port?: number
  enabled: boolean
  auto_start: boolean
  created_at: string
  updated_at: string
  status?: 'running' | 'stopped' | 'degraded' | 'error'
  health?: 'healthy' | 'unhealthy' | 'unknown'
  pid?: number
  started_at?: string
  last_health_check?: string
  health_check_message?: string
  uptime_seconds?: number
  memory_mb?: number
  cpu_percent?: number
}

export interface ServiceEvent {
  id: number
  service_id: number
  service_name: string
  event_type: 'start' | 'stop' | 'restart' | 'health_check_pass' | 'health_check_fail' | 'error' | 'warning' | 'config_change'
  message?: string
  details?: string
  timestamp: string
}

export interface ServicesResponse {
  success: boolean
  services: Service[]
  count: number
}

export interface ServiceResponse {
  success: boolean
  service: Service
}

export interface ServiceEventsResponse {
  success: boolean
  events: ServiceEvent[]
  count: number
}

export interface ServiceHealthResponse {
  success: boolean
  healthy: boolean
  message: string
}

export interface ServiceActionResponse {
  success: boolean
  message: string
}
