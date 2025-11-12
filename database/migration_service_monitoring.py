"""
Database migration for service monitoring and management
========================================================

This migration adds support for tracking and managing Go microservices
with real-time status monitoring, health checks, and event logging.
"""

import logging
from .models import db

logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the service monitoring migration to the database."""
    try:
        # Check if service_registry table already exists
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='service_registry'
        """
        result = db.execute_query(check_query)

        if result:
            logger.info("Service monitoring tables already exist, checking for new columns...")
            return add_missing_columns()

        # Create service_registry table
        create_registry_query = """
            CREATE TABLE service_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                service_type TEXT NOT NULL CHECK (service_type IN ('python', 'go')),
                description TEXT,
                binary_path TEXT,
                grpc_port INTEGER,
                http_port INTEGER,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                auto_start BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """

        db.execute_update(create_registry_query)

        # Create service_status table
        create_status_query = """
            CREATE TABLE service_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('running', 'stopped', 'degraded', 'error')),
                health TEXT CHECK (health IN ('healthy', 'unhealthy', 'unknown')),
                pid INTEGER,
                started_at DATETIME,
                last_health_check DATETIME,
                health_check_message TEXT,
                uptime_seconds INTEGER DEFAULT 0,
                memory_mb REAL,
                cpu_percent REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES service_registry(id) ON DELETE CASCADE
            )
        """

        db.execute_update(create_status_query)

        # Create service_events table
        create_events_query = """
            CREATE TABLE service_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN (
                    'start', 'stop', 'restart', 'health_check_pass', 'health_check_fail',
                    'error', 'warning', 'config_change'
                )),
                message TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES service_registry(id) ON DELETE CASCADE
            )
        """

        db.execute_update(create_events_query)

        # Create service_metrics table
        create_metrics_query = """
            CREATE TABLE service_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                unit TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES service_registry(id) ON DELETE CASCADE
            )
        """

        db.execute_update(create_metrics_query)

        # Create indexes for performance
        indexes = [
            # Service registry indexes
            "CREATE INDEX idx_service_registry_name ON service_registry(name)",
            "CREATE INDEX idx_service_registry_type ON service_registry(service_type)",
            "CREATE INDEX idx_service_registry_enabled ON service_registry(enabled)",

            # Service status indexes
            "CREATE INDEX idx_service_status_service ON service_status(service_id)",
            "CREATE INDEX idx_service_status_status ON service_status(status)",
            "CREATE INDEX idx_service_status_health ON service_status(health)",
            "CREATE INDEX idx_service_status_updated ON service_status(updated_at DESC)",

            # Service events indexes
            "CREATE INDEX idx_service_events_service ON service_events(service_id)",
            "CREATE INDEX idx_service_events_type ON service_events(event_type)",
            "CREATE INDEX idx_service_events_timestamp ON service_events(timestamp DESC)",

            # Service metrics indexes
            "CREATE INDEX idx_service_metrics_service ON service_metrics(service_id)",
            "CREATE INDEX idx_service_metrics_name ON service_metrics(metric_name)",
            "CREATE INDEX idx_service_metrics_timestamp ON service_metrics(timestamp DESC)"
        ]

        for index_query in indexes:
            db.execute_update(index_query)

        # Populate default services
        populate_default_services()

        logger.info("Service monitoring migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply service monitoring migration: {e}")
        return False


def populate_default_services():
    """Populate the service registry with default services."""
    try:
        default_services = [
            # Python backend (always running if you can query the database)
            {
                'name': 'backend',
                'service_type': 'python',
                'description': 'FastAPI backend server',
                'grpc_port': None,
                'http_port': 8001,
                'enabled': 1,
                'auto_start': 1
            },
            # Go File Watcher
            {
                'name': 'file-watcher',
                'service_type': 'go',
                'description': 'Real-time file monitoring service',
                'binary_path': 'go-services/file-watcher',
                'grpc_port': 50051,
                'http_port': None,
                'enabled': 1,
                'auto_start': 1
            },
            # Go Content Tracker
            {
                'name': 'content-tracker',
                'service_type': 'go',
                'description': 'Content hashing and diff generation service',
                'binary_path': 'go-services/content-tracker',
                'grpc_port': 50052,
                'http_port': None,
                'enabled': 1,
                'auto_start': 1
            },
            # Go Query Service
            {
                'name': 'query-service',
                'service_type': 'go',
                'description': 'High-performance database query service',
                'binary_path': 'go-services/query-service',
                'grpc_port': 50053,
                'http_port': None,
                'enabled': 1,
                'auto_start': 1
            },
            # Go SSE Hub
            {
                'name': 'sse-hub',
                'service_type': 'go',
                'description': 'Server-Sent Events hub for real-time updates',
                'binary_path': 'go-services/sse-hub',
                'grpc_port': 50054,
                'http_port': 8080,
                'enabled': 1,
                'auto_start': 1
            }
        ]

        for service in default_services:
            # Check if service already exists
            check_query = "SELECT id FROM service_registry WHERE name = ?"
            existing = db.execute_query(check_query, (service['name'],))

            if not existing:
                insert_query = """
                    INSERT INTO service_registry
                    (name, service_type, description, binary_path, grpc_port, http_port, enabled, auto_start)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                db.execute_update(insert_query, (
                    service['name'],
                    service['service_type'],
                    service['description'],
                    service.get('binary_path'),
                    service.get('grpc_port'),
                    service.get('http_port'),
                    service['enabled'],
                    service['auto_start']
                ))
                logger.info(f"Added service to registry: {service['name']}")

        logger.info("Default services populated successfully")

    except Exception as e:
        logger.warning(f"Failed to populate default services: {e}")


def add_missing_columns():
    """Add missing columns to existing service monitoring tables."""
    try:
        tables_to_check = [
            ('service_registry', [
                ('description', "ALTER TABLE service_registry ADD COLUMN description TEXT"),
                ('enabled', "ALTER TABLE service_registry ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT 1"),
                ('auto_start', "ALTER TABLE service_registry ADD COLUMN auto_start BOOLEAN NOT NULL DEFAULT 1"),
                ('updated_at', "ALTER TABLE service_registry ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            ]),
            ('service_status', [
                ('memory_mb', "ALTER TABLE service_status ADD COLUMN memory_mb REAL"),
                ('cpu_percent', "ALTER TABLE service_status ADD COLUMN cpu_percent REAL"),
                ('health_check_message', "ALTER TABLE service_status ADD COLUMN health_check_message TEXT")
            ])
        ]

        for table_name, columns in tables_to_check:
            # Check existing columns
            pragma_query = f"PRAGMA table_info({table_name})"
            existing_columns = db.execute_query(pragma_query)
            column_names = {col['name'] for col in existing_columns}

            # Add missing columns
            for col_name, alteration in columns:
                if col_name not in column_names:
                    try:
                        db.execute_update(alteration)
                        logger.info(f"Added missing column {col_name} to {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to add column {col_name} to {table_name}: {e}")

        # Add missing indexes
        add_missing_indexes()

        # Ensure default services are populated
        populate_default_services()

        logger.info("Service monitoring columns added successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to add missing columns: {e}")
        return False


def add_missing_indexes():
    """Add missing indexes for performance."""
    try:
        # Check if indexes exist
        index_check_query = """
            SELECT name FROM sqlite_master
            WHERE type='index' AND (
                name LIKE 'idx_service_registry_%' OR
                name LIKE 'idx_service_status_%' OR
                name LIKE 'idx_service_events_%' OR
                name LIKE 'idx_service_metrics_%'
            )
        """
        existing_indexes = db.execute_query(index_check_query)
        index_names = {idx['name'] for idx in existing_indexes}

        missing_indexes = [
            ("idx_service_registry_name", "CREATE INDEX IF NOT EXISTS idx_service_registry_name ON service_registry(name)"),
            ("idx_service_registry_type", "CREATE INDEX IF NOT EXISTS idx_service_registry_type ON service_registry(service_type)"),
            ("idx_service_registry_enabled", "CREATE INDEX IF NOT EXISTS idx_service_registry_enabled ON service_registry(enabled)"),
            ("idx_service_status_service", "CREATE INDEX IF NOT EXISTS idx_service_status_service ON service_status(service_id)"),
            ("idx_service_status_status", "CREATE INDEX IF NOT EXISTS idx_service_status_status ON service_status(status)"),
            ("idx_service_status_health", "CREATE INDEX IF NOT EXISTS idx_service_status_health ON service_status(health)"),
            ("idx_service_status_updated", "CREATE INDEX IF NOT EXISTS idx_service_status_updated ON service_status(updated_at DESC)"),
            ("idx_service_events_service", "CREATE INDEX IF NOT EXISTS idx_service_events_service ON service_events(service_id)"),
            ("idx_service_events_type", "CREATE INDEX IF NOT EXISTS idx_service_events_type ON service_events(event_type)"),
            ("idx_service_events_timestamp", "CREATE INDEX IF NOT EXISTS idx_service_events_timestamp ON service_events(timestamp DESC)"),
            ("idx_service_metrics_service", "CREATE INDEX IF NOT EXISTS idx_service_metrics_service ON service_metrics(service_id)"),
            ("idx_service_metrics_name", "CREATE INDEX IF NOT EXISTS idx_service_metrics_name ON service_metrics(metric_name)"),
            ("idx_service_metrics_timestamp", "CREATE INDEX IF NOT EXISTS idx_service_metrics_timestamp ON service_metrics(timestamp DESC)")
        ]

        for index_name, index_query in missing_indexes:
            if index_name not in index_names:
                try:
                    db.execute_update(index_query)
                    logger.info(f"Added missing index: {index_name}")
                except Exception as e:
                    logger.warning(f"Failed to add index {index_name}: {e}")

    except Exception as e:
        logger.warning(f"Failed to add missing indexes: {e}")


def rollback_migration():
    """Rollback the service monitoring migration (for testing purposes)."""
    try:
        # Drop indexes first
        db.execute_update("DROP INDEX IF EXISTS idx_service_registry_name")
        db.execute_update("DROP INDEX IF EXISTS idx_service_registry_type")
        db.execute_update("DROP INDEX IF EXISTS idx_service_registry_enabled")
        db.execute_update("DROP INDEX IF EXISTS idx_service_status_service")
        db.execute_update("DROP INDEX IF EXISTS idx_service_status_status")
        db.execute_update("DROP INDEX IF EXISTS idx_service_status_health")
        db.execute_update("DROP INDEX IF EXISTS idx_service_status_updated")
        db.execute_update("DROP INDEX IF EXISTS idx_service_events_service")
        db.execute_update("DROP INDEX IF EXISTS idx_service_events_type")
        db.execute_update("DROP INDEX IF EXISTS idx_service_events_timestamp")
        db.execute_update("DROP INDEX IF EXISTS idx_service_metrics_service")
        db.execute_update("DROP INDEX IF EXISTS idx_service_metrics_name")
        db.execute_update("DROP INDEX IF EXISTS idx_service_metrics_timestamp")

        # Drop tables (order matters due to foreign keys)
        db.execute_update("DROP TABLE IF EXISTS service_metrics")
        db.execute_update("DROP TABLE IF EXISTS service_events")
        db.execute_update("DROP TABLE IF EXISTS service_status")
        db.execute_update("DROP TABLE IF EXISTS service_registry")

        logger.info("Service monitoring migration rollback completed")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback service monitoring migration: {e}")
        return False
