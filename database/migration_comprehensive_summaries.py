"""
Migration: Add Comprehensive Summaries Table
============================================

This migration adds support for comprehensive summaries that capture
everything that happened since the last comprehensive summary generation.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATION_NAME = "add_comprehensive_summaries_table"
MIGRATION_VERSION = "1.0.0"

def apply_migration(db_path: str = "obby.db") -> bool:
    """Apply the comprehensive summaries migration."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if migration already applied
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='comprehensive_summaries'
            """)
            if cursor.fetchone():
                logger.info("Comprehensive summaries table already exists, skipping migration")
                return True
            
            logger.info("Applying comprehensive summaries migration...")
            
            # Create comprehensive_summaries table
            cursor.execute("""
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
            """)
            
            # Add indexes for performance
            cursor.execute("""
                CREATE INDEX idx_comprehensive_summaries_timestamp 
                ON comprehensive_summaries(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX idx_comprehensive_summaries_time_range 
                ON comprehensive_summaries(time_range_start, time_range_end)
            """)
            cursor.execute("""
                CREATE INDEX idx_comprehensive_summaries_impact 
                ON comprehensive_summaries(overall_impact)
            """)
            
            # Add configuration for tracking last comprehensive summary
            cursor.execute("""
                INSERT OR IGNORE INTO config_values (key, value, type, description) VALUES
                ('last_comprehensive_summary', ?, 'str', 'Timestamp of last comprehensive summary generation')
            """, (datetime.now().isoformat(),))
            
            cursor.execute("""
                INSERT OR IGNORE INTO config_values (key, value, type, description) VALUES
                ('comprehensive_summary_enabled', 'true', 'bool', 'Enable comprehensive summary generation')
            """)
            
            conn.commit()
            
            # Log successful migration
            cursor.execute("""
                INSERT INTO migration_log (migration_name, success, records_migrated) 
                VALUES (?, TRUE, 0)
            """, (MIGRATION_NAME,))
            conn.commit()
            
            logger.info("Comprehensive summaries migration completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to apply comprehensive summaries migration: {e}")
        
        # Log failed migration
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    INSERT INTO migration_log (migration_name, success, error_message) 
                    VALUES (?, FALSE, ?)
                """, (MIGRATION_NAME, str(e)))
                conn.commit()
        except:
            pass  # Don't fail on logging failure
            
        return False

def rollback_migration(db_path: str = "obby.db") -> bool:
    """Rollback the comprehensive summaries migration."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            logger.info("Rolling back comprehensive summaries migration...")
            
            # Drop table and indexes
            cursor.execute("DROP TABLE IF EXISTS comprehensive_summaries")
            cursor.execute("DROP INDEX IF EXISTS idx_comprehensive_summaries_timestamp")
            cursor.execute("DROP INDEX IF EXISTS idx_comprehensive_summaries_time_range") 
            cursor.execute("DROP INDEX IF EXISTS idx_comprehensive_summaries_impact")
            
            # Remove config values
            cursor.execute("DELETE FROM config_values WHERE key IN ('last_comprehensive_summary', 'comprehensive_summary_enabled')")
            
            conn.commit()
            
            logger.info("Comprehensive summaries migration rolled back successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to rollback comprehensive summaries migration: {e}")
        return False

if __name__ == "__main__":
    # Can be run directly for testing
    apply_migration()