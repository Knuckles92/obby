"""
Service Status Service
======================

Manages service monitoring, health checks, and status tracking for all backend services.
"""

import logging
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from database.models import db
import threading

logger = logging.getLogger(__name__)


class ServiceStatusService:
    """Service for managing service status and health monitoring."""

    def __init__(self):
        self.health_check_thread = None
        self.health_check_running = False

    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get all registered services with their current status."""
        try:
            query = """
                SELECT
                    sr.id, sr.name, sr.service_type, sr.description,
                    sr.binary_path, sr.grpc_port, sr.http_port,
                    sr.enabled, sr.auto_start, sr.created_at, sr.updated_at,
                    ss.status, ss.health, ss.pid, ss.started_at,
                    ss.last_health_check, ss.health_check_message,
                    ss.uptime_seconds, ss.memory_mb, ss.cpu_percent
                FROM service_registry sr
                LEFT JOIN service_status ss ON sr.id = ss.service_id
                ORDER BY sr.service_type, sr.name
            """
            services = db.execute_query(query)

            # Convert Row objects to dictionaries for easier manipulation
            services_list = [dict(row) for row in services]

            # For each service, check real-time status if Go launcher is available
            for service in services_list:
                if not service.get('status'):
                    # Initialize status if not exists
                    self._initialize_service_status(service['id'])
                    service['status'] = 'stopped'
                    service['health'] = 'unknown'

                # Update real-time status
                if service['service_type'] == 'python' and service['name'] == 'backend':
                    # Backend is obviously running if we can execute this code
                    service['status'] = 'running'
                    service['health'] = 'healthy'

            return services_list

        except Exception as e:
            logger.error(f"Failed to get all services: {e}")
            return []

    def get_service_by_id(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific service."""
        try:
            query = """
                SELECT
                    sr.id, sr.name, sr.service_type, sr.description,
                    sr.binary_path, sr.grpc_port, sr.http_port,
                    sr.enabled, sr.auto_start, sr.created_at, sr.updated_at,
                    ss.status, ss.health, ss.pid, ss.started_at,
                    ss.last_health_check, ss.health_check_message,
                    ss.uptime_seconds, ss.memory_mb, ss.cpu_percent
                FROM service_registry sr
                LEFT JOIN service_status ss ON sr.id = ss.service_id
                WHERE sr.id = ?
            """
            result = db.execute_query(query, (service_id,))
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to get service {service_id}: {e}")
            return None

    def get_service_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service information by name."""
        try:
            query = """
                SELECT id FROM service_registry WHERE name = ?
            """
            result = db.execute_query(query, (name,))
            if result:
                return self.get_service_by_id(result[0]['id'])
            return None

        except Exception as e:
            logger.error(f"Failed to get service {name}: {e}")
            return None

    def update_service_status(self, service_id: int, status: str, health: str = None,
                              pid: int = None, health_message: str = None) -> bool:
        """Update the status of a service."""
        try:
            # Check if status record exists
            check_query = "SELECT id FROM service_status WHERE service_id = ?"
            existing = db.execute_query(check_query, (service_id,))

            if existing:
                # Update existing record
                update_query = """
                    UPDATE service_status
                    SET status = ?, health = COALESCE(?, health), pid = COALESCE(?, pid),
                        health_check_message = COALESCE(?, health_check_message),
                        last_health_check = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE service_id = ?
                """
                db.execute_update(update_query, (status, health, pid, health_message, service_id))
            else:
                # Insert new record
                insert_query = """
                    INSERT INTO service_status
                    (service_id, status, health, pid, health_check_message, started_at, last_health_check)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                db.execute_update(insert_query, (service_id, status, health or 'unknown', pid, health_message))

            # Log event
            event_type = 'health_check_pass' if health == 'healthy' else 'health_check_fail' if health == 'unhealthy' else 'start' if status == 'running' else 'stop'
            self.log_service_event(service_id, event_type, health_message)

            return True

        except Exception as e:
            logger.error(f"Failed to update service status: {e}")
            return False

    def log_service_event(self, service_id: int, event_type: str, message: str = None, details: str = None) -> bool:
        """Log a service event."""
        try:
            insert_query = """
                INSERT INTO service_events (service_id, event_type, message, details)
                VALUES (?, ?, ?, ?)
            """
            db.execute_update(insert_query, (service_id, event_type, message, details))
            return True

        except Exception as e:
            logger.error(f"Failed to log service event: {e}")
            return False

    def get_service_events(self, service_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent service events."""
        try:
            if service_id:
                query = """
                    SELECT se.*, sr.name as service_name
                    FROM service_events se
                    JOIN service_registry sr ON se.service_id = sr.id
                    WHERE se.service_id = ?
                    ORDER BY se.timestamp DESC
                    LIMIT ?
                """
                return db.execute_query(query, (service_id, limit))
            else:
                query = """
                    SELECT se.*, sr.name as service_name
                    FROM service_events se
                    JOIN service_registry sr ON se.service_id = sr.id
                    ORDER BY se.timestamp DESC
                    LIMIT ?
                """
                return db.execute_query(query, (limit,))

        except Exception as e:
            logger.error(f"Failed to get service events: {e}")
            return []

    def check_service_health(self, service_id: int) -> Dict[str, Any]:
        """Check the health of a specific service."""
        try:
            service = self.get_service_by_id(service_id)
            if not service:
                return {'healthy': False, 'message': 'Service not found'}

            # Backend is always healthy if code is running
            if service['service_type'] == 'python' and service['name'] == 'backend':
                return {'healthy': True, 'message': 'Backend is running'}

            return {'healthy': False, 'message': 'Unknown service type'}

        except Exception as e:
            logger.error(f"Failed to check service health: {e}")
            return {'healthy': False, 'message': str(e)}

    def restart_service(self, service_id: int) -> Dict[str, Any]:
        """Restart a service."""
        try:
            service = self.get_service_by_id(service_id)
            if not service:
                return {'success': False, 'message': 'Service not found'}

            # Log restart event
            self.log_service_event(service_id, 'restart', 'Service restart requested')

            # Backend can't restart itself
            if service['service_type'] == 'python' and service['name'] == 'backend':
                return {'success': False, 'message': 'Cannot restart backend from within itself'}

            return {'success': False, 'message': 'Unknown service type'}

        except Exception as e:
            logger.error(f"Failed to restart service: {e}")
            return {'success': False, 'message': str(e)}

    def stop_service(self, service_id: int) -> Dict[str, Any]:
        """Stop a service."""
        try:
            service = self.get_service_by_id(service_id)
            if not service:
                return {'success': False, 'message': 'Service not found'}

            # Log stop event
            self.log_service_event(service_id, 'stop', 'Service stop requested')

            # Backend can't stop itself
            if service['service_type'] == 'python' and service['name'] == 'backend':
                return {'success': False, 'message': 'Cannot stop backend from within itself'}

            return {'success': False, 'message': 'Unknown service type'}

        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return {'success': False, 'message': str(e)}

    def start_service(self, service_id: int) -> Dict[str, Any]:
        """Start a service."""
        try:
            service = self.get_service_by_id(service_id)
            if not service:
                return {'success': False, 'message': 'Service not found'}

            # Log start event
            self.log_service_event(service_id, 'start', 'Service start requested')

            # Backend is already running
            if service['service_type'] == 'python' and service['name'] == 'backend':
                return {'success': True, 'message': 'Backend is already running'}

            return {'success': False, 'message': 'Unknown service type'}

        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return {'success': False, 'message': str(e)}

    def _initialize_service_status(self, service_id: int):
        """Initialize status record for a service."""
        try:
            check_query = "SELECT id FROM service_status WHERE service_id = ?"
            existing = db.execute_query(check_query, (service_id,))

            if not existing:
                insert_query = """
                    INSERT INTO service_status (service_id, status, health)
                    VALUES (?, 'stopped', 'unknown')
                """
                db.execute_update(insert_query, (service_id,))

        except Exception as e:
            logger.warning(f"Failed to initialize service status: {e}")

    def _check_port_in_use(self, port: int, timeout: float = 0.5) -> bool:
        """Check if a port is in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex(('localhost', port))
                return result == 0  # Port is in use if connection succeeds
        except Exception:
            return False


    def start_health_monitoring(self, interval_seconds: int = 10):
        """Start background health monitoring thread."""
        if self.health_check_running:
            logger.warning("Health monitoring is already running")
            return

        self.health_check_running = True

        def health_check_loop():
            while self.health_check_running:
                try:
                    services = self.get_all_services()
                    for service in services:
                        health_result = self.check_service_health(service['id'])
                        status = 'running' if health_result['healthy'] else 'stopped'
                        health = 'healthy' if health_result['healthy'] else 'unhealthy'
                        self.update_service_status(
                            service['id'],
                            status,
                            health,
                            health_message=health_result['message']
                        )
                except Exception as e:
                    logger.error(f"Error in health check loop: {e}")

                time.sleep(interval_seconds)

        self.health_check_thread = threading.Thread(target=health_check_loop, daemon=True)
        self.health_check_thread.start()
        logger.info(f"Started health monitoring with {interval_seconds}s interval")

    def stop_health_monitoring(self):
        """Stop background health monitoring thread."""
        if self.health_check_running:
            self.health_check_running = False
            if self.health_check_thread:
                self.health_check_thread.join(timeout=5)
            logger.info("Stopped health monitoring")


# Global service instance
_service_status_service: Optional[ServiceStatusService] = None


def get_service_status_service() -> ServiceStatusService:
    """Get or create the global service status service instance."""
    global _service_status_service
    if _service_status_service is None:
        _service_status_service = ServiceStatusService()
    return _service_status_service
