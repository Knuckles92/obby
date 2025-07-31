"""
File-Based API Integration & Advanced Query Engine
=================================================

High-performance query layer for API endpoints with file-based search,
analytics, and real-time capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json

from .models import (
    db, FileVersionModel, ContentDiffModel, FileChangeModel,
    EventModel, SemanticModel, ConfigModel, FileStateModel, PerformanceModel
)

logger = logging.getLogger(__name__)

class FileQueries:
    """File-focused queries for API endpoints."""
    
    @staticmethod
    def get_recent_diffs(limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Get recent file diffs - replaces git-based diff endpoints."""
        try:
            if file_path:
                diffs = ContentDiffModel.get_for_file(file_path, limit=limit)
            else:
                # Get recent diffs from all files
                query = """
                    SELECT cd.*, fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                           fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                    FROM content_diffs cd
                    LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                    LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                    ORDER BY cd.timestamp DESC
                    LIMIT ?
                """
                rows = db.execute_query(query, (limit,))
                diffs = [dict(row) for row in rows]
            
            # Format for API response
            formatted_diffs = []
            for diff in diffs:
                formatted_diff = {
                    'id': str(diff['id']),
                    'filePath': diff['file_path'],
                    'changeType': diff['change_type'],
                    'diffContent': diff['diff_content'],
                    'linesAdded': diff['lines_added'],
                    'linesRemoved': diff['lines_removed'],
                    'timestamp': diff['timestamp'],
                    'oldVersionId': diff['old_version_id'],
                    'newVersionId': diff['new_version_id']
                }
                formatted_diffs.append(formatted_diff)
            
            logger.info(f"Retrieved {len(formatted_diffs)} recent diffs")
            return formatted_diffs
            
        except Exception as e:
            logger.error(f"Error retrieving recent diffs: {e}")
            return []
    
    @staticmethod  
    def get_recent_versions(limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Get recent file versions - replaces commit-based tracking."""
        try:
            versions = FileVersionModel.get_recent(limit=limit, file_path=file_path)
            
            # Format for API response
            formatted_versions = []
            for version in versions:
                formatted_version = {
                    'id': str(version['id']),
                    'filePath': version['file_path'],
                    'contentHash': version['content_hash'],
                    'lineCount': version['line_count'],
                    'timestamp': version['timestamp'],
                    'changeDescription': version['change_description'],
                    'hasContent': bool(version.get('content'))
                }
                formatted_versions.append(formatted_version)
            
            logger.info(f"Retrieved {len(formatted_versions)} recent versions")
            return formatted_versions
            
        except Exception as e:
            logger.error(f"Error retrieving recent versions: {e}")
            return []
    
    @staticmethod
    def get_working_changes(status: str = None) -> List[Dict[str, Any]]:
        """Get recent file changes - replaces git working changes."""
        try:
            file_changes = FileChangeModel.get_recent(limit=100, change_type=status)
            
            # Format for API response
            formatted_changes = []
            for change in file_changes:
                formatted_change = {
                    'id': str(change['id']),
                    'filePath': change['file_path'],
                    'changeType': change['change_type'],
                    'oldContentHash': change['old_content_hash'],
                    'newContentHash': change['new_content_hash'],
                    'timestamp': change['timestamp']
                }
                formatted_changes.append(formatted_change)
            
            logger.info(f"Retrieved {len(formatted_changes)} file changes")
            return formatted_changes
            
        except Exception as e:
            logger.error(f"Error retrieving file changes: {e}")
            return []
    
    @staticmethod
    def get_repository_status() -> Dict[str, Any]:
        """Get file monitoring system status - replaces git repository status."""
        try:
            # Get performance stats
            perf_stats = PerformanceModel.get_stats()
            
            # Get recent activity
            recent_versions = FileVersionModel.get_recent(limit=10)
            recent_changes = FileChangeModel.get_recent(limit=10)
            
            # Get tracked files count
            tracked_files = FileStateModel.get_all_tracked_files()
            
            status = {
                'monitoring_active': True,  # TODO: Get from monitor instance
                'tracked_files_count': len(tracked_files),
                'recent_versions_count': len(recent_versions),
                'recent_changes_count': len(recent_changes),
                'database_stats': perf_stats,
                'last_activity': recent_changes[0]['timestamp'] if recent_changes else None,
                'system_type': 'file_based',
                'version': '3.0.0-file-based'
            }
            
            logger.info("Retrieved file monitoring system status")
            return status
            
        except Exception as e:
            logger.error(f"Error retrieving system status: {e}")
            return {'error': 'Failed to get system status'}
    
    @staticmethod
    def sync_files_to_database(directory_path: str = None) -> Dict[str, Any]:
        """Manually sync files to database - replaces git sync."""
        try:
            from core.file_tracker import file_tracker
            
            # Perform file scan
            files_processed = file_tracker.scan_directory(directory_path or "notes", recursive=True)
            
            sync_result = {
                'success': True,
                'files_processed': files_processed,
                'directory': directory_path or "notes",
                'timestamp': datetime.now().isoformat(),
                'errors': []
            }
            
            logger.info(f"File sync completed: {files_processed} files processed")
            return sync_result
            
        except Exception as e:
            logger.error(f"Error during file sync: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_processed': 0,
                'errors': [str(e)]
            }
    
    @staticmethod
    def clear_all_file_data() -> Dict[str, Any]:
        """Clear all file tracking data - replaces git data clearing."""
        try:
            # Clear file tracking tables
            content_diffs_cleared = db.execute_update("DELETE FROM content_diffs")
            file_versions_cleared = db.execute_update("DELETE FROM file_versions") 
            file_changes_cleared = db.execute_update("DELETE FROM file_changes")
            file_states_cleared = db.execute_update("DELETE FROM file_states")
            
            clear_result = {
                'success': True,
                'content_diffs_cleared': content_diffs_cleared,
                'file_versions_cleared': file_versions_cleared,
                'file_changes_cleared': file_changes_cleared,
                'file_states_cleared': file_states_cleared,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Cleared all file data: {sum(clear_result.values()) - 2} total records")  # -2 for success and timestamp
            return clear_result
            
        except Exception as e:
            logger.error(f"Error clearing file data: {e}")
            return {'success': False, 'error': str(e)}

class EventQueries:
    """Event-focused queries for real-time updates."""
    
    @staticmethod
    def get_recent_events(limit: int = 50, event_type: str = None, 
                         processed: bool = None) -> List[Dict[str, Any]]:
        """Get recent file system events."""
        try:
            events = EventModel.get_recent(limit=limit, event_type=event_type, processed=processed)
            
            # Format for API response
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': str(event['id']),
                    'type': event['type'],
                    'path': event['path'],
                    'timestamp': event['timestamp'],
                    'size': event.get('size', 0),
                    'processed': event.get('processed', False)
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Retrieved {len(formatted_events)} recent events")
            return formatted_events
            
        except Exception as e:
            logger.error(f"Error retrieving recent events: {e}")
            return []
    
    @staticmethod
    def get_recent_tree_changes(limit: int = 10, time_window_minutes: int = 30) -> List[Dict[str, Any]]:
        """Get recent file tree changes within time window."""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            
            query = """
                SELECT * FROM events 
                WHERE timestamp >= ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            rows = db.execute_query(query, (cutoff_time, limit))
            tree_changes = [dict(row) for row in rows]
            
            logger.info(f"Retrieved {len(tree_changes)} recent tree changes")
            return tree_changes
            
        except Exception as e:
            logger.error(f"Error retrieving tree changes: {e}")
            return []

class SemanticQueries:
    """Semantic search and AI-powered queries."""
    
    @staticmethod
    def search_content(query: str, limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Search semantic content with file-based filtering."""
        try:
            results = SemanticModel.search(query, limit=limit, file_path=file_path)
            
            # Format for API response
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': str(result['id']),
                    'summary': result['summary'],
                    'type': result['type'],
                    'impact': result['impact'],
                    'filePath': result['file_path'],
                    'timestamp': result['timestamp'],
                    'topics': result.get('topics', []),
                    'keywords': result.get('keywords', []),
                    'versionId': result.get('version_id')
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Semantic search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    @staticmethod
    def get_all_topics() -> List[str]:
        """Get all unique topics from semantic analysis."""
        return SemanticModel.get_all_topics()
    
    @staticmethod
    def get_all_keywords() -> List[Dict[str, Any]]:
        """Get all keywords with frequency counts."""
        return SemanticModel.get_all_keywords()

class ConfigQueries:
    """Configuration management queries."""
    
    @staticmethod
    def get_all_config() -> Dict[str, Any]:
        """Get all configuration values."""
        return ConfigModel.get_all()
    
    @staticmethod
    def update_config(key: str, value: Any, description: str = None) -> bool:
        """Update a configuration value."""
        try:
            ConfigModel.set(key, value, description)
            logger.info(f"Updated config: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating config {key}: {e}")
            return False
    
    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        return ConfigModel.get(key, default)

class AnalyticsQueries:
    """Analytics and reporting queries for file-based system."""
    
    @staticmethod
    def get_daily_stats(days: int = 30) -> List[Dict[str, Any]]:
        """Get daily file activity statistics."""
        try:
            query = """
                SELECT DATE(timestamp) as date,
                       COUNT(*) as change_count,
                       COUNT(DISTINCT file_path) as files_affected,
                       COUNT(DISTINCT change_type) as change_types
                FROM file_changes 
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """.format(days)
            
            rows = db.execute_query(query)
            stats = [dict(row) for row in rows]
            
            logger.info(f"Retrieved {len(stats)} days of statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving daily stats: {e}")
            return []
    
    @staticmethod
    def get_file_activity_stats() -> Dict[str, Any]:
        """Get file activity statistics."""
        try:
            # Most active files
            most_active_query = """
                SELECT file_path, COUNT(*) as change_count,
                       MAX(timestamp) as last_changed
                FROM file_changes
                GROUP BY file_path
                ORDER BY change_count DESC
                LIMIT 10
            """
            most_active_rows = db.execute_query(most_active_query)
            most_active_files = [dict(row) for row in most_active_rows]
            
            # Change type distribution
            change_types_query = """
                SELECT change_type, COUNT(*) as count
                FROM file_changes
                GROUP BY change_type
                ORDER BY count DESC
            """
            change_types_rows = db.execute_query(change_types_query)
            change_type_distribution = [dict(row) for row in change_types_rows]
            
            # Recent activity summary
            recent_activity_query = """
                SELECT COUNT(*) as total_changes,
                       COUNT(DISTINCT file_path) as files_affected,
                       MAX(timestamp) as last_activity
                FROM file_changes
                WHERE timestamp >= datetime('now', '-7 days')
            """
            recent_activity_rows = db.execute_query(recent_activity_query)
            recent_activity = dict(recent_activity_rows[0]) if recent_activity_rows else {}
            
            stats = {
                'most_active_files': most_active_files,
                'change_type_distribution': change_type_distribution,
                'recent_activity': recent_activity
            }
            
            logger.info("Retrieved file activity statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving file activity stats: {e}")
            return {}

logger.info("File-based query engine initialized successfully")