"""
Git Change Tracker - Replaces custom diff system
===============================================

Git-native change tracking that leverages full git capabilities
for comprehensive version control and change monitoring.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib

from .git_client import get_git_client, GitClient
from database.models import (
    GitCommitModel, GitFileChangeModel, GitWorkingChangeModel, 
    GitRepositoryStateModel, EventModel, SemanticModel, FileStateModel
)

logger = logging.getLogger(__name__)

class GitChangeTracker:
    """Git-native change tracking system replacing DiffTracker."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize git change tracker."""
        self.repo_path = Path(repo_path).resolve()
        self.git_client = get_git_client(str(repo_path))
        self._last_known_head = None
        self._last_known_status = None
        
        logger.info(f"Git change tracker initialized for: {self.repo_path}")
    
    def check_for_changes(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check for any git changes (commits, working changes, etc.).
        Returns (has_changes, change_summary).
        """
        try:
            # Get current git status
            current_status = self.git_client.get_status()
            
            if 'error' in current_status:
                logger.error(f"Git status error: {current_status['error']}")
                return False, None
            
            # Check for new commits
            commit_changes = self._check_commit_changes(current_status)
            
            # Check for working directory changes
            working_changes = self._check_working_changes(current_status)
            
            # Update repository state
            self._update_repository_state(current_status)
            
            # Determine if there are any changes
            has_changes = bool(commit_changes or working_changes)
            
            if has_changes:
                change_summary = {
                    'new_commits': len(commit_changes) if commit_changes else 0,
                    'working_changes': len(working_changes) if working_changes else 0,
                    'branch': current_status.get('branch'),
                    'total_changes': current_status.get('total_changes', 0),
                    'timestamp': datetime.now(),
                    'details': {
                        'commits': commit_changes,
                        'working': working_changes
                    }
                }
                
                logger.info(f"Git changes detected: {change_summary}")
                return True, change_summary
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking git changes: {e}")
            return False, None
    
    def _check_commit_changes(self, current_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for new commits since last check."""
        try:
            current_head = current_status.get('commit')
            
            if not current_head:
                return []
            
            # If this is the first check, just record the current head
            if self._last_known_head is None:
                self._last_known_head = current_head
                # Process recent commits for initial setup
                return self._process_recent_commits(limit=5)
            
            # If head hasn't changed, no new commits
            if self._last_known_head == current_head:
                return []
            
            # Get new commits between last known head and current head
            new_commits = self._get_commits_between(self._last_known_head, current_head)
            
            # Process and store new commits
            processed_commits = []
            for commit_info in new_commits:
                commit_id = self._store_commit(commit_info)
                if commit_id:
                    processed_commits.append({
                        'commit_id': commit_id,
                        'hash': commit_info['commit_hash'],
                        'message': commit_info['message'],
                        'author': commit_info['author_name'],
                        'files_changed': len(commit_info.get('files_changed', []))
                    })
            
            # Update last known head
            self._last_known_head = current_head
            
            return processed_commits
            
        except Exception as e:
            logger.error(f"Error checking commit changes: {e}")
            return []
    
    def _check_working_changes(self, current_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for working directory changes."""
        try:
            # Clear old working changes
            GitWorkingChangeModel.clear_all()
            
            processed_changes = []
            current_branch = current_status.get('branch')
            
            # Process staged files
            for staged_file in current_status.get('staged_files', []):
                diff_content = self.git_client.get_diff(staged_file['path'], 'staged')
                change_id = GitWorkingChangeModel.insert(
                    file_path=staged_file['path'],
                    change_type=staged_file['status'],
                    status='staged',
                    diff_content=diff_content,
                    branch_name=current_branch
                )
                
                if change_id:
                    processed_changes.append({
                        'id': change_id,
                        'path': staged_file['path'],
                        'type': staged_file['status'],
                        'status': 'staged'
                    })
            
            # Process unstaged files
            for unstaged_file in current_status.get('unstaged_files', []):
                diff_content = self.git_client.get_diff(unstaged_file['path'], 'working')
                change_id = GitWorkingChangeModel.insert(
                    file_path=unstaged_file['path'],
                    change_type=unstaged_file['status'],
                    status='unstaged',
                    diff_content=diff_content,
                    branch_name=current_branch
                )
                
                if change_id:
                    processed_changes.append({
                        'id': change_id,
                        'path': unstaged_file['path'],
                        'type': unstaged_file['status'],
                        'status': 'unstaged'
                    })
            
            # Process untracked files
            for untracked_file in current_status.get('untracked_files', []):
                change_id = GitWorkingChangeModel.insert(
                    file_path=untracked_file['path'],
                    change_type='untracked',
                    status='untracked',
                    branch_name=current_branch
                )
                
                if change_id:
                    processed_changes.append({
                        'id': change_id,
                        'path': untracked_file['path'],
                        'type': 'untracked',
                        'status': 'untracked'
                    })
            
            return processed_changes
            
        except Exception as e:
            logger.error(f"Error checking working changes: {e}")
            return []
    
    def _process_recent_commits(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Process recent commits for initial setup."""
        try:
            recent_commits = self.git_client.get_recent_commits(max_count=limit)
            processed_commits = []
            
            for commit_info in recent_commits:
                commit_id = self._store_commit(commit_info)
                if commit_id:
                    processed_commits.append({
                        'commit_id': commit_id,
                        'hash': commit_info['commit_hash'],
                        'message': commit_info['message'],
                        'author': commit_info['author_name'],
                        'files_changed': len(commit_info.get('files_changed', []))
                    })
            
            return processed_commits
            
        except Exception as e:
            logger.error(f"Error processing recent commits: {e}")
            return []
    
    def _get_commits_between(self, old_head: str, new_head: str) -> List[Dict[str, Any]]:
        """Get commits between two commit hashes."""
        try:
            # For now, just get recent commits up to the new head
            # In a more sophisticated implementation, we'd use git rev-list
            recent_commits = self.git_client.get_recent_commits(max_count=10)
            
            # Filter to only commits newer than old_head
            new_commits = []
            for commit in recent_commits:
                if commit['commit_hash'] == old_head:
                    break  # Stop when we reach the old head
                new_commits.append(commit)
            
            return new_commits
            
        except Exception as e:
            logger.error(f"Error getting commits between {old_head} and {new_head}: {e}")
            return []
    
    def _store_commit(self, commit_info: Dict[str, Any]) -> Optional[int]:
        """Store commit information in database."""
        try:
            # Insert commit
            commit_id = GitCommitModel.insert(
                commit_hash=commit_info['commit_hash'],
                author_name=commit_info['author_name'],
                author_email=commit_info['author_email'],
                message=commit_info['message'],
                timestamp=commit_info['timestamp'],
                branch_name=commit_info.get('branch')
            )
            
            if not commit_id:
                return None
            
            # Store file changes for this commit
            for file_change in commit_info.get('files_changed', []):
                # Get diff content for this file
                diff_content = self.git_client.get_diff(
                    file_change['path'], 
                    'HEAD'  # Show the commit's changes
                )
                
                GitFileChangeModel.insert(
                    commit_id=commit_id,
                    file_path=file_change['path'],
                    change_type=file_change['change_type'],
                    diff_content=diff_content
                )
            
            return commit_id
            
        except Exception as e:
            logger.error(f"Error storing commit {commit_info.get('commit_hash', 'unknown')}: {e}")
            return None
    
    def _update_repository_state(self, status: Dict[str, Any]) -> None:
        """Update repository state in database."""
        try:
            GitRepositoryStateModel.insert(
                current_branch=status.get('branch'),
                head_commit=status.get('commit'),
                is_dirty=not status.get('clean', True),
                staged_count=len(status.get('staged_files', [])),
                unstaged_count=len(status.get('unstaged_files', [])),
                untracked_count=len(status.get('untracked_files', []))
            )
        except Exception as e:
            logger.error(f"Error updating repository state: {e}")
    
    def get_recent_changes(self, limit: int = 20) -> Dict[str, Any]:
        """Get recent changes from database."""
        try:
            # Get recent commits
            recent_commits = GitCommitModel.get_recent(limit=limit//2)
            
            # Get current working changes
            working_changes = GitWorkingChangeModel.get_current()
            
            # Get repository state
            repo_state = GitRepositoryStateModel.get_latest()
            
            return {
                'commits': recent_commits,
                'working_changes': working_changes[:limit//2],
                'repository_state': repo_state,
                'total_commits': len(recent_commits),
                'total_working_changes': len(working_changes)
            }
            
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return {
                'commits': [],
                'working_changes': [],
                'repository_state': None,
                'total_commits': 0,
                'total_working_changes': 0
            }
    
    def get_file_history(self, file_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get git history for a specific file."""
        try:
            # Get from git client
            git_history = self.git_client.get_file_history(file_path, max_count=limit)
            
            # Get from database (file changes)
            db_history = GitFileChangeModel.get_file_history(file_path, limit)
            
            # Combine and deduplicate by commit hash
            combined_history = {}
            
            # Add git history
            for entry in git_history:
                combined_history[entry['commit_hash']] = entry
            
            # Add database history
            for entry in db_history:
                hash_key = entry.get('commit_hash')
                if hash_key and hash_key not in combined_history:
                    combined_history[hash_key] = entry
            
            # Sort by timestamp
            sorted_history = sorted(
                combined_history.values(),
                key=lambda x: x.get('timestamp', datetime.min),
                reverse=True
            )
            
            return sorted_history[:limit]
            
        except Exception as e:
            logger.error(f"Error getting file history for {file_path}: {e}")
            return []
    
    def get_blame_info(self, file_path: str) -> List[Dict[str, Any]]:
        """Get git blame information for a file."""
        try:
            return self.git_client.get_blame(file_path)
        except Exception as e:
            logger.error(f"Error getting blame info for {file_path}: {e}")
            return []
    
    def is_file_tracked(self, file_path: str) -> bool:
        """Check if file is tracked by git."""
        try:
            return self.git_client.is_file_tracked(file_path)
        except Exception as e:
            logger.error(f"Error checking if file is tracked {file_path}: {e}")
            return False
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current git status."""
        try:
            return self.git_client.get_status()
        except Exception as e:
            logger.error(f"Error getting current status: {e}")
            return {'error': str(e)}
    
    def update_file_state(self, file_path: str) -> None:
        """Update file state tracking."""
        try:
            # Check if file is tracked by git
            is_tracked = self.is_file_tracked(file_path)
            
            # Get git hash if tracked
            git_hash = None
            if is_tracked:
                # You could get the git hash here if needed
                # For now, we'll use a simple content hash
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        git_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                except Exception:
                    git_hash = None
            
            # Get line count
            line_count = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                pass
            
            # Update state
            FileStateModel.update_state(
                file_path=str(file_path),
                git_hash=git_hash,
                line_count=line_count,
                is_tracked=is_tracked
            )
            
        except Exception as e:
            logger.error(f"Error updating file state for {file_path}: {e}")

logger.info("Git change tracker initialized successfully")