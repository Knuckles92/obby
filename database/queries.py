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
    def get_recent_diffs(limit: int = 20, offset: int = 0, file_path: str = None, watch_handler = None) -> List[Dict[str, Any]]:
        """Get recent file diffs with pagination support - replaces git-based diff endpoints."""
        try:
            if file_path:
                diffs = ContentDiffModel.get_for_file(file_path, limit=limit, offset=offset)
            else:
                # Get recent diffs from all files
                query = """
                    SELECT cd.*, fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                           fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                    FROM content_diffs cd
                    LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                    LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                    ORDER BY cd.timestamp DESC
                    LIMIT ? OFFSET ?
                """
                rows = db.execute_query(query, (limit, offset))
                diffs = [dict(row) for row in rows]
            
            # Format for API response
            formatted_diffs = []
            for diff in diffs:
                # Apply watch pattern filtering if watch_handler is provided
                if watch_handler is not None:
                    from pathlib import Path
                    file_path_obj = Path(diff['file_path'])
                    if not watch_handler.should_watch(file_path_obj):
                        continue  # Skip files that don't match watch patterns
                
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
            
            logger.info(f"Retrieved {len(formatted_diffs)} recent diffs (after filtering)")
            return formatted_diffs
            
        except Exception as e:
            logger.error(f"Error retrieving recent diffs: {e}")
            return []

    @staticmethod
    def get_diffs_since(since: datetime, limit: int = 200, file_path: str = None, watch_handler = None) -> List[Dict[str, Any]]:
        """Get content diffs strictly after a given timestamp, ordered ASC.

        This enables creating summaries scoped to the window since the last
        living-note update (cursor-based summarization).
        """
        try:
            if file_path:
                query = """
                    SELECT cd.*, fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                           fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                    FROM content_diffs cd
                    LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                    LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                    WHERE cd.timestamp > ? AND cd.file_path = ?
                    ORDER BY cd.timestamp ASC
                    LIMIT ?
                """
                rows = db.execute_query(query, (since, file_path, limit))
            else:
                query = """
                    SELECT cd.*, fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                           fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                    FROM content_diffs cd
                    LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                    LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                    WHERE cd.timestamp > ?
                    ORDER BY cd.timestamp ASC
                    LIMIT ?
                """
                rows = db.execute_query(query, (since, limit))

            diffs = [dict(row) for row in rows]

            formatted_diffs = []
            total_diffs_processed = 0
            filtered_out_count = 0
            
            for diff in diffs:
                total_diffs_processed += 1
                file_path = diff['file_path']
                
                # Optional watch filtering
                if watch_handler is not None:
                    from pathlib import Path
                    should_include = watch_handler.should_watch(Path(file_path))
                    logger.debug(f"Watch filter for '{file_path}': {'INCLUDE' if should_include else 'EXCLUDE'}")
                    
                    if not should_include:
                        filtered_out_count += 1
                        logger.debug(f"Filtering out file: {file_path}")
                        continue
                else:
                    logger.debug(f"No watch handler, including file: {file_path}")

                formatted_diffs.append({
                    'id': str(diff['id']),
                    'filePath': file_path,
                    'changeType': diff['change_type'],
                    'diffContent': diff['diff_content'],
                    'linesAdded': diff['lines_added'],
                    'linesRemoved': diff['lines_removed'],
                    'timestamp': diff['timestamp'],
                    'oldVersionId': diff['old_version_id'],
                    'newVersionId': diff['new_version_id']
                })

            logger.info(f"Diffs since {since}: processed {total_diffs_processed}, filtered out {filtered_out_count}, returning {len(formatted_diffs)}")
            if formatted_diffs:
                included_files = [d['filePath'] for d in formatted_diffs]
                logger.info(f"Included files: {included_files}")
            
            return formatted_diffs
        except Exception as e:
            logger.error(f"Error retrieving diffs since {since}: {e}")
            return []
    
    @staticmethod
    def get_diff_content(diff_id: str) -> Optional[Dict[str, Any]]:
        """Get content diff by ID."""
        try:
            query = """
                SELECT cd.*, 
                       fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                       fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                FROM content_diffs cd
                LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                WHERE cd.id = ?
            """
            rows = db.execute_query(query, (diff_id,))
            if rows:
                diff = dict(rows[0])
                logger.debug(f"Retrieved content diff by ID: {diff_id}")
                return {
                    'id': str(diff['id']),
                    'content': diff['diff_content'],
                    'filePath': diff['file_path'],
                    'changeType': diff['change_type'],
                    'linesAdded': diff['lines_added'],
                    'linesRemoved': diff['lines_removed'],
                    'timestamp': diff['timestamp'],
                    'oldVersionId': diff['old_version_id'],
                    'newVersionId': diff['new_version_id']
                }
            else:
                logger.warning(f"Content diff not found: {diff_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving content diff by ID {diff_id}: {e}")
            return None
    
    @staticmethod
    def get_diffs_count(file_path: str = None, watch_handler = None) -> int:
        """Get total count of diffs for pagination metadata."""
        try:
            if file_path:
                query = "SELECT COUNT(*) as count FROM content_diffs WHERE file_path = ?"
                params = (file_path,)
            else:
                query = "SELECT COUNT(*) as count FROM content_diffs"
                params = ()
            
            rows = db.execute_query(query, params)
            total_count = rows[0]['count'] if rows else 0
            
            # Apply watch pattern filtering if needed (approximation)
            if watch_handler is not None and not file_path:
                # Get sample of diffs to estimate filtered count
                sample_query = """
                    SELECT file_path FROM content_diffs 
                    ORDER BY timestamp DESC LIMIT 100
                """
                sample_rows = db.execute_query(sample_query)
                if sample_rows:
                    filtered_sample = 0
                    for row in sample_rows:
                        from pathlib import Path
                        file_path_obj = Path(row['file_path'])
                        if watch_handler.should_watch(file_path_obj):
                            filtered_sample += 1
                    
                    # Estimate total filtered count based on sample ratio
                    if len(sample_rows) > 0:
                        filter_ratio = filtered_sample / len(sample_rows)
                        total_count = int(total_count * filter_ratio)
            
            logger.info(f"Retrieved diffs count: {total_count}")
            return total_count
            
        except Exception as e:
            logger.error(f"Error retrieving diffs count: {e}")
            return 0
    
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
    def get_working_changes(status: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent file changes with pagination support - replaces git working changes."""
        try:
            file_changes = FileChangeModel.get_recent(limit=limit, offset=offset, change_type=status)
            
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
    def get_file_changes_count(status: str = None) -> int:
        """Get total count of file changes for pagination metadata."""
        try:
            count = FileChangeModel.get_count(change_type=status)
            logger.info(f"Retrieved file changes count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error retrieving file changes count: {e}")
            return 0
    
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
            
            total_cleared = content_diffs_cleared + file_versions_cleared + file_changes_cleared + file_states_cleared
            logger.info(f"Cleared all file data: {total_cleared} total records")
            return clear_result
            
        except Exception as e:
            logger.error(f"Error clearing file data: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def clear_unwatched_file_diffs(watch_handler) -> Dict[str, Any]:
        """Clear file diffs that no longer match watch patterns."""
        try:
            if watch_handler is None:
                return {'success': False, 'error': 'No watch handler provided'}
            
            # Get all content diffs
            query = "SELECT id, file_path FROM content_diffs"
            rows = db.execute_query(query)
            
            unwatched_diff_ids = []
            for row in rows:
                diff_id, file_path = row
                from pathlib import Path
                if not watch_handler.should_watch(Path(file_path)):
                    unwatched_diff_ids.append(diff_id)
            
            if not unwatched_diff_ids:
                logger.info("No unwatched file diffs found to clear")
                return {
                    'success': True,
                    'content_diffs_cleared': 0,
                    'message': 'No unwatched diffs found'
                }
            
            # Delete unwatched diffs
            placeholders = ','.join(['?' for _ in unwatched_diff_ids])
            delete_query = f"DELETE FROM content_diffs WHERE id IN ({placeholders})"
            cleared_count = db.execute_update(delete_query, unwatched_diff_ids)
            
            logger.info(f"Cleared {cleared_count} unwatched file diffs")
            return {
                'success': True,
                'content_diffs_cleared': cleared_count,
                'unwatched_files_removed': len(unwatched_diff_ids),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error clearing unwatched file diffs: {e}")
            return {'success': False, 'error': str(e)}

class EventQueries:
    """Event-focused queries for real-time updates and API endpoints."""
    
    @staticmethod
    def add_event(event_type: str, file_path: str, file_size: int = 0) -> Optional[int]:
        """Add a file system event to the database."""
        try:
            event_id = EventModel.insert(
                event_type=event_type,
                path=file_path,
                size=file_size
            )
            logger.debug(f"Added event to database: {event_type} {file_path} (ID: {event_id})")
            return event_id
            
        except Exception as e:
            logger.error(f"Error adding event to database: {e}")
            return None
    
    @staticmethod
    def mark_event_processed(event_id: int) -> bool:
        """Mark an event as processed."""
        try:
            success = EventModel.mark_processed(event_id)
            if success:
                logger.debug(f"Marked event {event_id} as processed")
            return success
            
        except Exception as e:
            logger.error(f"Error marking event {event_id} as processed: {e}")
            return False
    
    @staticmethod
    def get_recent_events(limit: int = 50, event_type: str = None, 
                         processed: bool = None) -> List[Dict[str, Any]]:
        """Get recent file system events."""
        try:
            # Try the direct database query approach first, fallback to EventModel if needed
            query = """
                SELECT id, type, path, timestamp, size, processed, created_at
                FROM events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            rows = db.execute_query(query, (limit,))
            events = [dict(row) for row in rows]
            
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
    def get_events_since(since: datetime, event_type: str = None) -> List[Dict[str, Any]]:
        """Get events since a timestamp, optionally filtered by type (e.g., 'created')."""
        try:
            query = "SELECT id, type, path, timestamp, size, processed FROM events WHERE timestamp > ?"
            params: List[Any] = [since]
            if event_type:
                query += " AND type = ?"
                params.append(event_type)
            query += " ORDER BY timestamp ASC"
            rows = db.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving events since {since}: {e}")
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
    
    @staticmethod
    def get_events_today_count() -> int:
        """Get count of events from today."""
        try:
            today = datetime.now().date()
            query = """
                SELECT COUNT(*) as count
                FROM events 
                WHERE DATE(timestamp) = ?
            """
            rows = db.execute_query(query, (today,))
            count = rows[0]['count'] if rows else 0
            
            logger.debug(f"Retrieved events today count: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error retrieving events today count: {e}")
            return 0
    
    @staticmethod
    def get_total_count() -> int:
        """Get total count of all events."""
        try:
            query = "SELECT COUNT(*) as count FROM events"
            rows = db.execute_query(query)
            count = rows[0]['count'] if rows else 0
            
            logger.debug(f"Retrieved total events count: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error retrieving total events count: {e}")
            return 0

    @staticmethod
    def clear_all_events() -> Dict[str, Any]:
        """Clear all events from the database."""
        try:
            # Count events before clearing
            count_query = "SELECT COUNT(*) as count FROM events"
            count_result = db.execute_query(count_query)
            events_count = count_result[0]['count'] if count_result else 0
            
            # Clear all events
            delete_query = "DELETE FROM events"
            db.execute_query(delete_query)
            
            logger.info(f"Cleared {events_count} events from database")
            return {
                'success': True,
                'message': f'Successfully cleared {events_count} events',
                'events_cleared': events_count
            }
            
        except Exception as e:
            logger.error(f"Error clearing events: {e}")
            return {
                'success': False,
                'error': f'Failed to clear events: {str(e)}'
            }
    
    @staticmethod
    def mark_events_processed(event_ids: List[int]) -> bool:
        """Mark events as processed."""
        try:
            if not event_ids:
                return True
                
            placeholders = ','.join(['?' for _ in event_ids])
            query = f"UPDATE events SET processed = TRUE WHERE id IN ({placeholders})"
            db.execute_query(query, event_ids)
            
            logger.info(f"Marked {len(event_ids)} events as processed")
            return True
            
        except Exception as e:
            logger.error(f"Error marking events as processed: {e}")
            return False
    
    @staticmethod
    def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific event by ID."""
        try:
            query = """
                SELECT id, type, path, timestamp, size, processed, created_at,
                       content, diff_content, summary
                FROM events 
                WHERE id = ?
            """
            rows = db.execute_query(query, (event_id,))
            if rows:
                event = dict(rows[0])
                logger.debug(f"Retrieved event by ID: {event_id}")
                return event
            else:
                logger.warning(f"Event not found: {event_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error retrieving event by ID {event_id}: {e}")
            return None

    @staticmethod 
    def get_events_for_file(file_path: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get events for a specific file."""
        try:
            query = """
                SELECT id, type, path, timestamp, size, processed, created_at
                FROM events
                WHERE path = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            rows = db.execute_query(query, (file_path, limit))
            events = [dict(row) for row in rows]
            
            logger.debug(f"Retrieved {len(events)} events for file: {file_path}")
            return events
            
        except Exception as e:
            logger.error(f"Error retrieving events for file {file_path}: {e}")
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
    def get_config() -> Dict[str, Any]:
        """Get all configuration values."""
        return ConfigModel.get_all()
        
    @staticmethod
    def get_all_config() -> Dict[str, Any]:
        """Get all configuration values."""
        return ConfigModel.get_all()
    
    @staticmethod
    def update_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration values."""
        try:
            for key, value in config_data.items():
                ConfigModel.set(key, value)
            logger.info(f"Updated config with {len(config_data)} values")
            return {'success': True, 'message': 'Configuration updated successfully'}
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return {'success': False, 'error': str(e)}
    
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
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """Get database-specific statistics."""
        try:
            # Count total records from various tables
            events_count_query = "SELECT COUNT(*) as count FROM events"
            diffs_count_query = "SELECT COUNT(*) as count FROM diffs"
            
            events_count = db.execute_query(events_count_query)[0]['count']
            diffs_count = db.execute_query(diffs_count_query)[0]['count']
            
            # Get database file size (approximate)
            db_path = db.db_path if hasattr(db, 'db_path') else 'obby.db'
            try:
                import os
                db_size_bytes = os.path.getsize(db_path)
                db_size = f"{db_size_bytes / (1024*1024):.2f} MB"
            except:
                db_size = "Unknown"
            
            # Last optimization time (placeholder - would need to track this)
            last_optimized = "Never"
            
            stats = {
                'total_records': events_count,
                'total_diffs': diffs_count,
                'index_size': db_size,
                'last_optimized': last_optimized,
                'query_performance': 85  # Placeholder value
            }
            
            logger.info("Retrieved database statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving database stats: {e}")
            return {}
    
    @staticmethod
    def optimize_database() -> Dict[str, Any]:
        """Optimize the database by running VACUUM and ANALYZE commands."""
        try:
            results = {}
            
            # Run VACUUM to reclaim space
            db.execute_query("VACUUM")
            results['vacuum'] = 'completed'
            
            # Run ANALYZE to update query planner statistics
            db.execute_query("ANALYZE")
            results['analyze'] = 'completed'
            
            # Rebuild FTS indexes if they exist
            try:
                db.execute_query("INSERT INTO events_fts(events_fts) VALUES('rebuild')")
                results['fts_rebuild'] = 'completed'
            except:
                results['fts_rebuild'] = 'skipped (no FTS tables)'
            
            logger.info("Database optimization completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            return {'error': str(e)}

# Duplicate EventQueries class removed - methods merged into the first EventQueries class above

logger.info("File-based query engine initialized successfully")