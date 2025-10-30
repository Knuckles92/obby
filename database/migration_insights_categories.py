"""
Database migration to expand insights categories
==================================================

This migration expands the category constraint to support all 10 insight categories:
- action, pattern, relationship, temporal, opportunity
- quality, velocity, risk, documentation, follow-ups
"""

import logging
from .models import db

logger = logging.getLogger(__name__)


def apply_migration():
    """Expand the category constraint in the insights table."""
    try:
        # Check if migration is needed
        # SQLite doesn't allow directly modifying CHECK constraints
        # We need to recreate the table with the new constraint

        # First, check if the table exists and needs migration
        check_query = """
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='insights'
        """
        result = db.execute_query(check_query)

        if not result:
            logger.info("Insights table doesn't exist yet, skipping category migration")
            return True

        table_sql = result[0]['sql']

        # Check if migration already applied
        if 'action' in table_sql and 'pattern' in table_sql:
            logger.info("Category migration already applied, skipping")
            return True

        logger.info("Applying insights category expansion migration...")

        # Create new table with expanded categories
        create_new_table = """
            CREATE TABLE insights_new (
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
        db.execute_update(create_new_table)

        # Copy data from old table to new table
        copy_data = """
            INSERT INTO insights_new
            SELECT * FROM insights
        """
        db.execute_update(copy_data)

        # Drop old table
        db.execute_update("DROP TABLE insights")

        # Rename new table
        db.execute_update("ALTER TABLE insights_new RENAME TO insights")

        # Recreate indexes
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

        # Update configuration
        update_config = """
            UPDATE config_values
            SET value = 'action,pattern,relationship,temporal,opportunity,quality,velocity,risk,documentation,follow-ups'
            WHERE key = 'insights_categories_enabled'
        """
        db.execute_update(update_config)

        logger.info("Insights category expansion migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply category expansion migration: {e}")
        return False


def rollback_migration():
    """Rollback to original 5 categories (for testing purposes)."""
    try:
        logger.info("Rolling back category expansion migration...")

        # Create table with original categories
        create_original_table = """
            CREATE TABLE insights_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL CHECK (category IN ('quality', 'velocity', 'risk', 'documentation', 'follow-ups')),
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
        db.execute_update(create_original_table)

        # Copy only valid category data
        copy_data = """
            INSERT INTO insights_rollback
            SELECT * FROM insights
            WHERE category IN ('quality', 'velocity', 'risk', 'documentation', 'follow-ups')
        """
        db.execute_update(copy_data)

        # Drop current table
        db.execute_update("DROP TABLE insights")

        # Rename rollback table
        db.execute_update("ALTER TABLE insights_rollback RENAME TO insights")

        # Recreate indexes
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

        # Update configuration
        update_config = """
            UPDATE config_values
            SET value = 'quality,velocity,risk,documentation,follow-ups'
            WHERE key = 'insights_categories_enabled'
        """
        db.execute_update(update_config)

        logger.info("Category expansion rollback completed")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback category expansion: {e}")
        return False
