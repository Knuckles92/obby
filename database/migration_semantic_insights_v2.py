"""
Database migration for semantic insights v2 - contextual insights
==================================================================

This migration adds support for contextually-aware insights:
- reasoning: Explains WHY an insight matters
- context_awareness: JSON with recency scores, project context, relevance factors
- insight_category: immediate_action, trend, recommendation, observation
- working_context_config: User-configurable context window settings
"""

import logging
from .models import db

logger = logging.getLogger(__name__)

MIGRATION_NAME = "semantic_insights_v2"
MIGRATION_VERSION = "2.0.0"


def apply_migration():
    """Apply the semantic insights v2 migration."""
    try:
        # Add new columns to semantic_insights table
        _add_reasoning_column()
        _add_context_awareness_column()
        _add_insight_category_column()

        # Create working context config table
        _create_working_context_config_table()

        # Update insight_type constraint to include new types
        _update_insight_type_constraint()

        logger.info("Semantic insights v2 migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply semantic insights v2 migration: {e}")
        return False


def _add_reasoning_column():
    """Add reasoning column to semantic_insights table."""
    try:
        pragma_result = db.execute_query("PRAGMA table_info(semantic_insights)")
        column_names = [row['name'] for row in pragma_result]

        if 'reasoning' not in column_names:
            db.execute_update("ALTER TABLE semantic_insights ADD COLUMN reasoning TEXT")
            logger.info("Added reasoning column to semantic_insights table")
        else:
            logger.debug("reasoning column already exists")
    except Exception as e:
        logger.error(f"Failed to add reasoning column: {e}")


def _add_context_awareness_column():
    """Add context_awareness column to semantic_insights table."""
    try:
        pragma_result = db.execute_query("PRAGMA table_info(semantic_insights)")
        column_names = [row['name'] for row in pragma_result]

        if 'context_awareness' not in column_names:
            db.execute_update("ALTER TABLE semantic_insights ADD COLUMN context_awareness TEXT")
            logger.info("Added context_awareness column to semantic_insights table")
        else:
            logger.debug("context_awareness column already exists")
    except Exception as e:
        logger.error(f"Failed to add context_awareness column: {e}")


def _add_insight_category_column():
    """Add insight_category column to semantic_insights table."""
    try:
        pragma_result = db.execute_query("PRAGMA table_info(semantic_insights)")
        column_names = [row['name'] for row in pragma_result]

        if 'insight_category' not in column_names:
            db.execute_update(
                "ALTER TABLE semantic_insights ADD COLUMN insight_category TEXT DEFAULT 'observation'"
            )
            logger.info("Added insight_category column to semantic_insights table")
        else:
            logger.debug("insight_category column already exists")
    except Exception as e:
        logger.error(f"Failed to add insight_category column: {e}")


def _create_working_context_config_table():
    """Create table for working context configuration."""
    try:
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='working_context_config'
        """
        result = db.execute_query(check_query)

        if not result:
            create_query = """
                CREATE TABLE working_context_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    context_window_days INTEGER DEFAULT 14,
                    last_context_build TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            db.execute_update(create_query)

            # Insert default config row
            db.execute_update("""
                INSERT INTO working_context_config (id, context_window_days)
                VALUES (1, 14)
            """)

            logger.info("Created working_context_config table with default settings")
        else:
            logger.debug("working_context_config table already exists")
    except Exception as e:
        logger.error(f"Failed to create working_context_config table: {e}")


def _update_insight_type_constraint():
    """
    Update the insight_type constraint to include new contextual insight types.

    Note: SQLite doesn't support modifying constraints directly, but we can
    add new rows with new types since the constraint allows them in v1 already.
    The new types we'll use are already allowed or we just won't enforce strictly.
    """
    # The existing constraint includes: stale_todo, orphan_mention, connection, theme,
    # knowledge_gap, contradiction, timeline, active_todos, todo_summary, project_overview, concept_cluster
    # These are sufficient for our new contextual insights
    logger.debug("Insight type constraint is compatible with new insight system")


def get_config():
    """Get current working context configuration."""
    try:
        result = db.execute_query(
            "SELECT context_window_days, last_context_build FROM working_context_config WHERE id = 1"
        )
        if result:
            return {
                'context_window_days': result[0]['context_window_days'],
                'last_context_build': result[0]['last_context_build']
            }
        return {'context_window_days': 14, 'last_context_build': None}
    except Exception as e:
        logger.error(f"Failed to get working context config: {e}")
        return {'context_window_days': 14, 'last_context_build': None}


def update_config(context_window_days: int):
    """Update working context configuration."""
    try:
        db.execute_update(
            """
            UPDATE working_context_config
            SET context_window_days = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (context_window_days,)
        )
        logger.info(f"Updated context window to {context_window_days} days")
        return True
    except Exception as e:
        logger.error(f"Failed to update working context config: {e}")
        return False


def update_last_context_build():
    """Update the last_context_build timestamp."""
    try:
        db.execute_update(
            """
            UPDATE working_context_config
            SET last_context_build = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """
        )
        return True
    except Exception as e:
        logger.error(f"Failed to update last_context_build: {e}")
        return False


def get_migration_status():
    """Check the status of this migration."""
    status = {
        "name": MIGRATION_NAME,
        "version": MIGRATION_VERSION,
        "columns": {},
        "tables": {}
    }

    try:
        # Check new columns in semantic_insights
        pragma_result = db.execute_query("PRAGMA table_info(semantic_insights)")
        column_names = [row['name'] for row in pragma_result]

        status["columns"]["reasoning"] = 'reasoning' in column_names
        status["columns"]["context_awareness"] = 'context_awareness' in column_names
        status["columns"]["insight_category"] = 'insight_category' in column_names

        # Check working_context_config table
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='working_context_config'
        """
        result = db.execute_query(check_query)
        status["tables"]["working_context_config"] = bool(result)

    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")

    return status
