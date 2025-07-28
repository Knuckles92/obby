"""
🤖 SUBAGENT A: SQLite Database Models & Infrastructure
=======================================================

High-performance database layer with connection pooling, transactions, 
and optimized queries for all Obby data types.
"""

import sqlite3
import threading
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Thread-safe SQLite connection manager with connection pooling."""
    
    def __init__(self, db_path: str = "obby.db"):
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
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute query with multiple parameter sets."""
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

# Global database instance
db = DatabaseConnection()

class DiffModel:
    """High-performance diff storage with content hashing and deduplication."""
    
    @staticmethod
    def create_content_hash(content: str) -> str:
        """Generate SHA-256 hash for content deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @classmethod
    def insert(cls, file_path: str, diff_content: str, timestamp: datetime = None) -> Optional[int]:
        """Insert new diff with automatic deduplication."""
        if timestamp is None:
            timestamp = datetime.now()
        
        content_hash = cls.create_content_hash(diff_content)
        base_name = Path(file_path).stem
        size = len(diff_content)
        
        # Check for existing diff with same content hash
        existing = db.execute_query(
            "SELECT id FROM diffs WHERE content_hash = ?",
            (content_hash,)
        )
        
        if existing:
            logger.info(f"Duplicate diff content detected, skipping: {content_hash[:8]}")
            return existing[0]['id']
        
        try:
            query = """
                INSERT INTO diffs (file_path, base_name, content_hash, timestamp, diff_content, size)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (file_path, base_name, content_hash, timestamp, diff_content, size))
            
            # Get the inserted ID
            result = db.execute_query("SELECT last_insert_rowid() as id")
            diff_id = result[0]['id']
            logger.info(f"Created diff {diff_id} for {file_path}")
            return diff_id
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to insert diff: {e}")
            return None
    
    @classmethod
    def get_recent(cls, limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Get recent diffs with optional file filtering."""
        query = "SELECT * FROM diffs"
        params = []
        
        if file_path:
            query += " WHERE file_path = ?"
            params.append(file_path)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_by_id(cls, diff_id: int) -> Optional[Dict[str, Any]]:
        """Get specific diff by ID."""
        rows = db.execute_query("SELECT * FROM diffs WHERE id = ?", (diff_id,))
        return dict(rows[0]) if rows else None
    
    @classmethod
    def delete_old(cls, days: int = 30) -> int:
        """Delete diffs older than specified days."""
        query = "DELETE FROM diffs WHERE timestamp < datetime('now', '-' || ? || ' days')"
        return db.execute_update(query, (days,))
    
    @classmethod
    def clear_all(cls) -> int:
        """Clear all diffs (for API endpoint)."""
        return db.execute_update("DELETE FROM diffs")

class EventModel:
    """Persistent event tracking replacing in-memory storage."""
    
    @classmethod
    def insert(cls, event_type: str, path: str, size: int = 0, timestamp: datetime = None) -> int:
        """Insert new file event."""
        if timestamp is None:
            timestamp = datetime.now()
        
        query = "INSERT INTO events (type, path, timestamp, size) VALUES (?, ?, ?, ?)"
        return db.execute_update(query, (event_type, path, timestamp, size))
    
    @classmethod
    def get_recent(cls, limit: int = 50, event_type: str = None) -> List[Dict[str, Any]]:
        """Get recent events with optional type filtering."""
        query = "SELECT * FROM events"
        params = []
        
        if event_type:
            query += " WHERE type = ?"
            params.append(event_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_today_count(cls) -> int:
        """Get count of events today."""
        query = "SELECT COUNT(*) as count FROM events WHERE DATE(timestamp) = DATE('now')"
        result = db.execute_query(query)
        return result[0]['count']
    
    @classmethod
    def clear_all(cls) -> int:
        """Clear all events (for API endpoint)."""
        return db.execute_update("DELETE FROM events")

class SemanticModel:
    """Advanced semantic search with normalized storage."""
    
    @classmethod
    def insert_entry(cls, summary: str, entry_type: str, impact: str, 
                    topics: List[str], keywords: List[str], 
                    file_path: str = "", timestamp: datetime = None) -> int:
        """Insert semantic entry with topics and keywords."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create searchable text
        searchable_text = f"{summary} {' '.join(topics)} {' '.join(keywords)} {impact}".lower()
        
        # Insert main entry
        query = """
            INSERT INTO semantic_entries 
            (timestamp, date, time, type, summary, impact, file_path, searchable_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            timestamp,
            timestamp.strftime('%Y-%m-%d'),
            timestamp.strftime('%H:%M:%S'),
            entry_type,
            summary,
            impact,
            file_path,
            searchable_text
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
        
        logger.info(f"Created semantic entry {entry_id}: {summary}")
        return entry_id
    
    @classmethod
    def search(cls, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Full-text search with topic/keyword inclusion."""
        # Use FTS5 for fast search
        search_query = """
            SELECT se.*, GROUP_CONCAT(DISTINCT st.topic) as topics,
                   GROUP_CONCAT(DISTINCT sk.keyword) as keywords,
                   rank
            FROM semantic_search ss
            JOIN semantic_entries se ON ss.rowid = se.id
            LEFT JOIN semantic_topics st ON se.id = st.entry_id  
            LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
            WHERE semantic_search MATCH ?
            GROUP BY se.id
            ORDER BY rank, se.timestamp DESC
            LIMIT ?
        """
        
        rows = db.execute_query(search_query, (query, limit))
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

class ConfigModel:
    """Type-safe configuration storage replacing config.json."""
    
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
    """File state tracking replacing in-memory last_file_lines."""
    
    @classmethod
    def update_state(cls, file_path: str, content_hash: str, line_count: int) -> None:
        """Update file state with current hash and line count."""
        query = """
            INSERT OR REPLACE INTO file_states 
            (file_path, content_hash, last_modified, line_count, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
        """
        db.execute_update(query, (file_path, content_hash, line_count))
    
    @classmethod
    def get_state(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """Get current file state."""
        rows = db.execute_query("SELECT * FROM file_states WHERE file_path = ?", (file_path,))
        return dict(rows[0]) if rows else None
    
    @classmethod
    def has_changed(cls, file_path: str, content_hash: str) -> bool:
        """Check if file has changed since last recorded state."""
        current_state = cls.get_state(file_path)
        return current_state is None or current_state['content_hash'] != content_hash

# Performance monitoring
class PerformanceModel:
    """Database performance monitoring and optimization."""
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get database performance statistics."""
        stats = {}
        
        # Table sizes
        tables = ['diffs', 'events', 'semantic_entries', 'config_values']
        for table in tables:
            count = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")[0]['count']
            stats[f"{table}_count"] = count
        
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

logger.info("🤖 Subagent A: Database models initialized successfully")