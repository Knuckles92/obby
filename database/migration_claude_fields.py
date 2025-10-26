"""
Database migration: Add Claude-specific metadata fields
========================================================

This migration adds new fields to the semantic_entries table to support
Claude Agent SDK's enhanced metadata structure:
- impact_scope: local | moderate | widespread
- impact_complexity: simple | moderate | complex
- impact_risk: low | medium | high
- change_pattern: High-level change characterization
- relationships: Description of file relationships

The old 'impact' field is kept for backward compatibility and mapped
from impact_scope for legacy code.

Created: October 2025
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def migrate(db_path: str = "obby.db") -> bool:
    """
    Add Claude-specific metadata fields to semantic_entries table.

    Args:
        db_path: Path to SQLite database file

    Returns:
        bool: True if migration successful, False otherwise
    """
    try:
        logger.info("Starting Claude fields migration...")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check if migration already applied
        cursor.execute("PRAGMA table_info(semantic_entries)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'impact_scope' in columns:
            logger.info("Claude fields migration already applied, skipping")
            conn.close()
            return True

        logger.info("Adding new Claude metadata fields to semantic_entries...")

        # Add new columns with default values
        # impact_scope defaults to 'moderate' to match old 'impact' field
        cursor.execute("""
            ALTER TABLE semantic_entries
            ADD COLUMN impact_scope TEXT DEFAULT 'moderate'
            CHECK (impact_scope IN ('local', 'moderate', 'widespread'))
        """)

        cursor.execute("""
            ALTER TABLE semantic_entries
            ADD COLUMN impact_complexity TEXT DEFAULT 'moderate'
            CHECK (impact_complexity IN ('simple', 'moderate', 'complex'))
        """)

        cursor.execute("""
            ALTER TABLE semantic_entries
            ADD COLUMN impact_risk TEXT DEFAULT 'low'
            CHECK (impact_risk IN ('low', 'medium', 'high'))
        """)

        cursor.execute("""
            ALTER TABLE semantic_entries
            ADD COLUMN change_pattern TEXT DEFAULT NULL
        """)

        cursor.execute("""
            ALTER TABLE semantic_entries
            ADD COLUMN relationships TEXT DEFAULT NULL
        """)

        # Migrate existing 'impact' values to 'impact_scope' for consistency
        # brief -> local, moderate -> moderate, significant -> widespread
        cursor.execute("""
            UPDATE semantic_entries
            SET impact_scope = CASE impact
                WHEN 'brief' THEN 'local'
                WHEN 'moderate' THEN 'moderate'
                WHEN 'significant' THEN 'widespread'
                ELSE 'moderate'
            END
            WHERE impact_scope = 'moderate'  -- Only update defaults
        """)

        rows_updated = cursor.rowcount
        logger.info(f"Migrated {rows_updated} existing impact values to impact_scope")

        conn.commit()
        conn.close()

        logger.info("Claude fields migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Claude fields migration failed: {e}", exc_info=True)
        if 'conn' in locals():
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return False


def rollback(db_path: str = "obby.db") -> bool:
    """
    Rollback the Claude fields migration.

    Note: SQLite doesn't support DROP COLUMN until version 3.35.0+
    This rollback creates a new table without the Claude fields and copies data.

    Args:
        db_path: Path to SQLite database file

    Returns:
        bool: True if rollback successful, False otherwise
    """
    try:
        logger.info("Rolling back Claude fields migration...")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if fields exist
        cursor.execute("PRAGMA table_info(semantic_entries)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'impact_scope' not in columns:
            logger.info("Claude fields not present, nothing to rollback")
            conn.close()
            return True

        # Create backup table with original schema
        cursor.execute("""
            CREATE TABLE semantic_entries_rollback AS
            SELECT
                id, version_id, timestamp, date, time, type, summary, impact,
                file_path, searchable_text, markdown_file_path, source_type, created_at
            FROM semantic_entries
        """)

        # Drop current table
        cursor.execute("DROP TABLE semantic_entries")

        # Rename backup to original
        cursor.execute("ALTER TABLE semantic_entries_rollback RENAME TO semantic_entries")

        # Recreate indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_entries_timestamp
            ON semantic_entries(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_entries_date
            ON semantic_entries(date DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_entries_source_type
            ON semantic_entries(source_type)
        """)

        conn.commit()
        conn.close()

        logger.info("Claude fields rollback completed successfully")
        return True

    except Exception as e:
        logger.error(f"Claude fields rollback failed: {e}", exc_info=True)
        if 'conn' in locals():
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return False


if __name__ == "__main__":
    # Set up logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        success = rollback()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
