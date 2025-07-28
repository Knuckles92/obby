"""
🤖 SUBAGENT C: API Integration & Advanced Query Engine
======================================================

High-performance query layer for API endpoints with advanced search,
analytics, and real-time capabilities to replace all file operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json

from .models import (
    db, DiffModel, EventModel, SemanticModel, 
    ConfigModel, FileStateModel, PerformanceModel
)

logger = logging.getLogger(__name__)

class DiffQueries:
    """Advanced diff querying replacing file-based diff operations."""
    
    @staticmethod
    def get_recent_diffs(limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Get recent diffs with enhanced metadata - replaces /api/diffs endpoint."""
        try:
            # Build query with optional file filtering
            query = """
                SELECT 
                    id,
                    file_path as filePath,
                    base_name,
                    timestamp,
                    diff_content as content,
                    size,
                    content_hash,
                    created_at,
                    CASE 
                        WHEN LENGTH(diff_content) > 500 
                        THEN SUBSTR(diff_content, 1, 500) || '...'
                        ELSE diff_content 
                    END as preview
                FROM diffs
            """
            
            params = []
            if file_path:
                query += " WHERE file_path = ?"
                params.append(file_path)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = db.execute_query(query, tuple(params))
            
            # Format for API response
            diffs = []
            for row in rows:
                diff_entry = {
                    'id': str(row['id']),  # Convert to string for frontend
                    'filePath': row['filePath'],
                    'timestamp': row['timestamp'],
                    'content': row['preview'],  # Use preview for list view
                    'size': row['size'],
                    'fullPath': f"database://diffs/{row['id']}"  # Virtual path
                }
                diffs.append(diff_entry)
            
            logger.info(f"Retrieved {len(diffs)} recent diffs")
            return diffs
            
        except Exception as e:
            logger.error(f"Failed to get recent diffs: {e}")
            return []
    
    @staticmethod
    def get_diff_content(diff_id: int) -> Optional[Dict[str, Any]]:
        """Get full diff content for viewer - replaces file reading."""
        try:
            diff_data = DiffModel.get_by_id(diff_id)
            
            if not diff_data:
                return None
            
            return {
                'id': diff_data['id'],
                'filePath': diff_data['file_path'],
                'timestamp': diff_data['timestamp'],
                'content': diff_data['diff_content'],
                'size': diff_data['size'],
                'contentHash': diff_data['content_hash']
            }
            
        except Exception as e:
            logger.error(f"Failed to get diff content for {diff_id}: {e}")
            return None
    
    @staticmethod
    def search_diffs(query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search diff content with FTS."""
        try:
            search_query = """
                SELECT d.*, 
                       CASE 
                           WHEN LENGTH(d.diff_content) > 500 
                           THEN SUBSTR(d.diff_content, 1, 500) || '...'
                           ELSE d.diff_content 
                       END as preview
                FROM diffs d
                WHERE d.diff_content LIKE ? OR d.file_path LIKE ?
                ORDER BY d.timestamp DESC
                LIMIT ?
            """
            
            search_term = f"%{query}%"
            rows = db.execute_query(search_query, (search_term, search_term, limit))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Diff search failed: {e}")
            return []
    
    @staticmethod
    def get_diff_analytics() -> Dict[str, Any]:
        """Get diff analytics and statistics."""
        try:
            stats = {}
            
            # Total diffs
            total_result = db.execute_query("SELECT COUNT(*) as total FROM diffs")[0]
            stats['total_diffs'] = total_result['total']
            
            # Daily activity (last 7 days)
            daily_query = """
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM diffs 
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            stats['daily_activity'] = [dict(row) for row in db.execute_query(daily_query)]
            
            # Top files by diff count
            top_files_query = """
                SELECT file_path, COUNT(*) as diff_count
                FROM diffs
                GROUP BY file_path
                ORDER BY diff_count DESC
                LIMIT 10
            """
            stats['top_files'] = [dict(row) for row in db.execute_query(top_files_query)]
            
            # Recent activity trend
            trend_query = """
                SELECT 
                    COUNT(*) as total_last_24h,
                    COUNT(CASE WHEN timestamp >= datetime('now', '-1 hour') THEN 1 END) as last_hour
                FROM diffs
                WHERE timestamp >= datetime('now', '-24 hours')
            """
            trend_result = db.execute_query(trend_query)[0]
            stats['activity_trend'] = dict(trend_result)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get diff analytics: {e}")
            return {}
    
    @staticmethod
    def clear_all_diffs() -> Dict[str, Any]:
        """Clear all diffs - replaces /api/diffs/clear endpoint."""
        try:
            count = DiffModel.clear_all()
            message = f"Cleared {count} diffs successfully"
            logger.info(message)
            
            return {
                'message': message,
                'clearedCount': count
            }
            
        except Exception as e:
            error_msg = f"Failed to clear diffs: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'clearedCount': 0
            }

class EventQueries:
    """Event querying replacing in-memory event storage."""
    
    @staticmethod
    def get_recent_events(limit: int = 50, event_type: str = None) -> List[Dict[str, Any]]:
        """Get recent events - replaces in-memory recent_events list."""
        try:
            events = EventModel.get_recent(limit=limit, event_type=event_type)
            
            # Format for API response
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': f"event_{event['id']}",
                    'type': event['type'],
                    'path': event['path'],
                    'timestamp': event['timestamp'],
                    'size': event['size']
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Retrieved {len(formatted_events)} recent events")
            return formatted_events
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    @staticmethod
    def get_recent_tree_changes(limit: int = 10, time_window_minutes: int = 30) -> List[Dict[str, Any]]:
        """Get recent tree changes (created, deleted, moved) within a time window for diff context."""
        try:
            # Get recent tree events (created, deleted, moved)
            tree_events = EventModel.get_recent(limit=limit, event_type=None)  # Get all types first
            
            # Filter for tree change types and time window
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            
            recent_tree_changes = []
            for event in tree_events:
                # Check if it's a tree change event (created, deleted, moved)
                if event['type'] in ['created', 'deleted', 'moved']:
                    # Check if it's within our time window
                    event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) if isinstance(event['timestamp'], str) else event['timestamp']
                    if event_time >= cutoff_time:
                        recent_tree_changes.append(event)
            
            # Sort by timestamp descending (most recent first) and limit
            recent_tree_changes.sort(key=lambda x: x['timestamp'], reverse=True)
            recent_tree_changes = recent_tree_changes[:limit]
            
            logger.debug(f"Retrieved {len(recent_tree_changes)} recent tree changes within {time_window_minutes} minutes")
            return recent_tree_changes
            
        except Exception as e:
            logger.error(f"Failed to get recent tree changes: {e}")
            return []
    
    @staticmethod
    def add_event(event_type: str, path: str, size: int = 0) -> bool:
        """Add new event - replaces in-memory event addition."""
        try:
            EventModel.insert(event_type, path, size)
            logger.debug(f"Added event: {event_type} {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            return False
    
    @staticmethod
    def get_events_today_count() -> int:
        """Get today's event count for dashboard."""
        try:
            return EventModel.get_today_count()
        except Exception as e:
            logger.error(f"Failed to get today's event count: {e}")
            return 0
    
    @staticmethod
    def clear_all_events() -> Dict[str, Any]:
        """Clear all events - replaces /api/events/clear endpoint."""
        try:
            count = EventModel.clear_all()
            message = f"Cleared {count} events successfully"
            logger.info(message)
            
            return {
                'message': message,
                'clearedCount': count
            }
            
        except Exception as e:
            error_msg = f"Failed to clear events: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'clearedCount': 0
            }

class SemanticQueries:
    """Advanced semantic search replacing JSON file operations."""
    
    @staticmethod
    def search_semantic(query: str, limit: int = 20, change_type: str = None) -> Dict[str, Any]:
        """Enhanced semantic search - replaces /api/search endpoint."""
        try:
            # Perform FTS search
            results = SemanticModel.search(query, limit)
            
            # Filter by type if specified
            if change_type:
                results = [r for r in results if r.get('type') == change_type]
            
            # Format results with relevance scoring
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result['id'],
                    'timestamp': result['timestamp'],
                    'type': result['type'],
                    'summary': result['summary'],
                    'impact': result['impact'],
                    'topics': result['topics'],
                    'keywords': result['keywords'],
                    'file_path': result['file_path'],
                    'searchable_text': result['searchable_text'],
                    'relevance_score': result.get('rank', 0)
                }
                formatted_results.append(formatted_result)
            
            return {
                'results': formatted_results,
                'total': len(formatted_results),
                'query': query,
                'change_type_filter': change_type,
                'index_metadata': {
                    'total_entries': SemanticQueries._get_total_entries(),
                    'last_updated': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {
                'results': [],
                'total': 0,
                'query': query,
                'error': str(e)
            }
    
    @staticmethod
    def get_all_topics() -> Dict[str, Any]:
        """Get all topics - replaces /api/search/topics endpoint."""
        try:
            topics = SemanticModel.get_all_topics()
            
            return {
                'topics': topics,
                'total': len(topics)
            }
            
        except Exception as e:
            logger.error(f"Failed to get topics: {e}")
            return {
                'topics': [],
                'total': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_all_keywords() -> Dict[str, Any]:
        """Get all keywords with counts - replaces /api/search/keywords endpoint."""
        try:
            keywords = SemanticModel.get_all_keywords()
            
            return {
                'keywords': keywords,
                'total': len(keywords)
            }
            
        except Exception as e:
            logger.error(f"Failed to get keywords: {e}")
            return {
                'keywords': [],
                'total': 0,
                'error': str(e)
            }
    
    @staticmethod
    def _get_total_entries() -> int:
        """Get total semantic entries count."""
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM semantic_entries")[0]
            return result['count']
        except:
            return 0

class ConfigQueries:
    """Configuration management replacing config.json operations."""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get all configuration - replaces /api/config GET endpoint."""
        try:
            config = ConfigModel.get_all()
            
            # Ensure default values for API compatibility
            default_config = {
                'checkInterval': 20,
                'openaiApiKey': '',
                'aiModel': 'gpt-4.1-mini',
                'watchPaths': ['notes'],
                'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
                'periodicCheckEnabled': True
            }
            
            # Merge with database config
            default_config.update(config)
            
            return default_config
            
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return {}
    
    @staticmethod
    def update_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration - replaces /api/config PUT endpoint."""
        try:
            valid_fields = [
                'checkInterval', 'openaiApiKey', 'aiModel', 
                'ignorePatterns', 'periodicCheckEnabled'
            ]
            
            updated_count = 0
            for field in valid_fields:
                if field in config_data:
                    ConfigModel.set(field, config_data[field])
                    updated_count += 1
            
            logger.info(f"Updated {updated_count} configuration values")
            
            return {
                'message': 'Configuration updated successfully',
                'updated_fields': updated_count
            }
            
        except Exception as e:
            error_msg = f"Failed to update configuration: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg
            }

class AnalyticsQueries:
    """Advanced analytics and insights from database."""
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        try:
            stats = {}
            
            # Performance stats
            perf_stats = PerformanceModel.get_stats()
            stats.update(perf_stats)
            
            # Activity stats
            stats['events_today'] = EventQueries.get_events_today_count()
            
            # Diff stats
            recent_diffs = DiffQueries.get_recent_diffs(limit=5)
            stats['recent_diffs_count'] = len(recent_diffs)
            
            # System health
            stats['database_health'] = 'healthy'
            stats['last_updated'] = datetime.now().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {}
    
    @staticmethod
    def get_file_activity_heatmap(days: int = 30) -> List[Dict[str, Any]]:
        """Get file activity heatmap data."""
        try:
            query = """
                SELECT 
                    DATE(timestamp) as date,
                    file_path,
                    COUNT(*) as activity_count
                FROM diffs 
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(timestamp), file_path
                ORDER BY date DESC, activity_count DESC
            """
            
            rows = db.execute_query(query, (days,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get activity heatmap: {e}")
            return []
    
    @staticmethod
    def get_change_pattern_analysis() -> Dict[str, Any]:
        """Analyze change patterns and trends."""
        try:
            analysis = {}
            
            # Busiest hours
            hour_query = """
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    COUNT(*) as change_count
                FROM diffs
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY hour
                ORDER BY change_count DESC
            """
            analysis['busiest_hours'] = [dict(row) for row in db.execute_query(hour_query)]
            
            # Change velocity
            velocity_query = """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as changes,
                    COUNT(DISTINCT file_path) as files_changed
                FROM diffs
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            analysis['change_velocity'] = [dict(row) for row in db.execute_query(velocity_query)]
            
            # Impact distribution
            impact_query = """
                SELECT impact, COUNT(*) as count
                FROM semantic_entries
                GROUP BY impact
            """
            analysis['impact_distribution'] = [dict(row) for row in db.execute_query(impact_query)]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze change patterns: {e}")
            return {}

class RealTimeQueries:
    """Real-time data queries for WebSocket updates."""
    
    @staticmethod
    def get_live_activity(since: datetime = None) -> Dict[str, Any]:
        """Get activity since specified time for real-time updates."""
        try:
            if since is None:
                since = datetime.now() - timedelta(minutes=5)
            
            # Recent diffs
            diff_query = """
                SELECT 'diff' as type, file_path as path, timestamp, 'diff_created' as action
                FROM diffs
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """
            
            # Recent events  
            event_query = """
                SELECT 'event' as type, path, timestamp, type as action
                FROM events
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """
            
            diff_rows = db.execute_query(diff_query, (since,))
            event_rows = db.execute_query(event_query, (since,))
            
            # Combine and sort
            all_activity = []
            all_activity.extend([dict(row) for row in diff_rows])
            all_activity.extend([dict(row) for row in event_rows])
            
            # Sort by timestamp
            all_activity.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'activity': all_activity[:20],  # Limit to 20 most recent
                'timestamp': datetime.now().isoformat(),
                'count': len(all_activity)
            }
            
        except Exception as e:
            logger.error(f"Failed to get live activity: {e}")
            return {
                'activity': [],
                'timestamp': datetime.now().isoformat(),
                'count': 0,
                'error': str(e)
            }

logger.info("🤖 Subagent C: Query engine initialized successfully")