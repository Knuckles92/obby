"""
Database migration for insights table
====================================

This migration creates the insights table for storing AI-generated insights
from various data sources in the Obby system.
"""

import logging
from .models import db

logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the insights table migration to the database."""
    try:
        # Check if insights table already exists
        check_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='insights'
        """
        result = db.execute_query(check_query)
        
        if result:
            logger.info("Insights table already exists, skipping migration")
            return True
        
        # Create insights table with all supported categories
        create_table_query = """
            CREATE TABLE insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL CHECK (category IN (
                    'action', 'pattern', 'relationship', 'temporal', 'opportunity',
                    'quality', 'velocity', 'risk', 'documentation', 'follow-ups'
                )),
                priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                evidence_payload TEXT,
                related_entities TEXT,
                source_section TEXT NOT NULL,
                source_pointers TEXT,
                generated_by_agent TEXT,
                dismissal_flag BOOLEAN DEFAULT FALSE,
                archive_flag BOOLEAN DEFAULT FALSE,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        db.execute_update(create_table_query)
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX idx_insights_category ON insights(category)",
            "CREATE INDEX idx_insights_priority ON insights(priority)",
            "CREATE INDEX idx_insights_timestamp ON insights(timestamp DESC)",
            "CREATE INDEX idx_insights_source_section ON insights(source_section)",
            "CREATE INDEX idx_insights_dismissal ON insights(dismissal_flag)",
            "CREATE INDEX idx_insights_archive ON insights(archive_flag)"
        ]
        
        for index_query in indexes:
            db.execute_update(index_query)
        
        # Add configuration for insights
        config_updates = [
            ('insights_enabled', 'true', 'bool', 'Enable insights generation'),
            ('insights_max_age_days', '30', 'int', 'Maximum age of insights to keep'),
            ('insights_refresh_interval', '3600', 'int', 'Insights refresh interval in seconds'),
            ('insights_categories_enabled', 'action,pattern,relationship,temporal,opportunity,quality,velocity,risk,documentation,follow-ups', 'str', 'Enabled insight categories'),
            ('insights_agent_model', 'sonnet', 'str', 'AI model for insights generation')
        ]
        
        for key, value, value_type, description in config_updates:
            try:
                # Check if config exists first
                check_config = "SELECT key FROM config_values WHERE key = ?"
                existing = db.execute_query(check_config, (key,))
                
                if not existing:
                    insert_query = """
                        INSERT INTO config_values (key, value, type, description)
                        VALUES (?, ?, ?, ?)
                    """
                    db.execute_update(insert_query, (key, value, value_type, description))
            except Exception as e:
                logger.warning(f"Failed to insert config {key}: {e}")
        
        logger.info("Insights table migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply insights migration: {e}")
        return False


def rollback_migration():
    """Rollback the insights table migration (for testing purposes)."""
    try:
        # Drop indexes first
        db.execute_update("DROP INDEX IF EXISTS idx_insights_category")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_priority")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_timestamp")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_source_section")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_dismissal")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_archive")
        
        # Drop table
        db.execute_update("DROP TABLE IF EXISTS insights")
        
        # Remove config entries
        config_keys = [
            'insights_enabled',
            'insights_max_age_days',
            'insights_refresh_interval',
            'insights_categories_enabled',
            'insights_agent_model'
        ]
        
        placeholders = ','.join(['?' for _ in config_keys])
        db.execute_update(f"DELETE FROM config_values WHERE key IN ({placeholders})", config_keys)
        
        logger.info("Insights migration rollback completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rollback insights migration: {e}")
        return False