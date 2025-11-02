"""
Database migration for insights layout configuration
====================================================

This migration adds support for storing user-configurable layout preferences
for the insights page, allowing users to customize which insights appear
in each layout view and their positioning.
"""

import logging
from .models import db

logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the insights layout configuration migration to the database."""
    try:
        # Check if insights_layout_config table already exists
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='insights_layout_config'
        """
        result = db.execute_query(check_query)

        if result:
            logger.info("Insights layout config table already exists, checking for new columns...")
            return add_missing_columns()

        # Create insights_layout_config table
        create_table_query = """
            CREATE TABLE insights_layout_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layout_name TEXT NOT NULL UNIQUE,
                insight_cards TEXT NOT NULL,
                default_date_range TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """

        db.execute_update(create_table_query)

        # Create indexes for performance
        indexes = [
            "CREATE INDEX idx_insights_layout_name ON insights_layout_config(layout_name)",
            "CREATE INDEX idx_insights_layout_updated ON insights_layout_config(updated_at DESC)"
        ]

        for index_query in indexes:
            db.execute_update(index_query)

        # Insert default configurations for common layouts
        insert_defaults()

        logger.info("Insights layout configuration migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply insights layout configuration migration: {e}")
        return False


def add_missing_columns():
    """Add missing columns to existing insights_layout_config table."""
    try:
        # Check existing columns
        pragma_query = "PRAGMA table_info(insights_layout_config)"
        existing_columns = db.execute_query(pragma_query)
        column_names = {col['name'] for col in existing_columns}

        # Add missing columns if needed
        alterations = []

        if 'default_date_range' not in column_names:
            alterations.append("ALTER TABLE insights_layout_config ADD COLUMN default_date_range TEXT")

        if 'created_at' not in column_names:
            alterations.append("ALTER TABLE insights_layout_config ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")

        if 'updated_at' not in column_names:
            alterations.append("ALTER TABLE insights_layout_config ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")

        for alteration in alterations:
            try:
                db.execute_update(alteration)
                logger.info(f"Added missing column: {alteration}")
            except Exception as e:
                logger.warning(f"Failed to add column {alteration}: {e}")

        # Add indexes if they don't exist
        add_missing_indexes()

        logger.info("Insights layout configuration columns added successfully")
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
            WHERE type='index' AND name LIKE 'idx_insights_layout_%'
        """
        existing_indexes = db.execute_query(index_check_query)
        index_names = {idx['name'] for idx in existing_indexes}

        missing_indexes = [
            ("idx_insights_layout_name", "CREATE INDEX IF NOT EXISTS idx_insights_layout_name ON insights_layout_config(layout_name)"),
            ("idx_insights_layout_updated", "CREATE INDEX IF NOT EXISTS idx_insights_layout_updated ON insights_layout_config(updated_at DESC)")
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


def insert_defaults():
    """Insert default configurations for common layouts."""
    import json

    default_configs = {
        "masonry": {
            "insights": [
                {"id": "file_activity", "position": 0, "enabled": True},
                {"id": "peak_activity", "position": 1, "enabled": True},
                {"id": "code_metrics", "position": 2, "enabled": True},
                {"id": "trending_files", "position": 3, "enabled": True},
            ],
            "default_date_range": "7d"  # 7 days
        },
        "dashboard": {
            "insights": [
                {"id": "file_activity", "position": 0, "enabled": True},
                {"id": "peak_activity", "position": 1, "enabled": True},
                {"id": "code_metrics", "position": 2, "enabled": True},
                {"id": "trending_files", "position": 3, "enabled": True},
            ],
            "default_date_range": "7d"
        },
        "minimalist": {
            "insights": [
                {"id": "file_activity", "position": 0, "enabled": True},
                {"id": "peak_activity", "position": 1, "enabled": True},
            ],
            "default_date_range": "1d"  # 1 day
        },
        "timeline": {
            "insights": [
                {"id": "file_activity", "position": 0, "enabled": True},
                {"id": "peak_activity", "position": 1, "enabled": True},
                {"id": "trending_files", "position": 2, "enabled": True},
            ],
            "default_date_range": "1d"
        },
    }

    try:
        for layout_name, config in default_configs.items():
            insight_cards_json = json.dumps(config["insights"])
            default_date_range = config.get("default_date_range", "7d")

            insert_query = """
                INSERT OR IGNORE INTO insights_layout_config (layout_name, insight_cards, default_date_range)
                VALUES (?, ?, ?)
            """
            db.execute_update(insert_query, (layout_name, insight_cards_json, default_date_range))

        logger.info(f"Inserted default configurations for {len(default_configs)} layouts")

    except Exception as e:
        logger.warning(f"Failed to insert default configurations: {e}")


def rollback_migration():
    """Rollback the insights layout configuration migration (for testing purposes)."""
    try:
        # Drop indexes first
        db.execute_update("DROP INDEX IF EXISTS idx_insights_layout_name")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_layout_updated")

        # Drop table
        db.execute_update("DROP TABLE IF EXISTS insights_layout_config")

        logger.info("Insights layout configuration migration rollback completed")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback insights layout configuration migration: {e}")
        return False
