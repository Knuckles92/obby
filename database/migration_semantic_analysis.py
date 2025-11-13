"""
Database migration for semantic_analysis table
================================================

This migration adds the semantic_analysis table for backward compatibility
with legacy tests and code that expects this table structure.
"""

import logging
from .models import db

logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the semantic_analysis table migration."""
    try:
        # Check if semantic_analysis table already exists
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='semantic_analysis'
        """
        result = db.execute_query(check_query)

        if result:
            logger.info("semantic_analysis table already exists, skipping migration")
            return True

        logger.info("Creating semantic_analysis table...")

        # Create semantic_analysis table
        create_table_query = """
            CREATE TABLE semantic_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                summary TEXT NOT NULL,
                topics TEXT,
                keywords TEXT,
                impact_level TEXT CHECK (impact_level IN ('brief', 'moderate', 'significant')),
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, content_hash)
            )
        """
        db.execute_update(create_table_query)

        # Create indexes for performance
        indexes = [
            "CREATE INDEX idx_semantic_analysis_file_path ON semantic_analysis(file_path)",
            "CREATE INDEX idx_semantic_analysis_timestamp ON semantic_analysis(timestamp DESC)",
            "CREATE INDEX idx_semantic_analysis_impact ON semantic_analysis(impact_level)"
        ]

        for index_query in indexes:
            db.execute_update(index_query)

        # Log successful migration
        try:
            log_query = """
                INSERT INTO migration_log (migration_name, success, records_migrated)
                VALUES (?, TRUE, 0)
            """
            db.execute_update(log_query, ('add_semantic_analysis_table',))
        except Exception as e:
            logger.debug(f"Could not log migration: {e}")

        logger.info("semantic_analysis table migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply semantic_analysis migration: {e}")

        # Log failed migration
        try:
            log_query = """
                INSERT INTO migration_log (migration_name, success, error_message)
                VALUES (?, FALSE, ?)
            """
            db.execute_update(log_query, ('add_semantic_analysis_table', str(e)))
        except Exception:
            pass

        return False


def rollback_migration():
    """Rollback the semantic_analysis table migration."""
    try:
        logger.info("Rolling back semantic_analysis table migration...")

        # Drop indexes first
        db.execute_update("DROP INDEX IF EXISTS idx_semantic_analysis_file_path")
        db.execute_update("DROP INDEX IF EXISTS idx_semantic_analysis_timestamp")
        db.execute_update("DROP INDEX IF EXISTS idx_semantic_analysis_impact")

        # Drop table
        db.execute_update("DROP TABLE IF EXISTS semantic_analysis")

        logger.info("semantic_analysis table migration rolled back successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback semantic_analysis migration: {e}")
        return False


if __name__ == "__main__":
    # Can be run directly for testing
    apply_migration()
