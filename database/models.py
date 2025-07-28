"""
Git-Native Database Models & Infrastructure
==========================================

High-performance database layer with connection pooling, transactions, 
and git-focused models for Obby's version control integration.
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

class GitCommitModel:
    """Git commit tracking and storage."""
    
    @classmethod
    def insert(cls, commit_hash: str, author_name: str, author_email: str, 
               message: str, timestamp: datetime, branch_name: str = None) -> Optional[int]:
        """Insert new git commit."""
        try:
            short_hash = commit_hash[:8]
            
            query = """
                INSERT INTO git_commits 
                (commit_hash, short_hash, author_name, author_email, message, branch_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (commit_hash, short_hash, author_name, author_email, 
                                    message, branch_name, timestamp))
            
            # Get the inserted ID
            result = db.execute_query("SELECT last_insert_rowid() as id")
            commit_id = result[0]['id']
            logger.info(f"Created git commit {commit_id}: {short_hash}")
            return commit_id
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate commit {commit_hash[:8]}: {e}")
            # Return existing commit ID
            result = db.execute_query("SELECT id FROM git_commits WHERE commit_hash = ?", (commit_hash,))
            return result[0]['id'] if result else None
    
    @classmethod
    def get_recent(cls, limit: int = 20, branch: str = None) -> List[Dict[str, Any]]:
        """Get recent commits with optional branch filtering."""
        query = "SELECT * FROM git_commits"
        params = []
        
        if branch:
            query += " WHERE branch_name = ?"
            params.append(branch)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_by_hash(cls, commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get commit by hash (supports short or full hash)."""
        if len(commit_hash) <= 8:
            # Short hash
            rows = db.execute_query("SELECT * FROM git_commits WHERE short_hash = ?", (commit_hash,))
        else:
            # Full hash
            rows = db.execute_query("SELECT * FROM git_commits WHERE commit_hash = ?", (commit_hash,))
        
        return dict(rows[0]) if rows else None
    
    @classmethod
    def get_authors(cls) -> List[Dict[str, Any]]:
        """Get all unique authors with activity stats."""
        query = """
            SELECT author_name, author_email, COUNT(*) as commit_count,
                   MAX(timestamp) as last_commit, MIN(timestamp) as first_commit
            FROM git_commits
            GROUP BY author_name, author_email
            ORDER BY commit_count DESC
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]

class GitFileChangeModel:
    """Git file-level change tracking."""
    
    @classmethod
    def insert(cls, commit_id: int, file_path: str, change_type: str, 
               diff_content: str = None, lines_added: int = 0, 
               lines_removed: int = 0, old_path: str = None) -> Optional[int]:
        """Insert file change for a commit."""
        try:
            query = """
                INSERT INTO git_file_changes 
                (commit_id, file_path, change_type, diff_content, lines_added, lines_removed, old_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (commit_id, file_path, change_type, diff_content, 
                                    lines_added, lines_removed, old_path))
            
            result = db.execute_query("SELECT last_insert_rowid() as id")
            change_id = result[0]['id']
            logger.debug(f"Created file change {change_id}: {change_type} {file_path}")
            return change_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to insert file change: {e}")
            return None
    
    @classmethod
    def get_for_commit(cls, commit_id: int) -> List[Dict[str, Any]]:
        """Get all file changes for a specific commit."""
        query = "SELECT * FROM git_file_changes WHERE commit_id = ? ORDER BY file_path"
        rows = db.execute_query(query, (commit_id,))
        return [dict(row) for row in rows]
    
    @classmethod
    def get_file_history(cls, file_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get change history for a specific file."""
        query = """
            SELECT fc.*, gc.commit_hash, gc.short_hash, gc.author_name, 
                   gc.message, gc.timestamp, gc.branch_name
            FROM git_file_changes fc
            JOIN git_commits gc ON fc.commit_id = gc.id
            WHERE fc.file_path = ?
            ORDER BY gc.timestamp DESC
            LIMIT ?
        """
        rows = db.execute_query(query, (file_path, limit))
        return [dict(row) for row in rows]

class GitWorkingChangeModel:
    """Git working directory (uncommitted) change tracking."""
    
    @classmethod
    def insert(cls, file_path: str, change_type: str, status: str, 
               diff_content: str = None, branch_name: str = None, 
               timestamp: datetime = None) -> Optional[int]:
        """Insert working directory change."""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # Generate content hash for deduplication
            content_hash = hashlib.sha256(
                f"{file_path}{change_type}{status}{diff_content or ''}".encode('utf-8')
            ).hexdigest()
            
            query = """
                INSERT INTO git_working_changes 
                (file_path, change_type, status, diff_content, timestamp, branch_name, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (file_path, change_type, status, diff_content, 
                                    timestamp, branch_name, content_hash))
            
            result = db.execute_query("SELECT last_insert_rowid() as id")
            change_id = result[0]['id']
            logger.debug(f"Created working change {change_id}: {status} {change_type} {file_path}")
            return change_id
            
        except sqlite3.IntegrityError as e:
            logger.debug(f"Duplicate working change for {file_path}: {e}")
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to insert working change: {e}")
            return None
    
    @classmethod
    def get_current(cls, status: str = None) -> List[Dict[str, Any]]:
        """Get current working directory changes."""
        query = "SELECT * FROM git_working_changes"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC"
        
        rows = db.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    @classmethod
    def clear_all(cls) -> int:
        """Clear all working changes (for when git status changes)."""
        return db.execute_update("DELETE FROM git_working_changes")
    
    @classmethod
    def clear_for_file(cls, file_path: str) -> int:
        """Clear working changes for a specific file."""
        return db.execute_update("DELETE FROM git_working_changes WHERE file_path = ?", (file_path,))

class GitRepositoryStateModel:
    """Git repository state tracking."""
    
    @classmethod
    def insert(cls, current_branch: str, head_commit: str, is_dirty: bool,
               staged_count: int = 0, unstaged_count: int = 0, 
               untracked_count: int = 0, timestamp: datetime = None) -> Optional[int]:
        """Insert repository state snapshot."""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            query = """
                INSERT INTO git_repository_state 
                (current_branch, head_commit, is_dirty, staged_files_count, 
                 unstaged_files_count, untracked_files_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (current_branch, head_commit, is_dirty, 
                                    staged_count, unstaged_count, untracked_count, timestamp))
            
            result = db.execute_query("SELECT last_insert_rowid() as id")
            state_id = result[0]['id']
            logger.debug(f"Created repository state {state_id}: {current_branch} ({head_commit[:8]})")
            return state_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to insert repository state: {e}")
            return None
    
    @classmethod
    def get_latest(cls) -> Optional[Dict[str, Any]]:
        """Get the most recent repository state."""
        query = "SELECT * FROM git_repository_state ORDER BY timestamp DESC LIMIT 1"
        rows = db.execute_query(query)
        return dict(rows[0]) if rows else None
    
    @classmethod
    def get_history(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Get repository state history."""
        query = "SELECT * FROM git_repository_state ORDER BY timestamp DESC LIMIT ?"
        rows = db.execute_query(query, (limit,))
        return [dict(row) for row in rows]

class EventModel:
    """File system event tracking (enhanced with git context)."""
    
    @classmethod
    def insert(cls, event_type: str, path: str, size: int = 0, 
               git_status: str = None, timestamp: datetime = None) -> int:
        """Insert new file event with git context."""
        if timestamp is None:
            timestamp = datetime.now()
        
        query = """
            INSERT INTO events (type, path, timestamp, size, git_status) 
            VALUES (?, ?, ?, ?, ?)
        """
        return db.execute_update(query, (event_type, path, timestamp, size, git_status))
    
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
    """Advanced semantic search with git context integration."""
    
    @classmethod
    def insert_entry(cls, summary: str, entry_type: str, impact: str, 
                    topics: List[str], keywords: List[str], 
                    file_path: str = "", commit_hash: str = None,
                    author_name: str = None, branch_name: str = None,
                    timestamp: datetime = None) -> int:
        """Insert semantic entry with git context."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create searchable text
        searchable_text = f"{summary} {' '.join(topics)} {' '.join(keywords)} {impact}".lower()
        
        # Insert main entry
        query = """
            INSERT INTO semantic_entries 
            (timestamp, date, time, type, summary, impact, file_path, searchable_text,
             commit_hash, author_name, branch_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            commit_hash,
            author_name,
            branch_name
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
        
        logger.info(f"Created semantic entry {entry_id} for commit {commit_hash or 'working'}")
        return entry_id
    
    @classmethod
    def search(cls, query: str, limit: int = 20, commit_hash: str = None,
               author: str = None, branch: str = None) -> List[Dict[str, Any]]:
        """Enhanced semantic search with git filtering."""
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
        
        # Add git-based filters
        if commit_hash:
            search_query += " AND se.commit_hash = ?"
            params.append(commit_hash)
        
        if author:
            search_query += " AND se.author_name LIKE ?"
            params.append(f"%{author}%")
        
        if branch:
            search_query += " AND se.branch_name = ?"
            params.append(branch)
        
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
    """File state tracking with git integration."""
    
    @classmethod
    def update_state(cls, file_path: str, git_hash: str = None, 
                    line_count: int = 0, is_tracked: bool = False) -> None:
        """Update file state with git information."""
        query = """
            INSERT OR REPLACE INTO file_states 
            (file_path, git_hash, last_modified, line_count, is_tracked, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
        """
        db.execute_update(query, (file_path, git_hash, line_count, is_tracked))
    
    @classmethod
    def get_state(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """Get current file state."""
        rows = db.execute_query("SELECT * FROM file_states WHERE file_path = ?", (file_path,))
        return dict(rows[0]) if rows else None
    
    @classmethod
    def has_changed(cls, file_path: str, git_hash: str) -> bool:
        """Check if file has changed based on git hash."""
        current_state = cls.get_state(file_path)
        return current_state is None or current_state['git_hash'] != git_hash

# Performance monitoring
class PerformanceModel:
    """Database performance monitoring and optimization."""
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get database performance statistics."""
        stats = {}
        
        # Table sizes
        tables = ['git_commits', 'git_file_changes', 'git_working_changes', 
                 'events', 'semantic_entries', 'config_values']
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

logger.info("Git-native database models initialized successfully")