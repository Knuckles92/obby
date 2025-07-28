"""
Git client for native version control integration.
Replaces custom diff system with full git capabilities.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import git
from git.exc import InvalidGitRepositoryError, GitCommandError

logger = logging.getLogger(__name__)

class GitClient:
    """Git operations wrapper for Obby's change tracking system."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize git client with repository path."""
        self.repo_path = Path(repo_path).resolve()
        self._repo = None
        self._validate_repository()
    
    def _validate_repository(self):
        """Validate that we're in a git repository."""
        try:
            self._repo = git.Repo(self.repo_path)
            if self._repo.bare:
                raise InvalidGitRepositoryError("Cannot work with bare repositories")
            logger.info(f"Git repository initialized: {self.repo_path}")
        except InvalidGitRepositoryError as e:
            logger.error(f"Not a valid git repository: {self.repo_path}")
            raise ValueError(f"Directory is not a git repository: {self.repo_path}") from e
    
    @property
    def repo(self) -> git.Repo:
        """Get the git repository object."""
        if self._repo is None:
            self._validate_repository()
        return self._repo
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive git status information."""
        try:
            # Get status using git status --porcelain for reliable parsing
            status_output = self.repo.git.status('--porcelain=v1', '--untracked-files=all')
            
            # Parse status into categories
            staged_files = []
            unstaged_files = []
            untracked_files = []
            
            for line in status_output.strip().split('\n'):
                if not line:
                    continue
                    
                status_code = line[:2]
                file_path = line[3:]  # Skip status code and space
                
                # First character is staged status, second is working tree status
                staged_status = status_code[0]
                working_status = status_code[1]
                
                if staged_status != ' ' and staged_status != '?':
                    staged_files.append({
                        'path': file_path,
                        'status': self._parse_status_code(staged_status),
                        'status_code': staged_status
                    })
                
                if working_status != ' ':
                    if working_status == '?':
                        untracked_files.append({
                            'path': file_path,
                            'status': 'untracked',
                            'status_code': working_status
                        })
                    else:
                        unstaged_files.append({
                            'path': file_path,
                            'status': self._parse_status_code(working_status),
                            'status_code': working_status
                        })
            
            # Get current branch info
            try:
                current_branch = self.repo.active_branch.name
                branch_commit = self.repo.active_branch.commit.hexsha
            except TypeError:
                # Detached HEAD state
                current_branch = None
                branch_commit = self.repo.head.commit.hexsha
            
            return {
                'branch': current_branch,
                'commit': branch_commit,
                'staged_files': staged_files,
                'unstaged_files': unstaged_files,
                'untracked_files': untracked_files,
                'total_changes': len(staged_files) + len(unstaged_files) + len(untracked_files),
                'clean': len(staged_files) + len(unstaged_files) + len(untracked_files) == 0
            }
            
        except GitCommandError as e:
            logger.error(f"Failed to get git status: {e}")
            return {
                'error': str(e),
                'branch': None,
                'commit': None,
                'staged_files': [],
                'unstaged_files': [],
                'untracked_files': [],
                'total_changes': 0,
                'clean': True
            }
    
    def _parse_status_code(self, code: str) -> str:
        """Parse git status code to human readable string."""
        status_map = {
            'A': 'added',
            'M': 'modified', 
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied',
            'U': 'unmerged',
            '?': 'untracked',
            '!': 'ignored'
        }
        return status_map.get(code, 'unknown')
    
    def get_diff(self, file_path: str, diff_type: str = 'working') -> Optional[str]:
        """
        Get diff for a specific file.
        
        Args:
            file_path: Path to the file relative to repo root
            diff_type: 'working' (unstaged), 'staged', or 'HEAD' (last commit)
        """
        try:
            file_path = str(Path(file_path).as_posix())  # Normalize path for git
            
            if diff_type == 'working':
                # Compare working directory to index (unstaged changes)
                diff_output = self.repo.git.diff('HEAD', '--', file_path)
            elif diff_type == 'staged':
                # Compare index to HEAD (staged changes)
                diff_output = self.repo.git.diff('--cached', '--', file_path)
            elif diff_type == 'HEAD':
                # Show last commit changes for this file
                diff_output = self.repo.git.show(f'HEAD:{file_path}')
            else:
                raise ValueError(f"Invalid diff_type: {diff_type}")
            
            return diff_output if diff_output else None
            
        except GitCommandError as e:
            logger.warning(f"Failed to get diff for {file_path} ({diff_type}): {e}")
            return None
    
    def get_file_history(self, file_path: str, max_count: int = 50) -> List[Dict[str, Any]]:
        """Get commit history for a specific file."""
        try:
            file_path = str(Path(file_path).as_posix())
            
            # Use git log with --follow to track file across renames
            commits = list(self.repo.iter_commits(
                paths=file_path,
                max_count=max_count,
                follow=True
            ))
            
            history = []
            for commit in commits:
                history.append({
                    'commit_hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'author_name': commit.author.name,
                    'author_email': commit.author.email,
                    'message': commit.message.strip(),
                    'timestamp': datetime.fromtimestamp(commit.committed_date),
                    'branch': None  # Would need additional lookup to determine branch
                })
            
            return history
            
        except GitCommandError as e:
            logger.error(f"Failed to get file history for {file_path}: {e}")
            return []
    
    def get_blame(self, file_path: str) -> List[Dict[str, Any]]:
        """Get blame information for a file (line-by-line authorship)."""
        try:
            file_path = str(Path(file_path).as_posix())
            blame_output = self.repo.git.blame('--line-porcelain', file_path)
            
            blame_info = []
            lines = blame_output.split('\n')
            i = 0
            
            while i < len(lines):
                if not lines[i]:
                    i += 1
                    continue
                
                # Parse blame output format
                commit_hash = lines[i].split()[0]
                line_number = int(lines[i].split()[2])
                
                # Find author and content
                author = None
                content = None
                
                j = i + 1
                while j < len(lines) and not lines[j].startswith('\t'):
                    if lines[j].startswith('author '):
                        author = lines[j][7:]  # Remove 'author ' prefix
                    j += 1
                
                if j < len(lines):
                    content = lines[j][1:]  # Remove tab prefix
                
                blame_info.append({
                    'line_number': line_number,
                    'commit_hash': commit_hash,
                    'short_hash': commit_hash[:8],
                    'author': author,
                    'content': content
                })
                
                i = j + 1
            
            return blame_info
            
        except GitCommandError as e:
            logger.error(f"Failed to get blame for {file_path}: {e}")
            return []
    
    def get_recent_commits(self, max_count: int = 20, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get recent commits in the repository."""
        try:
            kwargs = {'max_count': max_count}
            if since:
                kwargs['since'] = since
            
            commits = list(self.repo.iter_commits(**kwargs))
            
            commit_list = []
            for commit in commits:
                # Get files changed in this commit
                files_changed = []
                try:
                    # Compare with parent (or empty tree for initial commit)
                    if commit.parents:
                        diff = commit.parents[0].diff(commit)
                    else:
                        diff = commit.diff(git.NULL_TREE)
                    
                    for diff_item in diff:
                        change_type = 'modified'
                        if diff_item.new_file:
                            change_type = 'added'
                        elif diff_item.deleted_file:
                            change_type = 'deleted'
                        elif diff_item.renamed_file:
                            change_type = 'renamed'
                        
                        files_changed.append({
                            'path': diff_item.b_path or diff_item.a_path,
                            'change_type': change_type
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to get files for commit {commit.hexsha}: {e}")
                
                commit_list.append({
                    'commit_hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'author_name': commit.author.name,
                    'author_email': commit.author.email,
                    'message': commit.message.strip(),
                    'timestamp': datetime.fromtimestamp(commit.committed_date),
                    'files_changed': files_changed
                })
            
            return commit_list
            
        except GitCommandError as e:
            logger.error(f"Failed to get recent commits: {e}")
            return []
    
    def is_file_tracked(self, file_path: str) -> bool:
        """Check if a file is tracked by git."""
        try:
            file_path = str(Path(file_path).as_posix())
            self.repo.git.ls_files('--error-unmatch', file_path)
            return True
        except GitCommandError:
            return False
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD
            return None
    
    def get_repository_info(self) -> Dict[str, Any]:
        """Get general repository information."""
        try:
            return {
                'repo_path': str(self.repo_path),
                'current_branch': self.get_current_branch(),
                'head_commit': self.repo.head.commit.hexsha,
                'is_dirty': self.repo.is_dirty(),
                'untracked_files': len(self.repo.untracked_files),
                'remote_url': self._get_remote_url()
            }
        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return {'error': str(e)}
    
    def _get_remote_url(self) -> Optional[str]:
        """Get the remote URL if available."""
        try:
            if 'origin' in self.repo.remotes:
                return self.repo.remotes.origin.url
            elif self.repo.remotes:
                return self.repo.remotes[0].url
            return None
        except Exception:
            return None

# Global git client instance
_git_client = None

def get_git_client(repo_path: str = ".") -> GitClient:
    """Get or create global git client instance."""
    global _git_client
    if _git_client is None:
        _git_client = GitClient(repo_path)
    return _git_client

logger.info("Git client module initialized successfully")