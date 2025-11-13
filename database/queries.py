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
        """Get recent file diffs with pagination support - replaces git-based diff endpoints.
        
        STRICT MODE: Always applies watch filtering. If watch_handler is None, it will be initialized.
        """
        try:
            # STRICT: Always initialize watch_handler if not provided
            if watch_handler is None:
                from utils.watch_handler import WatchHandler
                from pathlib import Path
                root_folder = Path.cwd()
                watch_handler = WatchHandler(root_folder)
                logger.debug("Initialized watch_handler for strict filtering in get_recent_diffs")
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
                # Exclude internal semantic index artifact to prevent stale content pollution
                try:
                    fp = str(diff['file_path']).lower()
                    if fp.endswith('semantic_index.json'):
                        continue
                except Exception:
                    pass
                
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
        session-summary update (cursor-based summarization).
        
        STRICT MODE: Always applies watch filtering. If watch_handler is None, it will be initialized.
        """
        try:
            # STRICT: Always initialize watch_handler if not provided
            if watch_handler is None:
                from utils.watch_handler import WatchHandler
                from pathlib import Path
                root_folder = Path.cwd()
                watch_handler = WatchHandler(root_folder)
                logger.debug("Initialized watch_handler for strict filtering in get_diffs_since")
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
                # Exclude internal semantic index artifact
                try:
                    if str(file_path).lower().endswith('semantic_index.json'):
                        filtered_out_count += 1
                        continue
                except Exception:
                    pass
                
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
    def get_comprehensive_time_analysis(start_time: datetime, end_time: datetime,
                                      focus_areas: List[str] = None, watch_handler = None,
                                      exclude_nonexistent: bool = True) -> Dict[str, Any]:
        """Get comprehensive analysis for a specific time range including diffs, files, and metrics.

        Args:
            start_time: Range start
            end_time: Range end
            focus_areas: Optional string filters to include file paths containing any of these
            watch_handler: Watch filter - if None, will be initialized for strict filtering
            exclude_nonexistent: If True, exclude files that no longer exist on disk to avoid
                stale context from deleted notes.
                
        STRICT MODE: Always applies watch filtering. If watch_handler is None, it will be initialized.
        """
        try:
            # STRICT: Always initialize watch_handler if not provided
            if watch_handler is None:
                from utils.watch_handler import WatchHandler
                from pathlib import Path
                root_folder = Path.cwd()
                watch_handler = WatchHandler(root_folder)
                logger.debug("Initialized watch_handler for strict filtering in get_comprehensive_time_analysis")
            logger.info(f"Starting comprehensive analysis for range: {start_time} to {end_time}")
            
            # 1. Get all diffs in time range
            diffs_query = """
                SELECT cd.*, fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                       fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                FROM content_diffs cd
                LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                WHERE cd.timestamp BETWEEN ? AND ?
                ORDER BY cd.timestamp ASC
            """
            diff_rows = db.execute_query(diffs_query, (start_time, end_time))
            
            # 2. Get file activity metrics
            file_metrics_query = """
                SELECT 
                    file_path,
                    COUNT(*) as change_count,
                    SUM(lines_added) as total_lines_added,
                    SUM(lines_removed) as total_lines_removed,
                    MAX(timestamp) as last_modified,
                    MIN(timestamp) as first_modified
                FROM content_diffs
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY file_path
                ORDER BY change_count DESC
            """
            file_metrics = db.execute_query(file_metrics_query, (start_time, end_time))
            
            # 3. Get semantic analysis for the period (if available)
            semantic_rows = []
            try:
                semantic_query = """
                    SELECT 
                        topics, keywords, summary, impact_level,
                        file_path, timestamp
                    FROM semantic_analysis
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """
                semantic_rows = db.execute_query(semantic_query, (start_time, end_time))
            except Exception as e:
                logger.warning(f"Semantic analysis table not available: {e}")
                semantic_rows = []
            
            # Process and format the data
            processed_diffs = []
            file_paths = set()
            total_lines_added = 0
            total_lines_removed = 0
            change_types = {}
            
            from pathlib import Path
            # Simple existence cache to avoid repeated filesystem checks
            exists_cache: dict[str, bool] = {}

            for diff in diff_rows:
                file_path = diff['file_path']
                # Exclude internal semantic index artifact
                try:
                    if str(file_path).lower().endswith('semantic_index.json'):
                        continue
                except Exception:
                    pass
                
                # Apply watch filtering if provided
                if watch_handler is not None:
                    if not watch_handler.should_watch(Path(file_path)):
                        continue
                
                # Apply focus area filtering if specified
                if focus_areas:
                    # Simple substring matching for focus areas (could be enhanced)
                    if not any(focus_area.lower() in file_path.lower() for focus_area in focus_areas):
                        continue

                # Exclude files that no longer exist on disk when requested
                if exclude_nonexistent:
                    try:
                        p = Path(file_path)
                        # Handle relative DB paths by resolving against CWD
                        exists = p.exists() or (Path.cwd() / p).exists()
                        exists_cache.setdefault(file_path, exists)
                        if not exists_cache[file_path]:
                            continue
                    except Exception:
                        # If existence check fails, keep safe path and include
                        pass
                
                file_paths.add(file_path)
                total_lines_added += diff['lines_added'] or 0
                total_lines_removed += diff['lines_removed'] or 0
                
                change_type = diff['change_type']
                change_types[change_type] = change_types.get(change_type, 0) + 1
                
                processed_diffs.append({
                    'id': str(diff['id']),
                    'filePath': file_path,
                    'changeType': change_type,
                    'diffContent': diff['diff_content'],
                    'linesAdded': diff['lines_added'],
                    'linesRemoved': diff['lines_removed'],
                    'timestamp': diff['timestamp']
                })
            
            # Process file metrics with filtering
            processed_file_metrics = []
            for metric in file_metrics:
                file_path = metric['file_path']
                # Exclude internal semantic index artifact
                try:
                    if str(file_path).lower().endswith('semantic_index.json'):
                        continue
                except Exception:
                    pass
                
                # Apply same filtering as diffs
                if watch_handler is not None:
                    if not watch_handler.should_watch(Path(file_path)):
                        continue
                
                if focus_areas:
                    if not any(focus_area.lower() in file_path.lower() for focus_area in focus_areas):
                        continue

                if exclude_nonexistent:
                    try:
                        if file_path in exists_cache:
                            if not exists_cache[file_path]:
                                continue
                        else:
                            p = Path(file_path)
                            exists = p.exists() or (Path.cwd() / p).exists()
                            exists_cache[file_path] = exists
                            if not exists:
                                continue
                    except Exception:
                        pass
                
                processed_file_metrics.append(dict(metric))
            
            # Process semantic analysis
            topics_summary = {}
            keywords_summary = {}
            impact_levels = {}
            
            for semantic in semantic_rows:
                # Parse JSON topics and keywords
                try:
                    topics = json.loads(semantic['topics']) if semantic['topics'] else []
                    keywords = json.loads(semantic['keywords']) if semantic['keywords'] else []
                    
                    for topic in topics:
                        topics_summary[topic] = topics_summary.get(topic, 0) + 1
                    
                    for keyword in keywords:
                        keywords_summary[keyword] = keywords_summary.get(keyword, 0) + 1
                    
                    impact = semantic['impact_level'] or 'moderate'
                    impact_levels[impact] = impact_levels.get(impact, 0) + 1
                    
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Calculate time span
            time_span = end_time - start_time
            
            analysis_result = {
                'timeRange': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'duration': str(time_span),
                    'durationHours': time_span.total_seconds() / 3600
                },
                'summary': {
                    'totalChanges': len(processed_diffs),
                    'filesAffected': len(file_paths),
                    'linesAdded': total_lines_added,
                    'linesRemoved': total_lines_removed,
                    'netLinesChanged': total_lines_added - total_lines_removed,
                    'changeTypes': change_types
                },
                'diffs': processed_diffs,
                'fileMetrics': processed_file_metrics[:20],  # Top 20 most active files
                'semanticAnalysis': {
                    'topTopics': dict(sorted(topics_summary.items(), key=lambda x: x[1], reverse=True)[:10]),
                    'topKeywords': dict(sorted(keywords_summary.items(), key=lambda x: x[1], reverse=True)[:10]),
                    'impactDistribution': impact_levels
                },
                'metadata': {
                    'focusAreas': focus_areas,
                    'watchFiltered': watch_handler is not None,
                    'analysisTimestamp': datetime.now().isoformat()
                }
            }
            
            logger.info(f"Comprehensive analysis completed: {len(processed_diffs)} diffs, {len(file_paths)} files")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in comprehensive time analysis: {e}")
            return {
                'timeRange': {'start': start_time.isoformat(), 'end': end_time.isoformat()},
                'summary': {'totalChanges': 0, 'filesAffected': 0},
                'error': str(e)
            }
    
    @staticmethod
    def get_activity_timeline(start_time: datetime, end_time: datetime, 
                            granularity: str = 'hour') -> List[Dict[str, Any]]:
        """Get activity timeline data for visualization."""
        try:
            # Determine SQL date formatting based on granularity
            if granularity == 'hour':
                date_format = "%Y-%m-%d %H:00:00"
                group_format = "strftime('%Y-%m-%d %H:00:00', timestamp)"
            elif granularity == 'day':
                date_format = "%Y-%m-%d"
                group_format = "strftime('%Y-%m-%d', timestamp)"
            else:  # Default to hour
                date_format = "%Y-%m-%d %H:00:00"
                group_format = "strftime('%Y-%m-%d %H:00:00', timestamp)"
            
            query = f"""
                SELECT 
                    {group_format} as time_bucket,
                    COUNT(*) as change_count,
                    SUM(lines_added) as lines_added,
                    SUM(lines_removed) as lines_removed,
                    COUNT(DISTINCT file_path) as files_affected
                FROM content_diffs
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY time_bucket
                ORDER BY time_bucket ASC
            """
            
            rows = db.execute_query(query, (start_time, end_time))
            
            timeline = []
            for row in rows:
                timeline.append({
                    'timestamp': row['time_bucket'],
                    'changeCount': row['change_count'],
                    'linesAdded': row['lines_added'] or 0,
                    'linesRemoved': row['lines_removed'] or 0,
                    'filesAffected': row['files_affected']
                })
            
            return timeline
            
        except Exception as e:
            logger.error(f"Error generating activity timeline: {e}")
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
        """Get total count of diffs for pagination metadata.
        
        STRICT MODE: Always applies watch filtering. If watch_handler is None, it will be initialized.
        """
        try:
            # STRICT: Always initialize watch_handler if not provided
            if watch_handler is None:
                from utils.watch_handler import WatchHandler
                from pathlib import Path
                root_folder = Path.cwd()
                watch_handler = WatchHandler(root_folder)
                logger.debug("Initialized watch_handler for strict filtering in get_diffs_count")
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
    def get_repository_status(monitoring_active: bool = None) -> Dict[str, Any]:
        """Get file monitoring system status - replaces git repository status.
        
        Args:
            monitoring_active: Optional monitoring status. If None, defaults to False (safe fallback).
        """
        try:
            # Get performance stats
            perf_stats = PerformanceModel.get_stats()
            
            # Get recent activity
            recent_versions = FileVersionModel.get_recent(limit=10)
            recent_changes = FileChangeModel.get_recent(limit=10)
            
            # Get tracked files count
            tracked_files = FileStateModel.get_all_tracked_files()
            
            status = {
                'monitoring_active': monitoring_active if monitoring_active is not None else False,
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
        """Clear file diffs that no longer match watch patterns - STRICT MODE with audit logging."""
        try:
            if watch_handler is None:
                return {'success': False, 'error': 'No watch handler provided'}
            
            # Get all content diffs
            query = "SELECT id, file_path FROM content_diffs"
            rows = db.execute_query(query)
            
            unwatched_diff_ids = []
            unwatched_files = set()
            for row in rows:
                diff_id, file_path = row
                from pathlib import Path
                if not watch_handler.should_watch(Path(file_path)):
                    unwatched_diff_ids.append(diff_id)
                    unwatched_files.add(file_path)
            
            # AUDIT: Log unwatched files being removed
            if unwatched_files:
                logger.warning(f"AUDIT: Removing {len(unwatched_files)} unwatched files from database:")
                for file_path in sorted(unwatched_files):
                    logger.warning(f"  - {file_path}")
            
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

    @staticmethod
    def clear_semantic_data() -> Dict[str, Any]:
        """Clear AI semantic summaries (entries, topics, keywords, FTS, comprehensive summaries, output files, config values)."""
        try:
            cleared = {
                'semantic_entries_cleared': 0,
                'semantic_topics_cleared': 0,
                'semantic_keywords_cleared': 0,
                'semantic_search_cleared': 0,
                'comprehensive_summaries_cleared': 0,
                'output_files_cleared': 0,
                'config_values_cleared': 0,
            }
            try:
                cleared['semantic_topics_cleared'] = db.execute_update("DELETE FROM semantic_topics")
            except Exception:
                pass
            try:
                cleared['semantic_keywords_cleared'] = db.execute_update("DELETE FROM semantic_keywords")
            except Exception:
                pass
            try:
                cleared['semantic_entries_cleared'] = db.execute_update("DELETE FROM semantic_entries")
            except Exception:
                pass
            try:
                cleared['semantic_search_cleared'] = db.execute_update("DELETE FROM semantic_search")
            except Exception:
                pass

            # Clear comprehensive_summaries table if it exists
            try:
                check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='comprehensive_summaries'"
                table_exists = db.execute_query(check_query)
                if table_exists:
                    cleared['comprehensive_summaries_cleared'] = db.execute_update("DELETE FROM comprehensive_summaries")
                    logger.info(f"Cleared {cleared['comprehensive_summaries_cleared']} comprehensive summaries")
            except Exception as e:
                logger.debug(f"Could not clear comprehensive_summaries table: {e}")

            # Also remove on-disk semantic index file if present
            try:
                from pathlib import Path
                index_path = Path('notes/semantic_index.json')
                if index_path.exists():
                    index_path.unlink()
                    cleared['semantic_index_removed'] = True
            except Exception:
                cleared['semantic_index_removed'] = False

            # Clear output markdown files (AI-generated summaries derived from database)
            try:
                from pathlib import Path
                output_daily_cleared = 0
                output_summaries_cleared = 0
                session_summary_cleared = 0

                # Clear daily session summaries
                output_daily_dir = Path('output/daily')
                if output_daily_dir.exists() and output_daily_dir.is_dir():
                    for file_path in output_daily_dir.glob('*.md'):
                        try:
                            file_path.unlink()
                            output_daily_cleared += 1
                        except Exception as file_err:
                            logger.warning(f"Failed to remove {file_path}: {file_err}")

                # Clear comprehensive summaries markdown files
                output_summaries_dir = Path('output/summaries')
                if output_summaries_dir.exists() and output_summaries_dir.is_dir():
                    for file_path in output_summaries_dir.glob('*.md'):
                        try:
                            file_path.unlink()
                            output_summaries_cleared += 1
                        except Exception as file_err:
                            logger.warning(f"Failed to remove {file_path}: {file_err}")

                # Clear single-file session summary if it exists
                session_summary_path = Path('output/session_summary.md')
                if session_summary_path.exists():
                    try:
                        session_summary_path.unlink()
                        session_summary_cleared = 1
                    except Exception as file_err:
                        logger.warning(f"Failed to remove {session_summary_path}: {file_err}")

                cleared['output_files_cleared'] = output_daily_cleared + output_summaries_cleared + session_summary_cleared
                cleared['output_files_detail'] = {
                    'daily': output_daily_cleared,
                    'summaries': output_summaries_cleared,
                    'session_summary': session_summary_cleared
                }
                if cleared['output_files_cleared'] > 0:
                    logger.info(f"Cleared {cleared['output_files_cleared']} output markdown files")
            except Exception as output_err:
                logger.warning(f"Failed to clear output files: {output_err}")
                cleared['output_files_cleared'] = 0

            # Clear AI-related config values
            try:
                from database.models import ConfigModel
                ai_config_keys = ['session_summary_last_update', 'last_comprehensive_summary']
                config_cleared_count = 0
                for key in ai_config_keys:
                    try:
                        # Check if config exists before trying to delete
                        existing = ConfigModel.get(key)
                        if existing is not None:
                            # Delete from config_values table
                            db.execute_update("DELETE FROM config_values WHERE key = ?", (key,))
                            config_cleared_count += 1
                            logger.debug(f"Cleared config value: {key}")
                    except Exception as config_err:
                        logger.debug(f"Could not clear config value {key}: {config_err}")
                
                cleared['config_values_cleared'] = config_cleared_count
                if config_cleared_count > 0:
                    logger.info(f"Cleared {config_cleared_count} AI-related config values")
            except Exception as config_err:
                logger.warning(f"Failed to clear AI-related config values: {config_err}")
                cleared['config_values_cleared'] = 0

            return {'success': True, **cleared}
        except Exception as e:
            logger.error(f"Error clearing semantic data: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def clear_nonexistent_file_diffs() -> Dict[str, Any]:
        """Clear content diffs for files that no longer exist on disk.

        This helps prevent historical diffs for deleted files from influencing
        current summaries when users prefer current-only context.
        """
        try:
            # Get distinct file paths from content_diffs
            rows = db.execute_query("SELECT DISTINCT file_path FROM content_diffs")
            from pathlib import Path
            missing_paths: list[str] = []

            for row in rows:
                file_path = row['file_path']
                try:
                    p = Path(file_path)
                    exists = p.exists() or (Path.cwd() / p).exists()
                    if not exists:
                        missing_paths.append(file_path)
                except Exception:
                    # If check fails, do not treat as missing
                    pass

            if not missing_paths:
                return {
                    'success': True,
                    'content_diffs_cleared': 0,
                    'files_affected': 0,
                    'message': 'No diffs for non-existent files found'
                }

            # Delete diffs for missing paths
            placeholders = ','.join(['?' for _ in missing_paths])
            delete_diffs_query = f"DELETE FROM content_diffs WHERE file_path IN ({placeholders})"
            cleared_diffs = db.execute_update(delete_diffs_query, tuple(missing_paths))

            # Optionally clean up recent file_changes for those paths as well
            try:
                delete_changes_query = f"DELETE FROM file_changes WHERE file_path IN ({placeholders})"
                cleared_changes = db.execute_update(delete_changes_query, tuple(missing_paths))
            except Exception:
                cleared_changes = 0

            logger.info(f"Cleared {cleared_diffs} diffs and {cleared_changes} changes for {len(missing_paths)} non-existent files")
            return {
                'success': True,
                'content_diffs_cleared': cleared_diffs,
                'file_changes_cleared': cleared_changes,
                'files_affected': len(missing_paths)
            }
        except Exception as e:
            logger.error(f"Error clearing diffs for non-existent files: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_recent_changes_without_ai_summary(limit: int = None) -> List[Dict[str, Any]]:
        """Get recent file changes that don't have corresponding AI summaries yet."""
        try:
            # Get content diffs that don't have semantic entries
            base_query = """
                SELECT cd.id, cd.file_path, cd.diff_content, cd.timestamp, cd.change_type,
                       cd.lines_added, cd.lines_removed
                FROM content_diffs cd
                LEFT JOIN semantic_entries se ON cd.file_path = se.file_path 
                    AND cd.timestamp <= se.timestamp
                WHERE se.id IS NULL
                    AND cd.diff_content IS NOT NULL 
                    AND cd.diff_content != ''
                    AND LOWER(cd.file_path) NOT LIKE '%semantic_index.json'
                ORDER BY cd.timestamp DESC
            """
            
            # Add LIMIT only if specified
            if limit is not None:
                query = base_query + " LIMIT ?"
                rows = db.execute_query(query, (limit,))
            else:
                # No limit - get ALL changes without AI summaries  
                query = base_query
                rows = db.execute_query(query)
            
            changes = []
            for row in rows:
                changes.append({
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'diff_content': row['diff_content'],
                    'timestamp': row['timestamp'],
                    'change_type': row['change_type'],
                    'lines_added': row['lines_added'],
                    'lines_removed': row['lines_removed']
                })
            
            logger.info(f"Found {len(changes)} recent changes without AI summaries")
            return changes

        except Exception as e:
            logger.error(f"Error getting recent changes without AI summaries: {e}")
            return []

    @staticmethod
    def get_diffs_in_range(
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        file_filters: Optional['FileFilters'] = None,
        content_type_filters: Optional['ContentTypeFilters'] = None,
        max_files: int = 200,
        watch_handler = None
    ) -> List[Dict[str, Any]]:
        """Get diffs within a flexible time range with context filtering.

        Args:
            start_time: Range start (None = all time)
            end_time: Range end (None = now)
            file_filters: File pattern filters from SummaryContextConfig
            content_type_filters: Content type filters from SummaryContextConfig
            max_files: Maximum number of files to return
            watch_handler: Watch filter - if None, will be initialized

        Returns:
            List of formatted diffs matching the criteria
        """
        from pathlib import Path
        from fnmatch import fnmatch

        try:
            # STRICT: Always initialize watch_handler if not provided
            if watch_handler is None:
                from utils.watch_handler import WatchHandler
                root_folder = Path.cwd()
                watch_handler = WatchHandler(root_folder)
                logger.debug("Initialized watch_handler for strict filtering in get_diffs_in_range")

            # Build time range query
            if start_time and end_time:
                time_condition = "cd.timestamp BETWEEN ? AND ?"
                time_params = (start_time, end_time)
            elif start_time:
                time_condition = "cd.timestamp > ?"
                time_params = (start_time,)
            elif end_time:
                time_condition = "cd.timestamp <= ?"
                time_params = (end_time,)
            else:
                time_condition = "1=1"
                time_params = ()

            query = f"""
                SELECT cd.*, fv_old.content_hash as old_hash, fv_old.timestamp as old_timestamp,
                       fv_new.content_hash as new_hash, fv_new.timestamp as new_timestamp
                FROM content_diffs cd
                LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
                LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                WHERE {time_condition}
                ORDER BY cd.timestamp ASC
            """

            rows = db.execute_query(query, time_params)
            diffs = [dict(row) for row in rows]

            # Apply filters
            formatted_diffs = []
            file_count = 0
            unique_files = set()

            for diff in diffs:
                file_path = diff['file_path']

                # Exclude internal semantic index artifact
                if str(file_path).lower().endswith('semantic_index.json'):
                    continue

                # Apply watch filtering (respects .obbywatch if enabled)
                if watch_handler is not None:
                    use_obbywatch = not file_filters or file_filters.use_obbywatch_defaults
                    if use_obbywatch and not watch_handler.should_watch(Path(file_path)):
                        continue

                # Apply file pattern filters
                if file_filters:
                    # Include patterns
                    if file_filters.include_patterns:
                        matches_include = any(
                            fnmatch(file_path, pattern)
                            for pattern in file_filters.include_patterns
                        )
                        if not matches_include:
                            continue

                    # Exclude patterns
                    if file_filters.exclude_patterns:
                        matches_exclude = any(
                            fnmatch(file_path, pattern)
                            for pattern in file_filters.exclude_patterns
                        )
                        if matches_exclude:
                            continue

                    # Specific paths
                    if file_filters.specific_paths and file_path not in file_filters.specific_paths:
                        continue

                # Apply content type filters
                if content_type_filters:
                    # File type filtering
                    is_code = any(file_path.endswith(ext) for ext in ['.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.cpp', '.c', '.go', '.rs'])
                    is_doc = file_path.endswith('.md')

                    if not content_type_filters.include_code_files and is_code:
                        continue
                    if not content_type_filters.include_documentation and is_doc:
                        continue

                    # Deleted files filter
                    if not content_type_filters.include_deleted and diff['change_type'] == 'deleted':
                        continue

                # Track unique files and enforce max_files limit
                if file_path not in unique_files:
                    unique_files.add(file_path)
                    file_count = len(unique_files)

                    if file_count > max_files:
                        logger.info(f"Reached max_files limit ({max_files}), truncating results")
                        break

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

            logger.info(f"get_diffs_in_range: {len(formatted_diffs)} diffs from {len(unique_files)} unique files")
            return formatted_diffs

        except Exception as e:
            logger.error(f"Error in get_diffs_in_range: {e}")
            return []

    @staticmethod
    def get_preview_data(
        context_config: 'SummaryContextConfig',
        watch_handler = None
    ) -> Dict[str, Any]:
        """Generate preview data for summary generation without full diff content.

        Args:
            context_config: Complete context configuration
            watch_handler: Watch filter - if None, will be initialized

        Returns:
            Preview data with matched files, stats, and warnings
        """
        from pathlib import Path
        from utils.summary_context import MatchedFile

        try:
            # STRICT: Always initialize watch_handler if not provided
            if watch_handler is None:
                from utils.watch_handler import WatchHandler
                root_folder = Path.cwd()
                watch_handler = WatchHandler(root_folder)
                logger.debug("Initialized watch_handler for strict filtering in get_preview_data")

            # Parse time window
            time_window = context_config.time_window
            if time_window.preset and time_window.preset != "custom" and time_window.preset != "auto":
                # Parse preset (e.g., "1h", "6h", "24h", "7d")
                preset = time_window.preset
                if preset.endswith('h'):
                    hours = int(preset[:-1])
                    start_time = datetime.now() - timedelta(hours=hours)
                elif preset.endswith('d'):
                    days = int(preset[:-1])
                    start_time = datetime.now() - timedelta(days=days)
                else:
                    start_time = datetime.now() - timedelta(hours=4)  # Default
                end_time = datetime.now()

                # If include_previously_covered is False (default), restrict to changes since last summary
                if not time_window.include_previously_covered:
                    last_update = ConfigModel.get('session_summary_last_update')
                    if last_update:
                        last_summary_time = datetime.fromisoformat(last_update)
                        # Use the more restrictive (later) of the two timestamps
                        if last_summary_time > start_time:
                            logger.info(f"Preview: Restricting time window to changes since last summary: {last_summary_time}")
                            start_time = last_summary_time
            elif time_window.preset == "auto":
                # Auto = since last update (cursor-based)
                last_update = ConfigModel.get('session_summary_last_update')
                if last_update:
                    start_time = datetime.fromisoformat(last_update)
                else:
                    start_time = datetime.now() - timedelta(hours=4)
                end_time = datetime.now()
            else:
                start_time = time_window.start_date
                end_time = time_window.end_date or datetime.now()

                # If include_previously_covered is False, restrict to changes since last summary
                if not time_window.include_previously_covered:
                    last_update = ConfigModel.get('session_summary_last_update')
                    if last_update:
                        last_summary_time = datetime.fromisoformat(last_update)
                        # Use the more restrictive (later) of the two timestamps
                        if last_summary_time > start_time:
                            logger.info(f"Preview: Restricting custom time window to changes since last summary: {last_summary_time}")
                            start_time = last_summary_time

            # Get diffs in range
            diffs = FileQueries.get_diffs_in_range(
                start_time=start_time,
                end_time=end_time,
                file_filters=context_config.file_filters,
                content_type_filters=context_config.content_types,
                max_files=context_config.scope_controls.max_files,
                watch_handler=watch_handler
            )

            # Build matched files list
            matched_files = []
            file_stats = {}

            for diff in diffs:
                file_path = diff['filePath']

                if file_path not in file_stats:
                    file_stats[file_path] = {
                        'lines_added': 0,
                        'lines_removed': 0,
                        'changes': 0,
                        'last_modified': diff['timestamp']
                    }

                file_stats[file_path]['lines_added'] += diff['linesAdded'] or 0
                file_stats[file_path]['lines_removed'] += diff['linesRemoved'] or 0
                file_stats[file_path]['changes'] += 1

                if diff['timestamp'] > file_stats[file_path]['last_modified']:
                    file_stats[file_path]['last_modified'] = diff['timestamp']

            # Convert to MatchedFile objects
            for file_path, stats in file_stats.items():
                change_summary = f"{stats['changes']} change(s), +{stats['lines_added']}/-{stats['lines_removed']} lines"

                # Get file size if exists
                size_bytes = None
                try:
                    p = Path(file_path)
                    if p.exists():
                        size_bytes = p.stat().st_size
                except Exception:
                    pass

                matched_files.append(MatchedFile(
                    path=file_path,
                    change_summary=change_summary,
                    last_modified=datetime.fromisoformat(stats['last_modified']) if isinstance(stats['last_modified'], str) else stats['last_modified'],
                    size_bytes=size_bytes,
                    is_deleted=not Path(file_path).exists()
                ))

            # Calculate totals
            total_files = len(matched_files)
            total_changes = len(diffs)
            total_lines_added = sum(stats['lines_added'] for stats in file_stats.values())
            total_lines_removed = sum(stats['lines_removed'] for stats in file_stats.values())

            # Build filters applied list
            filters_applied = []
            if time_window.preset:
                filters_applied.append(f"Time window: {time_window.get_description()}")
            if context_config.file_filters.include_patterns:
                filters_applied.append(f"Include patterns: {', '.join(context_config.file_filters.include_patterns)}")
            if context_config.file_filters.exclude_patterns:
                filters_applied.append(f"Exclude patterns: {', '.join(context_config.file_filters.exclude_patterns)}")
            if context_config.scope_controls.max_files:
                filters_applied.append(f"Max files: {context_config.scope_controls.max_files}")
            if context_config.scope_controls.detail_level != "standard":
                filters_applied.append(f"Detail level: {context_config.scope_controls.detail_level}")
            if context_config.scope_controls.focus_areas:
                filters_applied.append(f"Focus areas: {', '.join(context_config.scope_controls.focus_areas)}")

            # Generate warnings
            warnings = []
            if total_files == 0:
                warnings.append("No files matched the specified criteria")
            elif total_files >= context_config.scope_controls.max_files:
                warnings.append(f"File limit reached ({context_config.scope_controls.max_files}). Consider narrowing your filters.")

            if total_changes == 0:
                warnings.append("No changes found in the specified time window")

            preview_data = {
                'matched_files': [f.to_dict() for f in matched_files],
                'time_range_description': time_window.get_description(),
                'total_files': total_files,
                'total_changes': total_changes,
                'total_lines_added': total_lines_added,
                'total_lines_removed': total_lines_removed,
                'filters_applied': filters_applied,
                'warnings': warnings
            }

            logger.info(f"Preview generated: {total_files} files, {total_changes} changes")
            return preview_data

        except Exception as e:
            logger.error(f"Error generating preview data: {e}")
            return {
                'matched_files': [],
                'time_range_description': 'Error',
                'total_files': 0,
                'total_changes': 0,
                'total_lines_added': 0,
                'total_lines_removed': 0,
                'filters_applied': [],
                'warnings': [f"Error generating preview: {str(e)}"]
            }

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
    def clear_all_events() -> int:
        """Clear all events from the database and return number cleared."""
        try:
            # Count events before clearing
            count_query = "SELECT COUNT(*) as count FROM events"
            count_result = db.execute_query(count_query)
            events_count = count_result[0]['count'] if count_result else 0
            
            # Clear all events
            delete_query = "DELETE FROM events"
            db.execute_update(delete_query)
            
            logger.info(f"Cleared {events_count} events from database")
            return events_count
            
        except Exception as e:
            logger.error(f"Error clearing events: {e}")
            return 0
    
    @staticmethod
    def mark_events_processed(event_ids: List[int]) -> bool:
        """Mark events as processed."""
        try:
            if not event_ids:
                return True
                
            placeholders = ','.join(['?' for _ in event_ids])
            query = f"UPDATE events SET processed = TRUE WHERE id IN ({placeholders})"
            db.execute_update(query, event_ids)
            
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
                SELECT id, type, path, timestamp, size, processed, created_at
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

    @staticmethod
    def search_semantic(query: str, limit: int = 20, change_type: str = None) -> Dict[str, Any]:
        """Search semantic entries with full-text capabilities.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            change_type: Optional filter by entry type ('content', 'tree', etc.)
            
        Returns:
            Dict containing search results and metadata
        """
        try:
            # Build search query for semantic entries
            base_query = """
                SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path, se.source_type,
                       GROUP_CONCAT(st.topic) as topics,
                       GROUP_CONCAT(sk.keyword) as keywords
                FROM semantic_entries se
                LEFT JOIN semantic_topics st ON se.id = st.entry_id
                LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                WHERE 1=1
            """
            
            params = []
            
            # Add search condition - search in summary, topics, and keywords
            base_query += """
                AND (se.summary LIKE ? OR se.summary LIKE ? OR
                     EXISTS (SELECT 1 FROM semantic_topics st2 WHERE st2.entry_id = se.id AND st2.topic LIKE ?) OR
                     EXISTS (SELECT 1 FROM semantic_keywords sk2 WHERE sk2.entry_id = se.id AND sk2.keyword LIKE ?))
            """
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            
            # Add type filter if specified
            if change_type:
                base_query += " AND se.source_type = ?"
                params.append(change_type)
            
            # Group and order results
            base_query += """
                GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path, se.source_type
                ORDER BY se.timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            rows = db.execute_query(base_query, params)
            
            # Format results
            results = []
            for row in rows:
                result = {
                    'id': str(row['id']),
                    'summary': row['summary'],
                    'type': row['source_type'],
                    'impact': row['impact'],
                    'filePath': row['file_path'],
                    'timestamp': row['timestamp'],
                    'topics': row['topics'].split(',') if row['topics'] else [],
                    'keywords': row['keywords'].split(',') if row['keywords'] else []
                }
                results.append(result)
            
            logger.info(f"Semantic search for '{query}' returned {len(results)} results")
            
            return {
                'query': query,
                'results': results,
                'total_results': len(results),
                'limit': limit,
                'change_type': change_type
            }
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return {
                'query': query,
                'results': [],
                'total_results': 0,
                'limit': limit,
                'error': str(e)
            }

    @staticmethod
    def search_semantic_index(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search semantic index for session summary summaries.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching semantic entries
        """
        try:
            # Search specifically in session summary entries
            search_query = """
                SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path,
                       GROUP_CONCAT(st.topic) as topics,
                       GROUP_CONCAT(sk.keyword) as keywords
                FROM semantic_entries se
                LEFT JOIN semantic_topics st ON se.id = st.entry_id  
                LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                WHERE se.source_type = 'session_summary'
                  AND (se.summary LIKE ? OR 
                       EXISTS (SELECT 1 FROM semantic_topics st2 WHERE st2.entry_id = se.id AND st2.topic LIKE ?) OR
                       EXISTS (SELECT 1 FROM semantic_keywords sk2 WHERE sk2.entry_id = se.id AND sk2.keyword LIKE ?))
                GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path
                ORDER BY se.timestamp DESC
                LIMIT ?
            """
            
            search_pattern = f"%{query}%"
            rows = db.execute_query(search_query, (search_pattern, search_pattern, search_pattern, limit))
            
            # Format results  
            results = []
            for row in rows:
                result = {
                    'id': str(row['id']),
                    'summary': row['summary'],
                    'impact': row['impact'],
                    'file_path': row['file_path'],
                    'markdown_file_path': row['markdown_file_path'],
                    'timestamp': row['timestamp'],
                    'topics': row['topics'].split(',') if row['topics'] else [],
                    'keywords': row['keywords'].split(',') if row['keywords'] else []
                }
                results.append(result)
            
            logger.info(f"Semantic index search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic index search: {e}")
            return []

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
            diffs_count_query = "SELECT COUNT(*) as count FROM content_diffs"
            
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
    
    @staticmethod
    def reset_database(confirmation_phrase: str, backup_enabled: bool = True) -> Dict[str, Any]:
        """Completely reset the database with safety measures and backup creation."""
        try:
            import shutil
            import os
            from datetime import datetime
            
            # Validate confirmation phrase exactly
            expected_phrase = "if i ruin my database it is my fault"
            if confirmation_phrase.strip().lower() != expected_phrase:
                return {
                    'success': False,
                    'error': 'Invalid confirmation phrase. Reset aborted.',
                    'expected_phrase': expected_phrase
                }
            
            results = {
                'backup_created': False,
                'backup_path': None,
                'tables_reset': [],
                'total_records_deleted': 0,
                'reset_timestamp': datetime.now().isoformat()
            }
            
            # Create backup if enabled
            if backup_enabled:
                try:
                    db_path = db.db_path if hasattr(db, 'db_path') else 'obby.db'
                    if os.path.exists(db_path):
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_path = f"{db_path}.backup_{timestamp}"
                        shutil.copy2(db_path, backup_path)
                        results['backup_created'] = True
                        results['backup_path'] = backup_path
                        logger.info(f"Database backup created at: {backup_path}")
                except Exception as backup_error:
                    logger.warning(f"Failed to create backup: {backup_error}")
                    results['backup_error'] = str(backup_error)
            
            # Define all tables to reset (from both old and new schema)
            tables_to_reset = [
                # Core file tracking tables
                'content_diffs',
                'file_versions', 
                'file_changes',
                'events',
                'file_states',
                
                # Semantic analysis tables
                'semantic_entries',
                'semantic_topics', 
                'semantic_keywords',
                
                # Comprehensive summaries table
                'comprehensive_summaries',
                
                # (Removed legacy git_* tables)
                # (Removed legacy session_summary_sessions and session_summary_entries - these tables don't exist)
                
                # Metadata tables
                'migration_log',
                'watch_patterns'
            ]
            
            # Reset tables in transaction for safety
            total_deleted = 0
            
            # Start transaction
            db.execute_query("BEGIN TRANSACTION")
            
            try:
                for table in tables_to_reset:
                    try:
                        # Check if table exists
                        check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
                        table_exists = db.execute_query(check_query, (table,))
                        
                        if table_exists:
                            # Count records before deletion
                            count_query = f"SELECT COUNT(*) as count FROM {table}"
                            count_result = db.execute_query(count_query)
                            record_count = count_result[0]['count'] if count_result else 0
                            
                            # Delete all records from table
                            delete_query = f"DELETE FROM {table}"
                            db.execute_query(delete_query)
                            
                            results['tables_reset'].append({
                                'table': table,
                                'records_deleted': record_count
                            })
                            total_deleted += record_count
                            
                            logger.info(f"Reset table {table}: {record_count} records deleted")
                    
                    except Exception as table_error:
                        logger.warning(f"Failed to reset table {table}: {table_error}")
                        # Continue with other tables
                
                # Clear FTS tables if they exist
                try:
                    db.execute_query("DELETE FROM semantic_search")
                    logger.info("Cleared FTS semantic_search table")
                except:
                    pass  # FTS table might not exist
                
                # Reset critical configuration values to defaults
                try:
                    # Keep essential config but reset others
                    essential_keys = ['dbVersion', 'aiModel', 'checkInterval']
                    placeholders = ','.join(['?' for _ in essential_keys])
                    reset_config_query = f"DELETE FROM config_values WHERE key NOT IN ({placeholders})"
                    config_deleted = db.execute_update(reset_config_query, essential_keys)
                    
                    # Re-insert default values
                    default_configs = [
                        ('enableRealTimeUpdates', 'true', 'bool', 'Enable real-time WebSocket updates'),
                        ('fileMonitoringEnabled', 'true', 'bool', 'Enable file-based change tracking'),
                        ('maxFileVersions', '100', 'int', 'Maximum number of versions to retain per file')
                    ]
                    
                    for key, value, type_val, desc in default_configs:
                        insert_config = "INSERT OR REPLACE INTO config_values (key, value, type, description) VALUES (?, ?, ?, ?)"
                        db.execute_query(insert_config, (key, value, type_val, desc))
                    
                    results['config_reset'] = f"{config_deleted} config values reset"
                    
                except Exception as config_error:
                    logger.warning(f"Failed to reset config: {config_error}")
                
                # Commit transaction
                db.execute_query("COMMIT")
                
                results['success'] = True
                results['total_records_deleted'] = total_deleted
                results['message'] = f"Database reset successfully. {total_deleted} total records deleted from {len(results['tables_reset'])} tables."
                
                logger.info(f"Database reset completed successfully: {total_deleted} records deleted")
                
                # Run optimization after reset
                try:
                    db.execute_query("VACUUM")
                    db.execute_query("ANALYZE") 
                    results['post_reset_optimization'] = 'completed'
                except Exception as opt_error:
                    logger.warning(f"Post-reset optimization failed: {opt_error}")
                
                # Best-effort cleanup of legacy/auxiliary on-disk artifacts outside SQLite
                try:
                    from pathlib import Path
                    index_path = Path('notes/semantic_index.json')
                    if index_path.exists():
                        index_path.unlink()
                        logger.info("Removed notes/semantic_index.json during database reset")
                        results['files_removed'] = results.get('files_removed', []) + [str(index_path)]
                except Exception as fs_err:
                    logger.warning(f"Failed to remove notes/semantic_index.json: {fs_err}")
                    results['files_removed_error'] = str(fs_err)

                # Clear output folder contents (AI-generated summaries derived from database)
                try:
                    from pathlib import Path
                    output_daily_cleared = 0
                    output_summaries_cleared = 0

                    # Clear daily session summaries
                    output_daily_dir = Path('output/daily')
                    if output_daily_dir.exists() and output_daily_dir.is_dir():
                        for file_path in output_daily_dir.glob('*.md'):
                            try:
                                file_path.unlink()
                                output_daily_cleared += 1
                                logger.debug(f"Removed daily summary: {file_path}")
                            except Exception as file_err:
                                logger.warning(f"Failed to remove {file_path}: {file_err}")

                    # Clear comprehensive summaries
                    output_summaries_dir = Path('output/summaries')
                    if output_summaries_dir.exists() and output_summaries_dir.is_dir():
                        for file_path in output_summaries_dir.glob('*.md'):
                            try:
                                file_path.unlink()
                                output_summaries_cleared += 1
                                logger.debug(f"Removed comprehensive summary: {file_path}")
                            except Exception as file_err:
                                logger.warning(f"Failed to remove {file_path}: {file_err}")

                    # Clear single-file session summary if it exists
                    session_summary_path = Path('output/session_summary.md')
                    if session_summary_path.exists():
                        try:
                            session_summary_path.unlink()
                            output_daily_cleared += 1
                            logger.debug(f"Removed single-file session summary: {session_summary_path}")
                        except Exception as file_err:
                            logger.warning(f"Failed to remove {session_summary_path}: {file_err}")

                    total_output_cleared = output_daily_cleared + output_summaries_cleared
                    results['output_files_cleared'] = {
                        'daily': output_daily_cleared,
                        'summaries': output_summaries_cleared,
                        'total': total_output_cleared
                    }

                    if total_output_cleared > 0:
                        logger.info(f"Cleared {total_output_cleared} output files during database reset (daily: {output_daily_cleared}, summaries: {output_summaries_cleared})")

                except Exception as output_err:
                    logger.warning(f"Failed to clear output folder: {output_err}")
                    results['output_clear_error'] = str(output_err)

                return results
                
            except Exception as reset_error:
                # Rollback transaction on error
                db.execute_query("ROLLBACK")
                raise reset_error
                
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return {
                'success': False,
                'error': f'Failed to reset database: {str(e)}',
                'backup_path': results.get('backup_path') if 'results' in locals() else None
            }

logger.info("File-based query engine initialized successfully")
