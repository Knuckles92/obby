"""
Migration: Update Semantic Entries Impact Constraint
====================================================

This migration updates the semantic_entries table to use 'brief' instead of 'minor'
for the impact constraint, aligning with the rest of the codebase.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATION_NAME = "update_semantic_impact_constraint"
MIGRATION_VERSION = "1.0.0"

def apply_migration(db_path: str = ".db/obby.db") -> bool:
    """Apply the semantic impact constraint migration."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if semantic_entries table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='semantic_entries'
            """)
            if not cursor.fetchone():
                logger.info("Semantic entries table does not exist yet, skipping migration")
                return True
            
            # Check if migration already applied by looking for 'brief' in constraint
            # We'll try a test insert with 'brief' to see if constraint allows it
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='semantic_entries'")
            table_sql = cursor.fetchone()[0]
            
            # If the constraint already includes 'brief', migration is done
            if "'brief'" in table_sql and "'minor'" not in table_sql:
                logger.info("Semantic impact constraint already updated to use 'brief', skipping migration")
                return True
            
            logger.info("Applying semantic impact constraint migration...")
            
            # Step 1: Backup existing data
            cursor.execute("""
                CREATE TEMPORARY TABLE semantic_entries_backup AS 
                SELECT * FROM semantic_entries
            """)
            
            rows_backed_up = cursor.execute("SELECT COUNT(*) FROM semantic_entries_backup").fetchone()[0]
            logger.info(f"Backed up {rows_backed_up} semantic entries")
            
            # Step 2: Update any 'minor' values to 'brief' in backup
            cursor.execute("""
                UPDATE semantic_entries_backup 
                SET impact = 'brief' 
                WHERE impact = 'minor'
            """)
            minor_updated = cursor.rowcount
            if minor_updated > 0:
                logger.info(f"Updated {minor_updated} entries from 'minor' to 'brief'")
            
            # Step 3: Drop the old table
            cursor.execute("DROP TABLE semantic_entries")
            
            # Step 4: Recreate table with new constraint
            cursor.execute("""
                CREATE TABLE semantic_entries (
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
                    source_type TEXT DEFAULT 'session_summary',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Step 5: Restore data from backup
            cursor.execute("""
                INSERT INTO semantic_entries 
                SELECT * FROM semantic_entries_backup
            """)
            
            rows_restored = cursor.rowcount
            logger.info(f"Restored {rows_restored} semantic entries")
            
            # Step 6: Recreate indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_entries_timestamp 
                ON semantic_entries(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_entries_file_path 
                ON semantic_entries(file_path)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_entries_type 
                ON semantic_entries(type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_entries_impact 
                ON semantic_entries(impact)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_entries_date 
                ON semantic_entries(date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_entries_searchable 
                ON semantic_entries(searchable_text)
            """)
            
            # Step 7: Drop temporary backup table
            cursor.execute("DROP TABLE semantic_entries_backup")
            
            conn.commit()
            
            # Log successful migration
            cursor.execute("""
                INSERT INTO migration_log (migration_name, success, records_migrated) 
                VALUES (?, TRUE, ?)
            """, (MIGRATION_NAME, rows_restored))
            conn.commit()
            
            logger.info(f"Semantic impact constraint migration completed successfully. {rows_restored} entries migrated.")
            return True
            
    except Exception as e:
        logger.error(f"Failed to apply semantic impact constraint migration: {e}")
        
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

def rollback_migration(db_path: str = ".db/obby.db") -> bool:
    """Rollback the semantic impact constraint migration (not typically needed)."""
    logger.warning("Rollback for semantic impact constraint migration is not supported")
    logger.warning("If needed, restore from backup or recreate table manually")
    return False

if __name__ == "__main__":
    # Can be run directly for testing
    apply_migration()

