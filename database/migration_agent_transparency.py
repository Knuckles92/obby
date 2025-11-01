"""
Database migration for agent transparency logs
=============================================

This migration adds support for storing detailed agent action logs
to provide transparency about AI operations and file exploration.
"""

import logging
from .models import db

logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the agent transparency migration to the database."""
    try:
        # Check if agent_action_logs table already exists
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='agent_action_logs'
        """
        result = db.execute_query(check_query)

        if result:
            logger.info("Agent action logs table already exists, checking for new columns...")
            # Table exists, check if we need to add new columns
            return add_missing_columns()

        # Create agent_action_logs table
        create_table_query = """
            CREATE TABLE agent_action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                insight_id INTEGER,
                phase TEXT NOT NULL CHECK (phase IN (
                    'data_collection', 'file_exploration', 'analysis', 'generation', 'error'
                )),
                operation TEXT NOT NULL,
                details TEXT,
                files_processed INTEGER DEFAULT 0,
                total_files INTEGER,
                current_file TEXT,
                timing TEXT,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (insight_id) REFERENCES insights(id) ON DELETE SET NULL
            )
        """

        db.execute_update(create_table_query)

        # Create indexes for performance
        indexes = [
            "CREATE INDEX idx_agent_action_logs_session ON agent_action_logs(session_id)",
            "CREATE INDEX idx_agent_action_logs_insight ON agent_action_logs(insight_id)",
            "CREATE INDEX idx_agent_action_logs_phase ON agent_action_logs(phase)",
            "CREATE INDEX idx_agent_action_logs_timestamp ON agent_action_logs(timestamp DESC)"
        ]

        for index_query in indexes:
            db.execute_update(index_query)

        # Add new columns to insights table for enhanced provenance
        add_insights_enhancements()

        logger.info("Agent transparency migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply agent transparency migration: {e}")
        return False


def add_missing_columns():
    """Add missing columns to existing agent_action_logs table."""
    try:
        # Check existing columns
        pragma_query = "PRAGMA table_info(agent_action_logs)"
        existing_columns = db.execute_query(pragma_query)
        column_names = {col['name'] for col in existing_columns}

        # Add missing columns if needed
        alterations = []

        if 'insight_id' not in column_names:
            alterations.append("ALTER TABLE agent_action_logs ADD COLUMN insight_id INTEGER REFERENCES insights(id) ON DELETE SET NULL")

        if 'phase' not in column_names:
            alterations.append("ALTER TABLE agent_action_logs ADD COLUMN phase TEXT CHECK (phase IN ('data_collection', 'file_exploration', 'analysis', 'generation', 'error'))")

        if 'files_processed' not in column_names:
            alterations.append("ALTER TABLE agent_action_logs ADD COLUMN files_processed INTEGER DEFAULT 0")

        if 'total_files' not in column_names:
            alterations.append("ALTER TABLE agent_action_logs ADD COLUMN total_files INTEGER")

        if 'current_file' not in column_names:
            alterations.append("ALTER TABLE agent_action_logs ADD COLUMN current_file TEXT")

        if 'timing' not in column_names:
            alterations.append("ALTER TABLE agent_action_logs ADD COLUMN timing TEXT")

        for alteration in alterations:
            try:
                db.execute_update(alteration)
                logger.info(f"Added missing column: {alteration}")
            except Exception as e:
                logger.warning(f"Failed to add column {alteration}: {e}")

        # Add indexes if they don't exist
        add_missing_indexes()

        # Enhance insights table
        add_insights_enhancements()

        logger.info("Agent transparency columns added successfully")
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
            WHERE type='index' AND name LIKE 'idx_agent_action_logs_%'
        """
        existing_indexes = db.execute_query(index_check_query)
        index_names = {idx['name'] for idx in existing_indexes}

        missing_indexes = [
            ("idx_agent_action_logs_session", "CREATE INDEX IF NOT EXISTS idx_agent_action_logs_session ON agent_action_logs(session_id)"),
            ("idx_agent_action_logs_insight", "CREATE INDEX IF NOT EXISTS idx_agent_action_logs_insight ON agent_action_logs(insight_id)"),
            ("idx_agent_action_logs_phase", "CREATE INDEX IF NOT EXISTS idx_agent_action_logs_phase ON agent_action_logs(phase)"),
            ("idx_agent_action_logs_timestamp", "CREATE INDEX IF NOT EXISTS idx_agent_action_logs_timestamp ON agent_action_logs(timestamp DESC)")
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


def add_insights_enhancements():
    """Add enhanced provenance columns to insights table."""
    try:
        # Check existing columns in insights table
        pragma_query = "PRAGMA table_info(insights)"
        existing_columns = db.execute_query(pragma_query)
        column_names = {col['name'] for col in existing_columns}

        # Add enhanced provenance columns if they don't exist
        alterations = []

        if 'agent_session_id' not in column_names:
            alterations.append("ALTER TABLE insights ADD COLUMN agent_session_id TEXT")

        if 'agent_files_explored' not in column_names:
            alterations.append("ALTER TABLE insights ADD COLUMN agent_files_explored TEXT")

        if 'agent_tools_used' not in column_names:
            alterations.append("ALTER TABLE insights ADD COLUMN agent_tools_used TEXT")

        if 'agent_turns_taken' not in column_names:
            alterations.append("ALTER TABLE insights ADD COLUMN agent_turns_taken INTEGER")

        if 'agent_duration_ms' not in column_names:
            alterations.append("ALTER TABLE insights ADD COLUMN agent_duration_ms INTEGER")

        for alteration in alterations:
            try:
                db.execute_update(alteration)
                logger.info(f"Added insights enhancement: {alteration}")
            except Exception as e:
                logger.warning(f"Failed to add insights enhancement {alteration}: {e}")

        # Add indexes for new columns
        new_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_insights_agent_session ON insights(agent_session_id)",
            "CREATE INDEX IF NOT EXISTS idx_insights_duration ON insights(agent_duration_ms)"
        ]

        for index_query in new_indexes:
            try:
                db.execute_update(index_query)
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")

    except Exception as e:
        logger.warning(f"Failed to add insights enhancements: {e}")


def rollback_migration():
    """Rollback the agent transparency migration (for testing purposes)."""
    try:
        # Drop indexes first
        db.execute_update("DROP INDEX IF EXISTS idx_agent_action_logs_session")
        db.execute_update("DROP INDEX IF EXISTS idx_agent_action_logs_insight")
        db.execute_update("DROP INDEX IF EXISTS idx_agent_action_logs_phase")
        db.execute_update("DROP INDEX IF EXISTS idx_agent_action_logs_timestamp")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_agent_session")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_duration")

        # Drop table
        db.execute_update("DROP TABLE IF EXISTS agent_action_logs")

        # Note: We don't drop the added columns from insights table
        # as SQLite doesn't support DROP COLUMN and this would be complex

        logger.info("Agent transparency migration rollback completed")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback agent transparency migration: {e}")
        return False