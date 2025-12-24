"""
Database migration for semantic insights tables
================================================

This migration adds tables for AI-powered semantic insights:
- note_entities: Extracted todos, people, projects, concepts, dates
- note_embeddings: Vector embeddings for similarity search
- note_relationships: Discovered connections between notes
- semantic_insights: Generated insight tiles for display
- semantic_processing_state: Track which notes need reprocessing
- insight_scheduler_runs: Processing history/audit log
"""

import logging
from .models import db

logger = logging.getLogger(__name__)

MIGRATION_NAME = "semantic_insights"
MIGRATION_VERSION = "1.0.0"


def apply_migration():
    """Apply the semantic insights migration to the database."""
    try:
        # Check if semantic_insights table already exists (main table)
        check_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='semantic_insights'
        """
        result = db.execute_query(check_query)

        if result:
            logger.info("Semantic insights tables already exist, checking for updates...")
            return add_missing_tables_and_columns()

        # Create all tables
        create_note_entities_table()
        create_note_embeddings_table()
        create_note_relationships_table()
        create_semantic_insights_table()
        create_semantic_processing_state_table()
        create_insight_scheduler_runs_table()

        # Create all indexes
        create_indexes()

        logger.info("Semantic insights migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply semantic insights migration: {e}")
        return False


def create_note_entities_table():
    """Create table for extracted entities from notes."""
    create_query = """
        CREATE TABLE IF NOT EXISTS note_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_path TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_value TEXT NOT NULL,
            context TEXT,
            status TEXT DEFAULT 'active',
            line_number INTEGER,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (entity_type IN ('todo', 'person', 'project', 'concept', 'date', 'mention', 'tag', 'link')),
            CHECK (status IN ('active', 'completed', 'stale', 'dismissed'))
        )
    """
    db.execute_update(create_query)
    logger.info("Created note_entities table")


def create_note_embeddings_table():
    """Create table for note vector embeddings."""
    create_query = """
        CREATE TABLE IF NOT EXISTS note_embeddings (
            note_path TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            chunk_embeddings TEXT,
            model_version TEXT NOT NULL,
            token_count INTEGER,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    db.execute_update(create_query)
    logger.info("Created note_embeddings table")


def create_note_relationships_table():
    """Create table for discovered relationships between notes."""
    create_query = """
        CREATE TABLE IF NOT EXISTS note_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_note TEXT NOT NULL,
            target_note TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_note, target_note, relationship_type),
            CHECK (relationship_type IN ('similar', 'references', 'continues', 'contradicts', 'related')),
            CHECK (confidence >= 0.0 AND confidence <= 1.0)
        )
    """
    db.execute_update(create_query)
    logger.info("Created note_relationships table")


def create_semantic_insights_table():
    """Create table for generated semantic insights."""
    create_query = """
        CREATE TABLE IF NOT EXISTS semantic_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            source_notes TEXT NOT NULL,
            evidence TEXT,
            confidence REAL DEFAULT 1.0,
            priority INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            user_action TEXT,
            suggested_actions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            viewed_at TIMESTAMP,
            expires_at TIMESTAMP,
            CHECK (insight_type IN ('stale_todo', 'orphan_mention', 'connection', 'theme', 'knowledge_gap', 'contradiction', 'timeline', 'active_todos', 'todo_summary', 'project_overview', 'concept_cluster')),
            CHECK (status IN ('new', 'viewed', 'dismissed', 'pinned', 'actioned')),
            CHECK (confidence >= 0.0 AND confidence <= 1.0)
        )
    """
    db.execute_update(create_query)
    logger.info("Created semantic_insights table")


def create_semantic_processing_state_table():
    """Create table for tracking processing state of notes."""
    create_query = """
        CREATE TABLE IF NOT EXISTS semantic_processing_state (
            note_path TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            last_entity_extraction TIMESTAMP,
            last_embedding_update TIMESTAMP,
            last_relationship_scan TIMESTAMP
        )
    """
    db.execute_update(create_query)
    logger.info("Created semantic_processing_state table")


def create_insight_scheduler_runs_table():
    """Create table for scheduler run history."""
    create_query = """
        CREATE TABLE IF NOT EXISTS insight_scheduler_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            runtime_seconds REAL,
            notes_processed INTEGER,
            insights_generated INTEGER,
            errors TEXT
        )
    """
    db.execute_update(create_query)
    logger.info("Created insight_scheduler_runs table")


def create_indexes():
    """Create indexes for performance."""
    indexes = [
        # note_entities indexes
        "CREATE INDEX IF NOT EXISTS idx_entities_note ON note_entities(note_path)",
        "CREATE INDEX IF NOT EXISTS idx_entities_type ON note_entities(entity_type)",
        "CREATE INDEX IF NOT EXISTS idx_entities_status ON note_entities(status)",
        "CREATE INDEX IF NOT EXISTS idx_entities_value ON note_entities(entity_value)",
        "CREATE INDEX IF NOT EXISTS idx_entities_extracted ON note_entities(extracted_at DESC)",

        # note_relationships indexes
        "CREATE INDEX IF NOT EXISTS idx_relationships_source ON note_relationships(source_note)",
        "CREATE INDEX IF NOT EXISTS idx_relationships_target ON note_relationships(target_note)",
        "CREATE INDEX IF NOT EXISTS idx_relationships_type ON note_relationships(relationship_type)",

        # semantic_insights indexes
        "CREATE INDEX IF NOT EXISTS idx_insights_type ON semantic_insights(insight_type)",
        "CREATE INDEX IF NOT EXISTS idx_insights_status ON semantic_insights(status)",
        "CREATE INDEX IF NOT EXISTS idx_insights_created ON semantic_insights(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_insights_priority ON semantic_insights(priority DESC)",

        # semantic_processing_state indexes
        "CREATE INDEX IF NOT EXISTS idx_processing_hash ON semantic_processing_state(content_hash)",
    ]

    for index_query in indexes:
        try:
            db.execute_update(index_query)
        except Exception as e:
            logger.warning(f"Failed to create index: {e}")

    logger.info(f"Created {len(indexes)} indexes for semantic insights tables")


def add_missing_tables_and_columns():
    """Add any missing tables or columns to existing installation."""
    try:
        tables_to_check = [
            ('note_entities', create_note_entities_table),
            ('note_embeddings', create_note_embeddings_table),
            ('note_relationships', create_note_relationships_table),
            ('semantic_insights', create_semantic_insights_table),
            ('semantic_processing_state', create_semantic_processing_state_table),
            ('insight_scheduler_runs', create_insight_scheduler_runs_table),
        ]

        for table_name, create_func in tables_to_check:
            check_query = f"""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='{table_name}'
            """
            result = db.execute_query(check_query)
            if not result:
                create_func()
                logger.info(f"Created missing table: {table_name}")

        # Update semantic_insights table to support new insight types
        _update_semantic_insights_constraint()

        # Add suggested_actions column if it doesn't exist
        _add_suggested_actions_column()

        # Ensure all indexes exist
        create_indexes()

        logger.info("Semantic insights tables updated successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to update semantic insights tables: {e}")
        return False


def _add_suggested_actions_column():
    """Add suggested_actions column to semantic_insights table if it doesn't exist."""
    try:
        # Check if column already exists
        pragma_result = db.execute_query("PRAGMA table_info(semantic_insights)")
        column_names = [row['name'] for row in pragma_result]
        
        if 'suggested_actions' not in column_names:
            db.execute_update("ALTER TABLE semantic_insights ADD COLUMN suggested_actions TEXT")
            logger.info("Added suggested_actions column to semantic_insights table")
        else:
            logger.debug("suggested_actions column already exists")
    except Exception as e:
        logger.error(f"Failed to add suggested_actions column: {e}")


def _update_semantic_insights_constraint():
    """Update the CHECK constraint on semantic_insights to allow new insight types."""
    try:
        # Check if table needs updating by looking at schema
        schema_result = db.execute_query(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='semantic_insights'"
        )
        if not schema_result:
            return  # Table doesn't exist, will be created fresh

        current_schema = schema_result[0]['sql']

        # Check if new insight types are already in the constraint
        if 'active_todos' in current_schema:
            logger.debug("semantic_insights table already has updated constraint")
            return

        # Need to recreate table with new constraint
        # First, backup any existing data
        count_result = db.execute_query("SELECT COUNT(*) as cnt FROM semantic_insights")
        row_count = count_result[0]['cnt'] if count_result else 0

        if row_count > 0:
            # Backup data to temp table
            db.execute_update("CREATE TABLE semantic_insights_backup AS SELECT * FROM semantic_insights")

        # Drop old table and indexes
        db.execute_update("DROP INDEX IF EXISTS idx_insights_type")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_status")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_created")
        db.execute_update("DROP INDEX IF EXISTS idx_insights_priority")
        db.execute_update("DROP TABLE semantic_insights")

        # Create new table with updated constraint
        create_semantic_insights_table()

        if row_count > 0:
            # Restore data
            db.execute_update("""
                INSERT INTO semantic_insights
                SELECT * FROM semantic_insights_backup
            """)
            db.execute_update("DROP TABLE semantic_insights_backup")

        logger.info("Updated semantic_insights table with new insight type constraint")

    except Exception as e:
        logger.error(f"Failed to update semantic_insights constraint: {e}")


def rollback_migration():
    """Rollback the semantic insights migration (for testing purposes)."""
    try:
        # Drop indexes first
        indexes_to_drop = [
            "idx_entities_note", "idx_entities_type", "idx_entities_status",
            "idx_entities_value", "idx_entities_extracted",
            "idx_relationships_source", "idx_relationships_target", "idx_relationships_type",
            "idx_insights_type", "idx_insights_status", "idx_insights_created", "idx_insights_priority",
            "idx_processing_hash"
        ]

        for index_name in indexes_to_drop:
            db.execute_update(f"DROP INDEX IF EXISTS {index_name}")

        # Drop tables
        tables_to_drop = [
            "note_entities",
            "note_embeddings",
            "note_relationships",
            "semantic_insights",
            "semantic_processing_state",
            "insight_scheduler_runs"
        ]

        for table_name in tables_to_drop:
            db.execute_update(f"DROP TABLE IF EXISTS {table_name}")

        logger.info("Semantic insights migration rollback completed")
        return True

    except Exception as e:
        logger.error(f"Failed to rollback semantic insights migration: {e}")
        return False


def get_migration_status():
    """Check the status of this migration."""
    status = {
        "name": MIGRATION_NAME,
        "version": MIGRATION_VERSION,
        "tables": {}
    }

    tables = [
        "note_entities",
        "note_embeddings",
        "note_relationships",
        "semantic_insights",
        "semantic_processing_state",
        "insight_scheduler_runs"
    ]

    for table_name in tables:
        check_query = f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{table_name}'
        """
        result = db.execute_query(check_query)
        status["tables"][table_name] = bool(result)

    return status
