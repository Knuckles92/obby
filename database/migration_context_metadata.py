"""
Migration: Add Context Metadata to Semantic Entries
====================================================

This migration adds context metadata tracking to semantic entries to store
the generation parameters used for each summary (time window, filters, scope, etc.).
"""

import logging
from .models import db

logger = logging.getLogger(__name__)

MIGRATION_NAME = "add_context_metadata_column"
MIGRATION_VERSION = "1.0.0"

def apply_migration() -> bool:
    """Apply the context metadata migration."""
    try:
        # Check if column already exists
        check_query = """
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='semantic_entries'
        """
        result = db.execute_query(check_query)

        if result and 'context_metadata' in result[0]['sql']:
            logger.info("context_metadata column already exists, skipping migration")
            return True

        logger.info("Applying context metadata migration...")

        # Add context_metadata column to semantic_entries table
        # This column stores JSON data with generation parameters:
        # - time_window (preset or custom range)
        # - file_filters (include/exclude patterns)
        # - content_types (what types of content were included)
        # - scope_controls (max files, detail level, focus areas)
        alter_table_query = """
            ALTER TABLE semantic_entries
            ADD COLUMN context_metadata TEXT
        """
        db.execute_update(alter_table_query)

        logger.info("Added context_metadata column to semantic_entries table")

        # Log successful migration
        try:
            log_query = """
                INSERT INTO migration_log (migration_name, success, records_migrated)
                VALUES (?, TRUE, 0)
            """
            db.execute_update(log_query, (MIGRATION_NAME,))
        except Exception as e:
            # migration_log table may not exist, that's okay
            logger.debug(f"Could not log migration to migration_log table: {e}")

        logger.info("Context metadata migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply context metadata migration: {e}")

        # Log failed migration
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
    """Rollback the context metadata migration.

    Note: SQLite does not support DROP COLUMN directly in older versions.
    This rollback creates a new table without the column and copies data over.
    """
    try:
        logger.info("Rolling back context metadata migration...")

        # Create temporary table without context_metadata column
        create_temp_query = """
            CREATE TABLE semantic_entries_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER REFERENCES file_versions(id) ON DELETE CASCADE,
                timestamp DATETIME NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                type TEXT NOT NULL,
                summary TEXT NOT NULL,
                impact TEXT NOT NULL CHECK (impact IN ('brief', 'moderate', 'significant')),
                file_path TEXT NOT NULL,
                searchable_text TEXT NOT NULL,
                markdown_file_path TEXT,
                source_type TEXT DEFAULT 'living_note',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        db.execute_update(create_temp_query)

        # Copy data from old table to temp table (excluding context_metadata)
        copy_data_query = """
            INSERT INTO semantic_entries_temp
            (id, version_id, timestamp, date, time, type, summary, impact,
             file_path, searchable_text, markdown_file_path, source_type, created_at)
            SELECT
            id, version_id, timestamp, date, time, type, summary, impact,
            file_path, searchable_text, markdown_file_path, source_type, created_at
            FROM semantic_entries
        """
        db.execute_update(copy_data_query)

        # Drop old table
        db.execute_update("DROP TABLE semantic_entries")

        # Rename temp table to original name
        db.execute_update("ALTER TABLE semantic_entries_temp RENAME TO semantic_entries")

        # Recreate indexes
        indexes = [
            "CREATE INDEX idx_semantic_timestamp ON semantic_entries(timestamp DESC)",
            "CREATE INDEX idx_semantic_version ON semantic_entries(version_id)",
            "CREATE INDEX idx_semantic_type ON semantic_entries(type)",
            "CREATE INDEX idx_semantic_impact ON semantic_entries(impact)"
        ]

        for index_query in indexes:
            try:
                db.execute_update(index_query)
            except Exception as e:
                logger.warning(f"Failed to recreate index: {e}")

        # Recreate FTS5 triggers
        triggers = [
            """
            CREATE TRIGGER semantic_search_insert AFTER INSERT ON semantic_entries BEGIN
                INSERT INTO semantic_search(rowid, summary, searchable_text)
                VALUES (new.id, new.summary, new.searchable_text);
            END
            """,
            """
            CREATE TRIGGER semantic_search_delete AFTER DELETE ON semantic_entries BEGIN
                DELETE FROM semantic_search WHERE rowid = old.id;
            END
            """,
            """
            CREATE TRIGGER semantic_search_update AFTER UPDATE ON semantic_entries BEGIN
                DELETE FROM semantic_search WHERE rowid = old.id;
                INSERT INTO semantic_search(rowid, summary, searchable_text)
                VALUES (new.id, new.summary, new.searchable_text);
            END
            """
        ]

        for trigger_query in triggers:
            try:
                db.execute_update(trigger_query)
            except Exception as e:
                logger.warning(f"Failed to recreate trigger: {e}")

        logger.info("Context metadata migration rolled back successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback context metadata migration: {e}")
        return False

if __name__ == "__main__":
    # Can be run directly for testing
    apply_migration()
