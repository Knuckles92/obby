"""
File-Based Database Models & Infrastructure
============================================

High-performance database layer with connection pooling, transactions, 
and file-system-focused models for Obby's pure file monitoring.
"""

import sqlite3
import threading
import json
import hashlib
import difflib
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import logging
import time

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Thread-safe SQLite connection manager with connection pooling."""
    
    def __init__(self, db_path: str = ".db/obby.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.schema_path = Path(__file__).parent / "schema.sql"
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists and schema is applied."""
        if not Path(self.db_path).exists():
            logger.info(f"Creating new database: {self.db_path}")
            self._create_database()
        else:
            logger.info(f"Using existing database: {self.db_path}")
    
    def _create_database(self):
        """Create database with schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.schema_path.read_text(encoding='utf-8'))
            logger.info("Database schema applied successfully")
    
    @contextmanager
    def get_connection(self):
        """Get thread-local database connection with automatic cleanup."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        
        try:
            yield self._local.connection
        except Exception as e:
            self._local.connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute SELECT query and return results."""
        with self.get_connection() as conn:
            t0 = time.perf_counter()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            dt = time.perf_counter() - t0
            # Log only the first line of the query to keep logs concise
            first_line = query.strip().splitlines()[0] if query else ""
            logger.info(f"DB timing: execute_query {dt:.3f}s rows={len(rows)} | {first_line[:120]}")
            return rows
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows."""
        with self.get_connection() as conn:
            t0 = time.perf_counter()
            cursor = conn.execute(query, params)
            conn.commit()
            dt = time.perf_counter() - t0
            first_line = query.strip().splitlines()[0] if query else ""
            logger.info(f"DB timing: execute_update {dt:.3f}s affected={cursor.rowcount} | {first_line[:120]}")
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute query with multiple parameter sets."""
        with self.get_connection() as conn:
            t0 = time.perf_counter()
            cursor = conn.executemany(query, params_list)
            conn.commit()
            dt = time.perf_counter() - t0
            first_line = query.strip().splitlines()[0] if query else ""
            logger.info(f"DB timing: execute_many {dt:.3f}s affected={cursor.rowcount} batches={len(params_list)} | {first_line[:120]}")
            return cursor.rowcount

    def close(self):
        """Close the thread-local database connection."""
        if hasattr(self._local, 'connection'):
            try:
                # Ensure all pending operations are complete
                self._local.connection.commit()
                self._local.connection.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
            finally:
                try:
                    del self._local.connection
                except AttributeError:
                    pass  # Already deleted

# Global database instance
db = DatabaseConnection()

class FileVersionModel:
    """File version tracking and storage using native file system operations."""
    
    @classmethod
    def insert(cls, file_path: str, content_hash: str, content: str = None, 
               line_count: int = 0, timestamp: datetime = None, 
               change_description: str = None) -> Optional[int]:
        """Insert new file version."""
        if timestamp is None:
            timestamp = datetime.now()
            
        try:
            query = """
                INSERT INTO file_versions 
                (file_path, content_hash, content, line_count, timestamp, change_description)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (file_path, content_hash, content, line_count, 
                                    timestamp, change_description))
            
            # Get the inserted ID
            result = db.execute_query("SELECT last_insert_rowid() as id")
            version_id = result[0]['id']
            logger.info(f"Created file version {version_id} for {file_path}")
            return version_id
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate file version {content_hash[:8]} for {file_path}: {e}")
            # Return existing version ID
            result = db.execute_query("SELECT id FROM file_versions WHERE content_hash = ? AND file_path = ?", 
                                    (content_hash, file_path))
            return result[0]['id'] if result else None
    
    @classmethod
    def get_recent(cls, limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Get recent file versions with optional file filtering."""
        query = "SELECT * FROM file_versions"
        params = []
        
        if file_path:
            query += " WHERE file_path = ?"
            params.append(file_path)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_by_hash(cls, content_hash: str, file_path: str = None) -> Optional[Dict[str, Any]]:
        """Get file version by content hash."""
        query = "SELECT * FROM file_versions WHERE content_hash = ?"
        params = [content_hash]
        
        if file_path:
            query += " AND file_path = ?"
            params.append(file_path)
            
        rows = db.execute_query(query, tuple(params))
        return dict(rows[0]) if rows else None
    
    @classmethod
    def get_file_history(cls, file_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get version history for a specific file."""
        query = """
            SELECT * FROM file_versions 
            WHERE file_path = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = db.execute_query(query, (file_path, limit))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_by_id(cls, version_id: int) -> Optional[Dict[str, Any]]:
        """Get a single file version by its primary key ID."""
        rows = db.execute_query("SELECT * FROM file_versions WHERE id = ?", (version_id,))
        return dict(rows[0]) if rows else None

class ContentDiffModel:
    """File content difference tracking using native diff generation."""
    
    @classmethod
    def should_create_diff(cls, old_version_id: int = None, new_version_id: int = None,
                          old_content: str = "", new_content: str = "") -> bool:
        """Check if a content diff should be created based on version IDs and content."""
        # Don't create diff if version IDs are the same (duplicate processing)
        if old_version_id is not None and old_version_id == new_version_id:
            logger.debug(f"Skipping diff creation: identical version IDs {old_version_id}")
            return False
        
        # Don't create diff if content is identical
        if old_content == new_content:
            logger.debug("Skipping diff creation: identical content")
            return False
        
        # Check if a diff with this version combination already exists
        if old_version_id is not None and new_version_id is not None:
            existing_query = """
                SELECT id FROM content_diffs 
                WHERE old_version_id = ? AND new_version_id = ?
                LIMIT 1
            """
            existing = db.execute_query(existing_query, (old_version_id, new_version_id))
            if existing:
                logger.debug(f"Skipping diff creation: diff already exists for versions {old_version_id} -> {new_version_id}")
                return False
        elif old_version_id is None and new_version_id is not None:
            # Check for creation diffs (old_version_id = NULL, new_version_id = specific)
            existing_query = """
                SELECT id FROM content_diffs 
                WHERE old_version_id IS NULL AND new_version_id = ?
                LIMIT 1
            """
            existing = db.execute_query(existing_query, (new_version_id,))
            if existing:
                logger.debug(f"Skipping diff creation: creation diff already exists for version {new_version_id}")
                return False
        
        return True
    
    @classmethod
    def insert(cls, file_path: str, old_version_id: int = None, new_version_id: int = None,
               change_type: str = 'modified', diff_content: str = None, 
               lines_added: int = 0, lines_removed: int = 0, 
               timestamp: datetime = None) -> Optional[int]:
        """Insert content diff between file versions."""
        if timestamp is None:
            timestamp = datetime.now()
            
        try:
            query = """
                INSERT INTO content_diffs 
                (file_path, old_version_id, new_version_id, change_type, diff_content, 
                 lines_added, lines_removed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (file_path, old_version_id, new_version_id, change_type, 
                                    diff_content, lines_added, lines_removed, timestamp))
            
            result = db.execute_query("SELECT last_insert_rowid() as id")
            diff_id = result[0]['id']
            
            # Enhanced logging for debugging duplicate processing
            if lines_added == 0 and lines_removed == 0:
                logger.warning(f"Created +0/-0 content diff {diff_id}: {change_type} {file_path} "
                             f"(versions: {old_version_id} -> {new_version_id})")
            else:
                logger.debug(f"Created content diff {diff_id}: {change_type} {file_path} "
                           f"(+{lines_added}/-{lines_removed} lines)")
            return diff_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to insert content diff: {e}")
            return None
    
    @classmethod
    def get_for_file(cls, file_path: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all content diffs for a specific file with pagination support."""
        query = """
            SELECT cd.*, 
                   fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                   fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
            FROM content_diffs cd
            LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
            LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
            WHERE cd.file_path = ? 
            ORDER BY cd.timestamp DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute_query(query, (file_path, limit, offset))
        return [dict(row) for row in rows]
    
    @classmethod
    def generate_diff(cls, old_content: str, new_content: str) -> tuple:
        """Generate diff content and calculate line changes."""
        old_lines = old_content.splitlines(keepends=True) if old_content else []
        new_lines = new_content.splitlines(keepends=True) if new_content else []
        
        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile='old', tofile='new',
            lineterm=''
        ))
        diff_content = '\n'.join(diff_lines)
        
        # Count added/removed lines
        lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))

        return diff_content, lines_added, lines_removed

    @classmethod
    def get_recent(cls, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent content diffs with pagination support."""
        query = """
            SELECT cd.*,
                   fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                   fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
            FROM content_diffs cd
            LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
            LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
            ORDER BY cd.timestamp DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute_query(query, (limit, offset))
        return [dict(row) for row in rows]

class FileChangeModel:
    """Simple file change tracking using native file system monitoring."""
    
    @classmethod
    def insert(cls, file_path: str, change_type: str, old_content_hash: str = None,
               new_content_hash: str = None, timestamp: datetime = None) -> Optional[int]:
        """Insert file change event."""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # Generate content hash for deduplication
            content_hash = hashlib.sha256(
                f"{file_path}{change_type}{old_content_hash or ''}{new_content_hash or ''}".encode('utf-8')
            ).hexdigest()
            
            query = """
                INSERT INTO file_changes 
                (file_path, change_type, old_content_hash, new_content_hash, timestamp, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (file_path, change_type, old_content_hash, 
                                    new_content_hash, timestamp, content_hash))
            
            result = db.execute_query("SELECT last_insert_rowid() as id")
            change_id = result[0]['id']
            logger.debug(f"Created file change {change_id}: {change_type} {file_path}")
            return change_id
            
        except sqlite3.IntegrityError as e:
            logger.debug(f"Duplicate file change for {file_path}: {e}")
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to insert file change: {e}")
            return None
    
    @classmethod
    def get_recent(cls, limit: int = 50, offset: int = 0, change_type: str = None) -> List[Dict[str, Any]]:
        """Get recent file changes with pagination support."""
        query = "SELECT * FROM file_changes"
        params = []
        
        if change_type:
            query += " WHERE change_type = ?"
            params.append(change_type)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_for_file(cls, file_path: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get change history for a specific file with pagination support."""
        query = """
            SELECT * FROM file_changes 
            WHERE file_path = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute_query(query, (file_path, limit, offset))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_count(cls, change_type: str = None, file_path: str = None) -> int:
        """Get total count of file changes for pagination metadata."""
        query = "SELECT COUNT(*) as count FROM file_changes"
        params = []
        
        conditions = []
        if change_type:
            conditions.append("change_type = ?")
            params.append(change_type)
        if file_path:
            conditions.append("file_path = ?")
            params.append(file_path)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        rows = db.execute_query(query, tuple(params))
        return rows[0]['count'] if rows else 0


class EventModel:
    """File system event tracking."""
    
    @classmethod
    def insert(cls, event_type: str, path: str, size: int = 0, 
               timestamp: datetime = None) -> int:
        """Insert new file system event."""
        if timestamp is None:
            timestamp = datetime.now()
        
        query = """
            INSERT INTO events (type, path, timestamp, size) 
            VALUES (?, ?, ?, ?)
        """
        return db.execute_update(query, (event_type, path, timestamp, size))
    
    @classmethod
    def get_recent(cls, limit: int = 50, event_type: str = None, 
                   processed: bool = None) -> List[Dict[str, Any]]:
        """Get recent events with optional filtering."""
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND type = ?"
            params.append(event_type)
        
        if processed is not None:
            query += " AND processed = ?"
            params.append(processed)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def mark_processed(cls, event_id: int) -> bool:
        """Mark an event as processed."""
        count = db.execute_update("UPDATE events SET processed = TRUE WHERE id = ?", (event_id,))
        return count > 0
    
    @classmethod
    def get_today_count(cls) -> int:
        """Get count of events today."""
        query = "SELECT COUNT(*) as count FROM events WHERE DATE(timestamp) = DATE('now')"
        result = db.execute_query(query)
        return result[0]['count']
    
    @classmethod
    def clear_all(cls) -> int:
        """Clear all events."""
        return db.execute_update("DELETE FROM events")

class SemanticModel:
    """Advanced semantic search for file content analysis."""
    
    @classmethod
    def insert_entry(cls, summary: str, entry_type: str, impact: str, 
                    topics: List[str], keywords: List[str], 
                    file_path: str = "", version_id: int = None,
                    timestamp: datetime = None, source_type: str = 'session_summary_auto') -> int:
        """Insert semantic entry for file content analysis."""
        # Apply migration if table constraint needs updating
        from .migration_semantic_impact import apply_migration
        apply_migration()
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create searchable text
        searchable_text = f"{summary} {' '.join(topics)} {' '.join(keywords)} {impact}".lower()
        
        # Insert main entry
        query = """
            INSERT INTO semantic_entries 
            (timestamp, date, time, type, summary, impact, file_path, searchable_text, version_id, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            timestamp,
            timestamp.strftime('%Y-%m-%d'),
            timestamp.strftime('%H:%M:%S'),
            entry_type,
            summary,
            impact,
            file_path,
            searchable_text,
            version_id,
            source_type
        )
        
        db.execute_update(query, params)
        
        # Get entry ID
        result = db.execute_query("SELECT last_insert_rowid() as id")
        entry_id = result[0]['id']
        
        # Insert topics
        if topics:
            topic_params = [(entry_id, topic) for topic in topics]
            db.execute_many(
                "INSERT INTO semantic_topics (entry_id, topic) VALUES (?, ?)",
                topic_params
            )
        
        # Insert keywords  
        if keywords:
            keyword_params = [(entry_id, keyword) for keyword in keywords]
            db.execute_many(
                "INSERT INTO semantic_keywords (entry_id, keyword) VALUES (?, ?)",
                keyword_params
            )
        
        logger.info(f"Created semantic entry {entry_id} for file {file_path} (source_type={source_type})")
        return entry_id
    
    @classmethod
    def search(cls, query: str, limit: int = 20, file_path: str = None,
               version_id: int = None) -> List[Dict[str, Any]]:
        """Enhanced semantic search with file-based filtering."""
        # Base FTS5 search
        search_query = """
            SELECT se.*, GROUP_CONCAT(DISTINCT st.topic) as topics,
                   GROUP_CONCAT(DISTINCT sk.keyword) as keywords,
                   rank
            FROM semantic_search ss
            JOIN semantic_entries se ON ss.rowid = se.id
            LEFT JOIN semantic_topics st ON se.id = st.entry_id  
            LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
            WHERE semantic_search MATCH ?
        """
        params = [query]
        
        # Add file-based filters
        if file_path:
            search_query += " AND se.file_path = ?"
            params.append(file_path)
        
        if version_id:
            search_query += " AND se.version_id = ?"
            params.append(version_id)
        
        search_query += """
            GROUP BY se.id
            ORDER BY rank, se.timestamp DESC
            LIMIT ?
        """
        params.append(limit)
        
        rows = db.execute_query(search_query, tuple(params))
        results = []
        
        for row in rows:
            result = dict(row)
            result['topics'] = row['topics'].split(',') if row['topics'] else []
            result['keywords'] = row['keywords'].split(',') if row['keywords'] else []
            results.append(result)
        
        return results
    
    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Get all unique topics."""
        rows = db.execute_query("SELECT DISTINCT topic FROM semantic_topics ORDER BY topic")
        return [row['topic'] for row in rows]
    
    @classmethod
    def get_all_keywords(cls) -> List[Dict[str, Any]]:
        """Get all keywords with frequency count."""
        query = """
            SELECT keyword, COUNT(*) as count
            FROM semantic_keywords
            GROUP BY keyword
            ORDER BY count DESC, keyword
        """
        rows = db.execute_query(query)
        return [{'keyword': row['keyword'], 'count': row['count']} for row in rows]

    @classmethod
    def upsert(cls, file_path: str, content_hash: str, summary: str,
               topics: List[str], keywords: List[str], impact_level: str,
               timestamp: datetime = None) -> Optional[int]:
        """
        Insert or update semantic analysis data (backward compatibility for tests).
        Uses the semantic_analysis table schema expected by legacy tests.
        """
        if timestamp is None:
            timestamp = datetime.now()

        try:
            # Convert lists to JSON strings for storage
            topics_json = ','.join(topics) if topics else ''
            keywords_json = ','.join(keywords) if keywords else ''

            # Check if entry exists
            check_query = """
                SELECT id FROM semantic_analysis
                WHERE file_path = ? AND content_hash = ?
            """
            existing = db.execute_query(check_query, (file_path, content_hash))

            if existing:
                # Update existing entry
                update_query = """
                    UPDATE semantic_analysis
                    SET summary = ?, topics = ?, keywords = ?,
                        impact_level = ?, timestamp = ?
                    WHERE file_path = ? AND content_hash = ?
                """
                db.execute_update(update_query, (
                    summary, topics_json, keywords_json, impact_level,
                    timestamp, file_path, content_hash
                ))
                return existing[0]['id']
            else:
                # Insert new entry
                insert_query = """
                    INSERT INTO semantic_analysis
                    (file_path, content_hash, summary, topics, keywords, impact_level, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                db.execute_update(insert_query, (
                    file_path, content_hash, summary, topics_json,
                    keywords_json, impact_level, timestamp
                ))

                result = db.execute_query("SELECT last_insert_rowid() as id")
                return result[0]['id']

        except sqlite3.Error as e:
            logger.error(f"Failed to upsert semantic analysis: {e}")
            return None

    @classmethod
    def search_by_topic(cls, topic: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search semantic analysis entries by topic (backward compatibility for tests).
        Uses the semantic_analysis table schema.
        """
        try:
            # Search for entries where the topic is in the topics list
            query = """
                SELECT *
                FROM semantic_analysis
                WHERE topics LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            # Use LIKE pattern to match topic in comma-separated list
            pattern = f'%{topic}%'
            rows = db.execute_query(query, (pattern, limit))

            results = []
            for row in rows:
                result = dict(row)
                # Convert comma-separated strings back to lists
                result['topics'] = result.get('topics', '').split(',') if result.get('topics') else []
                result['keywords'] = result.get('keywords', '').split(',') if result.get('keywords') else []
                results.append(result)

            return results
        except sqlite3.Error as e:
            logger.error(f"Failed to search by topic: {e}")
            return []

    @classmethod
    def search_by_keyword(cls, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search semantic analysis entries by keyword (backward compatibility for tests).
        Uses the semantic_analysis table schema.
        """
        try:
            # Search for entries where the keyword is in the keywords list
            query = """
                SELECT *
                FROM semantic_analysis
                WHERE keywords LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            # Use LIKE pattern to match keyword in comma-separated list
            pattern = f'%{keyword}%'
            rows = db.execute_query(query, (pattern, limit))

            results = []
            for row in rows:
                result = dict(row)
                # Convert comma-separated strings back to lists
                result['topics'] = result.get('topics', '').split(',') if result.get('topics') else []
                result['keywords'] = result.get('keywords', '').split(',') if result.get('keywords') else []
                results.append(result)

            return results
        except sqlite3.Error as e:
            logger.error(f"Failed to search by keyword: {e}")
            return []

class ConfigModel:
    """Type-safe configuration storage."""
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get configuration value with type conversion."""
        rows = db.execute_query("SELECT value, type FROM config_values WHERE key = ?", (key,))
        
        if not rows:
            return default
        
        value, value_type = rows[0]['value'], rows[0]['type']
        
        # Convert based on type
        if value_type == 'int':
            return int(value)
        elif value_type == 'bool':
            return value.lower() == 'true'
        elif value_type == 'json':
            return json.loads(value)
        else:
            return value
    
    @classmethod
    def set(cls, key: str, value: Any, description: str = None) -> None:
        """Set configuration value with automatic type detection."""
        # Determine type
        if isinstance(value, bool):
            value_type, str_value = 'bool', str(value).lower()
        elif isinstance(value, int):
            value_type, str_value = 'int', str(value)
        elif isinstance(value, (dict, list)):
            value_type, str_value = 'json', json.dumps(value)
        else:
            value_type, str_value = 'str', str(value)
        
        query = """
            INSERT OR REPLACE INTO config_values (key, value, type, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        db.execute_update(query, (key, str_value, value_type, description))
        logger.info(f"Updated config: {key} = {value}")
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration values."""
        rows = db.execute_query("SELECT key, value, type FROM config_values")
        
        config = {}
        for row in rows:
            key, value, value_type = row['key'], row['value'], row['type']
            
            if value_type == 'int':
                config[key] = int(value)
            elif value_type == 'bool':
                config[key] = value.lower() == 'true'
            elif value_type == 'json':
                config[key] = json.loads(value)
            else:
                config[key] = value
        
        return config

class FileStateModel:
    """Enhanced file state tracking for complete file snapshots."""
    
    @classmethod
    def update_state(cls, file_path: str, content_hash: str = None, 
                    line_count: int = 0, file_size: int = 0, 
                    last_modified: datetime = None) -> None:
        """Update file state with content information."""
        if last_modified is None:
            try:
                last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            except (OSError, FileNotFoundError):
                last_modified = datetime.now()
                
        query = """
            INSERT OR REPLACE INTO file_states 
            (file_path, content_hash, last_modified, line_count, file_size, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        db.execute_update(query, (file_path, content_hash, last_modified, line_count, file_size))
    
    @classmethod
    def get_state(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """Get current file state."""
        rows = db.execute_query("SELECT * FROM file_states WHERE file_path = ?", (file_path,))
        return dict(rows[0]) if rows else None
    
    @classmethod
    def has_changed(cls, file_path: str, content_hash: str) -> bool:
        """Check if file has changed based on content hash."""
        current_state = cls.get_state(file_path)
        return current_state is None or current_state['content_hash'] != content_hash
    
    @classmethod
    def calculate_content_hash(cls, content: str) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @classmethod
    def get_all_tracked_files(cls) -> List[Dict[str, Any]]:
        """Get all files currently being tracked."""
        query = "SELECT * FROM file_states ORDER BY last_modified DESC"
        rows = db.execute_query(query)
        return [dict(row) for row in rows]

# Performance monitoring
class PerformanceModel:
    """Database performance monitoring and optimization."""
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get database performance statistics."""
        stats = {}
        
        # Table sizes
        tables = ['file_versions', 'content_diffs', 'file_changes', 
                 'events', 'semantic_entries', 'config_values', 'file_states']
        for table in tables:
            try:
                count = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")[0]['count']
                stats[f"{table}_count"] = count
            except sqlite3.OperationalError:
                # Table doesn't exist yet
                stats[f"{table}_count"] = 0
        
        # Database size
        size_result = db.execute_query("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")[0]
        stats['database_size_bytes'] = size_result['size']
        
        return stats
    
    @classmethod
    def vacuum(cls) -> None:
        """Optimize database by reclaiming space."""
        db.execute_update("VACUUM")
        logger.info("Database vacuum completed")
    
    @classmethod
    def analyze(cls) -> None:
        """Update query planner statistics."""
        db.execute_update("ANALYZE")
        logger.info("Database analysis completed")

class ComprehensiveSummaryModel:
    """Comprehensive summary storage and management."""
    
    @classmethod
    def create_summary(cls, time_range_start: datetime, time_range_end: datetime,
                      summary_content: str, key_topics: List[str] = None, 
                      key_keywords: List[str] = None, overall_impact: str = 'moderate',
                      files_affected_count: int = 0, changes_count: int = 0,
                      time_span: str = None) -> Optional[int]:
        """Create a new comprehensive summary."""
        try:
            # Apply migration if table doesn't exist
            from .migration_comprehensive_summaries import apply_migration
            apply_migration()
            
            timestamp = datetime.now()
            
            # Convert lists to JSON strings
            topics_json = json.dumps(key_topics) if key_topics else None
            keywords_json = json.dumps(key_keywords) if key_keywords else None
            
            query = """
                INSERT INTO comprehensive_summaries 
                (timestamp, time_range_start, time_range_end, summary_content,
                 key_topics, key_keywords, overall_impact, files_affected_count,
                 changes_count, time_span)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            result = db.execute_update(query, (
                timestamp, time_range_start, time_range_end, summary_content,
                topics_json, keywords_json, overall_impact, files_affected_count,
                changes_count, time_span
            ))
            
            if result > 0:
                # Update last comprehensive summary timestamp
                ConfigModel.set('last_comprehensive_summary', timestamp.isoformat(),
                              'Timestamp of last comprehensive summary generation')
                
                # Get the inserted ID
                id_result = db.execute_query("SELECT last_insert_rowid() as id")
                return id_result[0]['id'] if id_result else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create comprehensive summary: {e}")
            return None
    
    @classmethod
    def get_latest_summary(cls) -> Optional[Dict[str, Any]]:
        """Get the most recent comprehensive summary."""
        try:
            query = """
                SELECT * FROM comprehensive_summaries 
                ORDER BY timestamp DESC 
                LIMIT 1
            """
            rows = db.execute_query(query)
            
            if rows:
                summary = dict(rows[0])
                # Parse JSON fields
                summary['key_topics'] = json.loads(summary['key_topics']) if summary['key_topics'] else []
                summary['key_keywords'] = json.loads(summary['key_keywords']) if summary['key_keywords'] else []
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest comprehensive summary: {e}")
            return None
    
    @classmethod
    def get_last_summary_timestamp(cls) -> Optional[datetime]:
        """Get timestamp of last comprehensive summary."""
        try:
            last_timestamp_str = ConfigModel.get('last_comprehensive_summary')
            if last_timestamp_str:
                return datetime.fromisoformat(last_timestamp_str)
            
            # Fallback: check actual summaries table
            latest = cls.get_latest_summary()
            return datetime.fromisoformat(latest['timestamp']) if latest else None
            
        except Exception as e:
            logger.error(f"Failed to get last summary timestamp: {e}")
            return None
    
    @classmethod
    def get_summaries_paginated(cls, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """Get comprehensive summaries with pagination."""
        try:
            offset = (page - 1) * page_size
            
            # Get total count
            count_result = db.execute_query("SELECT COUNT(*) as count FROM comprehensive_summaries")
            total_count = count_result[0]['count'] if count_result else 0
            
            # Get paginated results
            query = """
                SELECT * FROM comprehensive_summaries 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """
            rows = db.execute_query(query, (page_size, offset))
            
            summaries = []
            for row in rows:
                summary = dict(row)
                # Parse JSON fields
                summary['key_topics'] = json.loads(summary['key_topics']) if summary['key_topics'] else []
                summary['key_keywords'] = json.loads(summary['key_keywords']) if summary['key_keywords'] else []
                summaries.append(summary)
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                'summaries': summaries,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_previous': page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get paginated summaries: {e}")
            return {'summaries': [], 'pagination': {}}
    
    @classmethod
    def delete_summary(cls, summary_id: int) -> bool:
        """Delete a comprehensive summary."""
        try:
            result = db.execute_update("DELETE FROM comprehensive_summaries WHERE id = ?", (summary_id,))
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete comprehensive summary {summary_id}: {e}")
            return False

logger.info("File-based database models initialized successfully")
