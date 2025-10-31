"""
Migration: Add Comprehensive Summaries Table
============================================

This migration adds support for comprehensive summaries that capture
everything that happened since the last comprehensive summary generation.
"""

import logging
from datetime import datetime
from .models import db

logger = logging.getLogger(__name__)

MIGRATION_NAME = "add_comprehensive_summaries_table"
MIGRATION_VERSION = "1.0.0"

def apply_migration() -> bool:
    """Apply the comprehensive summaries migration."""
    try:
        # Check if migration already applied
        check_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='comprehensive_summaries'
        """
        result = db.execute_query(check_query)
        
        if result:
            logger.info("Comprehensive summaries table already exists, skipping migration")
            return True
        
        logger.info("Applying comprehensive summaries migration...")
        
        # Create comprehensive_summaries table
        create_table_query = """
            CREATE TABLE comprehensive_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                time_range_start DATETIME NOT NULL,
                time_range_end DATETIME NOT NULL,
                summary_content TEXT NOT NULL,
                key_topics TEXT, -- JSON array of topics
                key_keywords TEXT, -- JSON array of keywords  
                overall_impact TEXT NOT NULL CHECK (overall_impact IN ('brief', 'moderate', 'significant')),
                files_affected_count INTEGER DEFAULT 0,
                changes_count INTEGER DEFAULT 0,
                time_span TEXT, -- Human readable time span
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        db.execute_update(create_table_query)
        
        # Add indexes for performance
        indexes = [
            "CREATE INDEX idx_comprehensive_summaries_timestamp ON comprehensive_summaries(timestamp DESC)",
            "CREATE INDEX idx_comprehensive_summaries_time_range ON comprehensive_summaries(time_range_start, time_range_end)",
            "CREATE INDEX idx_comprehensive_summaries_impact ON comprehensive_summaries(overall_impact)"
        ]
        
        for index_query in indexes:
            db.execute_update(index_query)
        
        # Add configuration for tracking last comprehensive summary
        config_updates = [
            ('last_comprehensive_summary', datetime.now().isoformat(), 'str', 'Timestamp of last comprehensive summary generation'),
            ('comprehensive_summary_enabled', 'true', 'bool', 'Enable comprehensive summary generation')
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
        
        # Log successful migration (if migration_log table exists)
        try:
            log_query = """
                INSERT INTO migration_log (migration_name, success, records_migrated) 
                VALUES (?, TRUE, 0)
            """
            db.execute_update(log_query, (MIGRATION_NAME,))
        except Exception as e:
            # migration_log table may not exist, that's okay
            logger.debug(f"Could not log migration to migration_log table: {e}")
        
        logger.info("Comprehensive summaries migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply comprehensive summaries migration: {e}")
        
        # Log failed migration (if migration_log table exists)
        try:
            log_query = """
                INSERT INTO migration_log (migration_name, success, error_message) 
                VALUES (?, FALSE, ?)
            """
            db.execute_update(log_query, (MIGRATION_NAME, str(e)))
        except Exception:
            # Don't fail on logging failure
            pass
            
        return False

def rollback_migration() -> bool:
    """Rollback the comprehensive summaries migration."""
    try:
        logger.info("Rolling back comprehensive summaries migration...")
        
        # Drop indexes first
        db.execute_update("DROP INDEX IF EXISTS idx_comprehensive_summaries_timestamp")
        db.execute_update("DROP INDEX IF EXISTS idx_comprehensive_summaries_time_range")
        db.execute_update("DROP INDEX IF EXISTS idx_comprehensive_summaries_impact")
        
        # Drop table
        db.execute_update("DROP TABLE IF EXISTS comprehensive_summaries")
        
        # Remove config values
        config_keys = ['last_comprehensive_summary', 'comprehensive_summary_enabled']
        placeholders = ','.join(['?' for _ in config_keys])
        db.execute_update(f"DELETE FROM config_values WHERE key IN ({placeholders})", config_keys)
        
        logger.info("Comprehensive summaries migration rolled back successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rollback comprehensive summaries migration: {e}")
        return False

if __name__ == "__main__":
    # Can be run directly for testing
    apply_migration()