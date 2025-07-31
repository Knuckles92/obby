"""
Git-Native API Integration & Advanced Query Engine
==================================================

High-performance query layer for API endpoints with git-based search,
analytics, and real-time capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json

from .models import (
    db, GitCommitModel, GitFileChangeModel, GitWorkingChangeModel,
    GitRepositoryStateModel, EventModel, SemanticModel, 
    ConfigModel, FileStateModel, PerformanceModel
)

logger = logging.getLogger(__name__)

class GitQueries:
    """Git-focused queries for API endpoints."""
    
    @staticmethod
    def get_recent_diffs(limit: int = 20, file_path: str = None) -> List[Dict[str, Any]]:
        """Legacy compatibility method - maps to get_recent_commits."""
        return GitQueries.get_recent_commits(limit=limit)
    
    @staticmethod  
    def get_recent_commits(limit: int = 20, branch: str = None) -> List[Dict[str, Any]]:
        """Get recent commits - replaces /api/diffs endpoint."""
        try:
            commits = GitCommitModel.get_recent(limit=limit, branch=branch)
            
            # Format for API response with file changes
            formatted_commits = []
            for commit in commits:
                # Get file changes for this commit
                file_changes = GitFileChangeModel.get_for_commit(commit['id'])
                
                formatted_commit = {
                    'id': str(commit['id']),
                    'hash': commit['commit_hash'],
                    'shortHash': commit['short_hash'],
                    'author': commit['author_name'],
                    'email': commit['author_email'],
                    'message': commit['message'],
                    'branch': commit['branch_name'],
                    'timestamp': commit['timestamp'],
                    'filesChanged': len(file_changes),
                    'changes': [
                        {
                            'path': fc['file_path'],
                            'type': fc['change_type'],
                            'linesAdded': fc['lines_added'],
                            'linesRemoved': fc['lines_removed'],
                            'diff': fc.get('diff_content', '')
                        }
                        for fc in file_changes
                    ]
                }
                formatted_commits.append(formatted_commit)
            
            logger.info(f"Retrieved {len(formatted_commits)} recent commits")
            return formatted_commits
            
        except Exception as e:
            logger.error(f"Failed to get recent commits: {e}")
            return []
    
    @staticmethod
    def get_working_changes(status: str = None) -> List[Dict[str, Any]]:
        """Get current working directory changes."""
        try:
            changes = GitWorkingChangeModel.get_current(status=status)
            
            # Format for API response
            formatted_changes = []
            for change in changes:
                formatted_change = {
                    'id': str(change['id']),
                    'filePath': change['file_path'],
                    'changeType': change['change_type'],
                    'status': change['status'],  # staged, unstaged, untracked
                    'timestamp': change['timestamp'],
                    'branch': change['branch_name'],
                    'diff': change.get('diff_content', '')
                }
                formatted_changes.append(formatted_change)
            
            logger.info(f"Retrieved {len(formatted_changes)} working changes")
            return formatted_changes
            
        except Exception as e:
            logger.error(f"Failed to get working changes: {e}")
            return []
    
    @staticmethod
    def get_commit_details(commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific commit."""
        try:
            commit = GitCommitModel.get_by_hash(commit_hash)
            if not commit:
                return None
            
            # Get file changes
            file_changes = GitFileChangeModel.get_for_commit(commit['id'])
            
            return {
                'id': commit['id'],
                'hash': commit['commit_hash'],
                'shortHash': commit['short_hash'],
                'author': commit['author_name'],
                'email': commit['author_email'],
                'message': commit['message'],
                'branch': commit['branch_name'],
                'timestamp': commit['timestamp'],
                'filesChanged': len(file_changes),
                'changes': [
                    {
                        'path': fc['file_path'],
                        'type': fc['change_type'],
                        'diff': fc['diff_content'],
                        'linesAdded': fc['lines_added'],
                        'linesRemoved': fc['lines_removed'],
                        'oldPath': fc['old_path']
                    }
                    for fc in file_changes
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get commit details for {commit_hash}: {e}")
            return None
    
    @staticmethod
    def get_file_history(file_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get git history for a specific file."""
        try:
            history = GitFileChangeModel.get_file_history(file_path, limit)
            
            formatted_history = []
            for entry in history:
                formatted_entry = {
                    'commitHash': entry.get('commit_hash'),
                    'shortHash': entry.get('short_hash'),
                    'author': entry.get('author_name'),
                    'message': entry.get('message'),
                    'timestamp': entry.get('timestamp'),
                    'branch': entry.get('branch_name'),
                    'changeType': entry.get('change_type'),
                    'diff': entry.get('diff_content', ''),
                    'linesAdded': entry.get('lines_added', 0),
                    'linesRemoved': entry.get('lines_removed', 0)
                }
                formatted_history.append(formatted_entry)
            
            return formatted_history
            
        except Exception as e:
            logger.error(f"Failed to get file history for {file_path}: {e}")
            return []
    
    @staticmethod
    def get_repository_status() -> Dict[str, Any]:
        """Get current git repository status."""
        try:
            # Get latest repository state
            repo_state = GitRepositoryStateModel.get_latest()
            
            if not repo_state:
                return {'error': 'No repository state available'}
            
            return {
                'branch': repo_state['current_branch'],
                'headCommit': repo_state['head_commit'],
                'isDirty': repo_state['is_dirty'],
                'stagedFiles': repo_state['staged_files_count'],
                'unstagedFiles': repo_state['unstaged_files_count'],
                'untrackedFiles': repo_state['untracked_files_count'],
                'lastUpdated': repo_state['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Failed to get repository status: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def search_commits(query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search commits by message or author using FTS."""
        try:
            search_query = """
                SELECT gc.*, rank
                FROM commit_search cs
                JOIN git_commits gc ON cs.rowid = gc.id
                WHERE commit_search MATCH ?
                ORDER BY rank, gc.timestamp DESC
                LIMIT ?
            """
            
            rows = db.execute_query(search_query, (query, limit))
            
            commits = []
            for row in rows:
                commit_dict = dict(row)
                # Get file changes count
                file_changes = GitFileChangeModel.get_for_commit(commit_dict['id'])
                commit_dict['filesChanged'] = len(file_changes)
                commits.append(commit_dict)
            
            return commits
            
        except Exception as e:
            logger.error(f"Commit search failed: {e}")
            return []
    
    @staticmethod
    def sync_git_commits_to_database(git_client) -> Dict[str, Any]:
        """
        Sync recent git commits from the repository to the database.
        This ensures the database is up to date with actual git commits.
        """
        try:
            # Get recent commits from git (last 10 should be sufficient for sync)
            recent_commits = git_client.get_recent_commits(max_count=10)
            
            synced_count = 0
            error_count = 0
            
            for commit_data in recent_commits:
                try:
                    # Insert commit into database (will skip if already exists due to unique constraint)
                    commit_id = GitCommitModel.insert(
                        commit_hash=commit_data['commit_hash'],
                        author_name=commit_data['author_name'],
                        author_email=commit_data['author_email'],
                        message=commit_data['message'],
                        timestamp=commit_data['timestamp'],
                        branch_name=GitQueries._get_current_branch_name(git_client)
                    )
                    
                    if commit_id:
                        # Sync file changes for this commit
                        files_synced = GitQueries._sync_commit_file_changes(
                            git_client, commit_id, commit_data
                        )
                        synced_count += 1
                        logger.debug(f"Synced commit {commit_data['short_hash']} with {files_synced} file changes")
                    
                except Exception as e:
                    logger.warning(f"Failed to sync commit {commit_data.get('short_hash', 'unknown')}: {e}")
                    error_count += 1
                    continue
            
            logger.info(f"Git sync completed: {synced_count} commits synced, {error_count} errors")
            return {
                'synced_commits': synced_count,
                'errors': error_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to sync git commits to database: {e}")
            return {
                'synced_commits': 0,
                'errors': 1,
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _get_current_branch_name(git_client) -> Optional[str]:
        """Get current branch name from git client."""
        try:
            return git_client.get_current_branch()
        except Exception:
            return None
    
    @staticmethod
    def _sync_commit_file_changes(git_client, commit_id: int, commit_data: Dict[str, Any]) -> int:
        """Sync file changes for a specific commit."""
        try:
            files_synced = 0
            
            # Get file changes from the git commit data
            files_changed = commit_data.get('files_changed', [])
            
            for file_change in files_changed:
                try:
                    # Get diff content for this file from git
                    file_path = file_change['path']
                    change_type = file_change['change_type']
                    
                    # Try to get diff content from git
                    diff_content = None
                    try:
                        # For new commits, we may not be able to get diff easily
                        # This is optional - the UI can fetch diffs on demand
                        diff_content = git_client.get_diff(file_path, 'HEAD') if file_path else None
                    except Exception:
                        # Diff retrieval is optional
                        pass
                    
                    # Insert file change
                    change_id = GitFileChangeModel.insert(
                        commit_id=commit_id,
                        file_path=file_path,
                        change_type=change_type,
                        diff_content=diff_content,
                        lines_added=0,  # Could be calculated from diff if needed
                        lines_removed=0,  # Could be calculated from diff if needed
                        old_path=None  # For renames - not implemented yet
                    )
                    
                    if change_id:
                        files_synced += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to sync file change {file_change.get('path')}: {e}")
                    continue
            
            return files_synced
            
        except Exception as e:
            logger.error(f"Failed to sync file changes for commit {commit_id}: {e}")
            return 0
    
    @staticmethod
    def clear_all_git_data() -> Dict[str, Any]:
        """Clear all git-related data from database."""
        try:
            from .models import db
            
            # Clear in order due to foreign key constraints
            db.execute_update("DELETE FROM git_file_changes")
            db.execute_update("DELETE FROM git_working_changes") 
            db.execute_update("DELETE FROM git_commits")
            db.execute_update("DELETE FROM git_repository_state")
            
            logger.info("Cleared all git data from database")
            return {
                'message': 'All git data cleared successfully',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to clear git data: {e}")
            return {
                'error': f'Failed to clear git data: {str(e)}',
                'success': False
            }

class EventQueries:
    """Event querying with git context."""
    
    @staticmethod
    def get_recent_events(limit: int = 50, event_type: str = None, 
                         processed: bool = None) -> List[Dict[str, Any]]:
        """Get recent events with git context."""
        try:
            events = EventModel.get_recent(limit=limit, event_type=event_type, 
                                          processed=processed)
            
            # Format for API response
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': f"event_{event['id']}",
                    'type': event['type'],
                    'path': event['path'],
                    'timestamp': event['timestamp'],
                    'size': event['size'],
                    'gitStatus': event.get('git_status'),
                    'processed': event.get('processed', False)
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Retrieved {len(formatted_events)} recent events")
            return formatted_events
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []
    
    @staticmethod
    def add_event(event_type: str, path: str, size: int = 0, 
                  git_status: str = None) -> bool:
        """Add new event with git context."""
        try:
            EventModel.insert(event_type, path, size, git_status)
            logger.debug(f"Added event: {event_type} {path} (git: {git_status})")
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
        """Clear all events."""
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
    """Enhanced semantic search with git context."""
    
    @staticmethod
    def search_semantic(query: str, limit: int = 20, commit_hash: str = None,
                       author: str = None, branch: str = None) -> Dict[str, Any]:
        """Enhanced semantic search with git filtering."""
        try:
            # Perform search with git context
            results = SemanticModel.search(
                query=query, 
                limit=limit, 
                commit_hash=commit_hash,
                author=author, 
                branch=branch
            )
            
            # Format results
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
                    'filePath': result['file_path'],
                    'commitHash': result.get('commit_hash'),
                    'author': result.get('author_name'),
                    'branch': result.get('branch_name'),
                    'relevanceScore': result.get('rank', 0)
                }
                formatted_results.append(formatted_result)
            
            return {
                'results': formatted_results,
                'total': len(formatted_results),
                'query': query,
                'filters': {
                    'commit': commit_hash,
                    'author': author,
                    'branch': branch
                },
                'gitContext': True
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
        """Get all topics."""
        try:
            topics = SemanticModel.get_all_topics()
            return {
                'topics': topics,
                'total': len(topics)
            }
        except Exception as e:
            logger.error(f"Failed to get topics: {e}")
            return {'topics': [], 'total': 0, 'error': str(e)}
    
    @staticmethod
    def get_all_keywords() -> Dict[str, Any]:
        """Get all keywords with counts."""
        try:
            keywords = SemanticModel.get_all_keywords()
            return {
                'keywords': keywords,
                'total': len(keywords)
            }
        except Exception as e:
            logger.error(f"Failed to get keywords: {e}")
            return {'keywords': [], 'total': 0, 'error': str(e)}

class ConfigQueries:
    """Configuration management."""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get all configuration."""
        try:
            config = ConfigModel.get_all()
            
            # Ensure default values for API compatibility
            default_config = {
                'checkInterval': 20,
                'openaiApiKey': '',
                'aiModel': 'gpt-4.1-mini',
                'watchPaths': ['notes'],
                'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
                'periodicCheckEnabled': True,
                'gitIntegrationEnabled': True,
                'maxCommitHistory': 1000
            }
            
            # Merge with database config
            default_config.update(config)
            
            return default_config
            
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return {}
    
    @staticmethod
    def update_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration."""
        try:
            valid_fields = [
                'checkInterval', 'openaiApiKey', 'aiModel', 
                'ignorePatterns', 'periodicCheckEnabled',
                'gitIntegrationEnabled', 'maxCommitHistory'
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
            return {'error': error_msg}

class AnalyticsQueries:
    """Git-focused analytics and insights."""
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        try:
            stats = {}
            
            # Performance stats
            perf_stats = PerformanceModel.get_stats()
            stats.update(perf_stats)
            
            # Git-specific stats
            recent_commits = GitQueries.get_recent_commits(limit=5)
            working_changes = GitQueries.get_working_changes()
            repo_status = GitQueries.get_repository_status()
            
            stats.update({
                'recent_commits_count': len(recent_commits),
                'working_changes_count': len(working_changes),
                'repository_status': repo_status,
                'database_health': 'healthy',
                'last_updated': datetime.now().isoformat()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {}
    
    @staticmethod
    def get_commit_activity(days: int = 30) -> List[Dict[str, Any]]:
        """Get commit activity over time."""
        try:
            query = """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as commit_count,
                    COUNT(DISTINCT author_name) as authors,
                    COUNT(DISTINCT branch_name) as branches
                FROM git_commits 
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            
            rows = db.execute_query(query, (days,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get commit activity: {e}")
            return []
    
    @staticmethod
    def get_author_stats() -> List[Dict[str, Any]]:
        """Get author contribution statistics."""
        try:
            authors = GitCommitModel.get_authors()
            return authors
        except Exception as e:
            logger.error(f"Failed to get author stats: {e}")
            return []
    
    @staticmethod
    def get_file_change_frequency(limit: int = 20) -> List[Dict[str, Any]]:
        """Get most frequently changed files."""
        try:
            query = """
                SELECT 
                    file_path,
                    COUNT(*) as change_count,
                    COUNT(DISTINCT fc.commit_id) as commits,
                    MAX(gc.timestamp) as last_changed
                FROM git_file_changes fc
                JOIN git_commits gc ON fc.commit_id = gc.id
                GROUP BY file_path
                ORDER BY change_count DESC
                LIMIT ?
            """
            
            rows = db.execute_query(query, (limit,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get file change frequency: {e}")
            return []

class RealTimeQueries:
    """Real-time data queries for live updates."""
    
    @staticmethod
    def get_live_activity(since: datetime = None) -> Dict[str, Any]:
        """Get git activity since specified time for real-time updates."""
        try:
            if since is None:
                since = datetime.now() - timedelta(minutes=5)
            
            # Recent commits
            commit_query = """
                SELECT 'commit' as type, commit_hash as identifier, author_name as actor,
                       message as description, timestamp, branch_name as context
                FROM git_commits
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """
            
            # Recent working changes
            working_query = """
                SELECT 'working_change' as type, file_path as identifier, 'system' as actor,
                       change_type || ' (' || status || ')' as description, 
                       timestamp, branch_name as context
                FROM git_working_changes
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """
            
            commit_rows = db.execute_query(commit_query, (since,))
            working_rows = db.execute_query(working_query, (since,))
            
            # Combine and sort
            all_activity = []
            all_activity.extend([dict(row) for row in commit_rows])
            all_activity.extend([dict(row) for row in working_rows])
            
            # Sort by timestamp
            all_activity.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'activity': all_activity[:20],  # Limit to 20 most recent
                'timestamp': datetime.now().isoformat(),
                'count': len(all_activity),
                'gitNative': True
            }
            
        except Exception as e:
            logger.error(f"Failed to get live activity: {e}")
            return {
                'activity': [],
                'timestamp': datetime.now().isoformat(),
                'count': 0,
                'error': str(e)
            }

# Legacy compatibility aliases (for gradual migration)
DiffQueries = GitQueries  # Map old DiffQueries to GitQueries

logger.info("Git-native query engine initialized successfully")