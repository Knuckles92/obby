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
        """Validate or create git repository for Obsidian vault."""
        try:
            # Try to open existing repository
            self._repo = git.Repo(self.repo_path)
            if self._repo.bare:
                raise InvalidGitRepositoryError("Cannot work with bare repositories")
            logger.info(f"Found existing git repository: {self.repo_path}")
        except InvalidGitRepositoryError:
            # No git repository exists - create one for the Obsidian vault
            logger.info(f"No git repository found. Initializing new repository at: {self.repo_path}")
            self._initialize_vault_repository()
    
    def _initialize_vault_repository(self):
        """Initialize a new git repository for an Obsidian vault."""
        try:
            # Initialize the repository
            self._repo = git.Repo.init(self.repo_path)
            logger.info(f"Initialized new git repository at: {self.repo_path}")
            
            # Set up Obsidian-specific .gitignore
            self._create_obsidian_gitignore()
            
            # Configure git user if not set (use generic defaults)
            self._configure_git_user()
            
            # Make initial commit of existing vault content
            self._make_initial_commit()
            
            logger.info("Git repository setup complete for Obsidian vault")
            
        except Exception as e:
            logger.error(f"Failed to initialize git repository: {e}")
            raise ValueError(f"Could not set up git repository: {e}") from e
    
    def _create_obsidian_gitignore(self):
        """Create .gitignore file optimized for Obsidian vaults."""
        gitignore_content = """# Obsidian configuration and cache
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/hotkeys.json
.obsidian/appearance.json
.obsidian/core-plugins.json
.obsidian/community-plugins.json
.obsidian/plugins/*/data.json
.obsidian/graph.json
.obsidian/canvas.json

# Obsidian cache
.obsidian/cache/

# Trash
.trash/

# System files
.DS_Store
Thumbs.db
desktop.ini

# Temporary files
*.tmp
*.temp
*~
.#*

# Obby-specific files (our own app data)
obby.db
obby.log
*.obby

# Common editor temporary files
.vscode/
*.swp
*.swo
"""
        
        gitignore_path = self.repo_path / ".gitignore"
        try:
            gitignore_path.write_text(gitignore_content, encoding='utf-8')
            logger.info("Created Obsidian-optimized .gitignore")
        except Exception as e:
            logger.warning(f"Could not create .gitignore: {e}")
    
    def _configure_git_user(self):
        """Configure git user for commits if not already set."""
        try:
            # Check if user is already configured
            try:
                self._repo.config_reader().get_value("user", "name")
                self._repo.config_reader().get_value("user", "email")
                logger.info("Git user already configured")
                return
            except Exception:
                pass
            
            # Set default user for this repository
            with self._repo.config_writer() as git_config:
                git_config.set_value("user", "name", "Obby Note Tracker")
                git_config.set_value("user", "email", "obby@local.vault")
            
            logger.info("Configured default git user for Obby")
            
        except Exception as e:
            logger.warning(f"Could not configure git user: {e}")
    
    def _make_initial_commit(self):
        """Make initial commit of existing vault content."""
        try:
            # Add .gitignore first
            if (self.repo_path / ".gitignore").exists():
                self._repo.index.add([".gitignore"])
            
            # Add existing files (respecting .gitignore)
            # Get all files except those ignored
            all_files = []
            for file_path in self.repo_path.rglob('*'):
                if file_path.is_file() and not self._should_ignore_file(file_path):
                    relative_path = file_path.relative_to(self.repo_path)
                    all_files.append(str(relative_path))
            
            if all_files:
                self._repo.index.add(all_files)
                logger.info(f"Staged {len(all_files)} files for initial commit")
            
            # Create initial commit
            if self._repo.index.entries:
                commit = self._repo.index.commit(
                    "Initial commit: Import existing Obsidian vault\n\n"
                    "🗄️ This commit imports the existing vault contents into git version control.\n"
                    "📝 All existing notes and files are now tracked.\n"
                    "🤖 Generated by Obby - Obsidian change tracker"
                )
                logger.info(f"Created initial commit: {commit.hexsha[:8]}")
            else:
                logger.info("No files to commit - empty vault")
                
        except Exception as e:
            logger.error(f"Failed to make initial commit: {e}")
            # Don't raise - repository is still usable
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored based on .gitignore patterns."""
        try:
            # Convert to relative path from repo root
            relative_path = file_path.relative_to(self.repo_path)
            
            # Basic ignore patterns (before .gitignore is processed)
            ignore_patterns = [
                '.git', '.obsidian/workspace*.json', '.obsidian/hotkeys.json',
                '.obsidian/cache', '.trash', '.DS_Store', 'Thumbs.db',
                'obby.db', 'obby.log', '*.tmp', '*.temp'
            ]
            
            path_str = str(relative_path)
            for pattern in ignore_patterns:
                if pattern in path_str or path_str.endswith(pattern.replace('*', '')):
                    return True
            
            # Check if it's in an ignored directory
            for part in relative_path.parts:
                if part.startswith('.') and part not in ['.gitignore']:
                    return True
            
            return False
            
        except Exception:
            return False
    
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
    
    # Auto-commit methods for Obsidian vault management
    
    def auto_commit_file(self, file_path: str, commit_message: str = None, ai_client=None) -> Optional[str]:
        """
        Automatically stage and commit a single file.
        
        Args:
            file_path: Path to file to commit (relative to repo root)
            commit_message: Custom commit message, or auto-generated if None
            
        Returns:
            Commit hash if successful, None if failed
        """
        try:
            file_path = str(Path(file_path).as_posix())  # Normalize for git
            
            # Check if file exists and has changes
            if not self._file_has_changes(file_path):
                logger.debug(f"No changes to commit for {file_path}")
                return None
            
            # Stage the file
            self.repo.index.add([file_path])
            logger.debug(f"Staged file: {file_path}")
            
            # Generate commit message if not provided
            if not commit_message:
                commit_message = self._generate_commit_message(file_path, ai_client)
            
            # Create commit
            commit = self.repo.index.commit(commit_message)
            logger.info(f"Auto-committed {file_path}: {commit.hexsha[:8]}")
            
            return commit.hexsha
            
        except Exception as e:
            logger.error(f"Failed to auto-commit {file_path}: {e}")
            return None
    
    def auto_commit_multiple_files(self, file_paths: List[str], commit_message: str = None, ai_client=None) -> Optional[str]:
        """
        Automatically stage and commit multiple files in a single commit.
        
        Args:
            file_paths: List of file paths to commit
            commit_message: Custom commit message, or auto-generated if None
            
        Returns:
            Commit hash if successful, None if failed
        """
        try:
            # Normalize paths and filter for files with changes
            normalized_paths = []
            for path in file_paths:
                normalized_path = str(Path(path).as_posix())
                if self._file_has_changes(normalized_path):
                    normalized_paths.append(normalized_path)
            
            if not normalized_paths:
                logger.debug("No files with changes to commit")
                return None
            
            # Stage all files
            self.repo.index.add(normalized_paths)
            logger.debug(f"Staged {len(normalized_paths)} files")
            
            # Generate commit message if not provided
            if not commit_message:
                commit_message = self._generate_batch_commit_message(normalized_paths)
            
            # Create commit
            commit = self.repo.index.commit(commit_message)
            logger.info(f"Auto-committed {len(normalized_paths)} files: {commit.hexsha[:8]}")
            
            return commit.hexsha
            
        except Exception as e:
            logger.error(f"Failed to auto-commit multiple files: {e}")
            return None
    
    def _file_has_changes(self, file_path: str) -> bool:
        """Check if a file has uncommitted changes."""
        try:
            # Check if file is in working directory changes
            if file_path in [item.a_path for item in self.repo.index.diff(None)]:
                return True
            
            # Check if file is untracked
            if file_path in self.repo.untracked_files:
                return True
            
            # Check if file is staged
            if file_path in [item.a_path for item in self.repo.index.diff("HEAD")]:
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking changes for {file_path}: {e}")
            return False
    
    def _generate_commit_message(self, file_path: str, ai_client=None) -> str:
        """Generate an automatic commit message for a single file with optional AI assistance."""
        try:
            file_name = Path(file_path).name
            
            # Determine the type of change
            if file_path in self.repo.untracked_files:
                change_type = "feat"
                action = "create"
            elif self.is_file_tracked(file_path):
                change_type = "docs" if file_path.endswith('.md') else "update"
                action = "update"
            else:
                change_type = "feat"
                action = "add"
            
            # Try AI-assisted message generation for markdown files
            if ai_client and file_path.endswith('.md'):
                ai_message = self._generate_ai_commit_message(file_path, change_type, action, ai_client)
                if ai_message:
                    return ai_message
            
            # Get basic info about the file
            try:
                file_full_path = self.repo_path / file_path
                if file_full_path.exists():
                    # Try to get some context from the file
                    if file_path.endswith('.md'):
                        # For markdown files, try to get the first heading or content preview
                        with open(file_full_path, 'r', encoding='utf-8') as f:
                            first_lines = f.read(200).strip()
                            if first_lines.startswith('#'):
                                title = first_lines.split('\n')[0].strip('# ')
                                return f"{change_type}: {action} note '{title}'"
            except Exception:
                pass
            
            # Fallback to simple message
            return f"{change_type}: {action} {file_name}"
            
        except Exception as e:
            logger.warning(f"Error generating commit message for {file_path}: {e}")
            return f"docs: update {Path(file_path).name}"
    
    def _generate_ai_commit_message(self, file_path: str, change_type: str, action: str, ai_client) -> Optional[str]:
        """Generate AI-assisted commit message for a file."""
        try:
            file_full_path = self.repo_path / file_path
            if not file_full_path.exists():
                return None
            
            # Get file content
            try:
                with open(file_full_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)  # First 500 chars for analysis
            except Exception as e:
                logger.debug(f"Could not read file content for AI analysis: {e}")
                return None
            
            # Get diff content if it's a modification
            diff_content = ""
            if action == "update":
                try:
                    diff_content = self.get_diff(file_path, 'working') or ""
                except Exception:
                    pass
            
            # Create prompt for AI
            prompt = f"""Generate a concise git commit message for this change:

File: {file_path}
Action: {action}
Type: {change_type}

Content preview:
{content[:300]}

{f"Changes made:\n{diff_content[:200]}" if diff_content else ""}

Generate a commit message in the format: "{change_type}: brief description"
Keep it under 50 characters, focus on what changed, not how."""
            
            # Try to get AI response using the OpenAI client directly
            try:
                from openai import OpenAI
                
                # Use the AI client's OpenAI client instance
                if hasattr(ai_client, 'client') and ai_client.client:
                    response = ai_client.client.chat.completions.create(
                        model=ai_client.model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that generates concise git commit messages."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=50,
                        temperature=0.3
                    )
                    
                    if response.choices and response.choices[0].message:
                        message = response.choices[0].message.content.strip()
                        # Clean up the response
                        message = message.replace('\n', ' ').replace('"', '')
                        if len(message) > 72:  # Standard git message length
                            message = message[:69] + "..."
                        logger.debug(f"AI generated commit message: {message}")
                        return message
            except Exception as e:
                logger.debug(f"AI commit message generation failed: {e}")
                return None
            
        except Exception as e:
            logger.debug(f"Error in AI commit message generation: {e}")
            return None
    
    def _generate_batch_commit_message(self, file_paths: List[str]) -> str:
        """Generate an automatic commit message for multiple files."""
        try:
            file_count = len(file_paths)
            
            # Categorize files
            markdown_files = [p for p in file_paths if p.endswith('.md')]
            other_files = [p for p in file_paths if not p.endswith('.md')]
            
            # Generate message based on file types
            if file_count == 1:
                return self._generate_commit_message(file_paths[0])
            
            if markdown_files and not other_files:
                return f"docs: update {len(markdown_files)} notes"
            elif other_files and not markdown_files:
                return f"feat: update {len(other_files)} files"
            else:
                return f"update: modify {file_count} files ({len(markdown_files)} notes, {len(other_files)} other)"
            
        except Exception as e:
            logger.warning(f"Error generating batch commit message: {e}")
            return f"update: modify {len(file_paths)} files"
    
    def get_uncommitted_files(self) -> Dict[str, List[str]]:
        """Get lists of uncommitted files by category."""
        try:
            return {
                'modified': [item.a_path for item in self.repo.index.diff(None)],
                'staged': [item.a_path for item in self.repo.index.diff("HEAD")],
                'untracked': list(self.repo.untracked_files)
            }
        except Exception as e:
            logger.error(f"Failed to get uncommitted files: {e}")
            return {'modified': [], 'staged': [], 'untracked': []}

# Global git client instance
_git_client = None

def get_git_client(repo_path: str = ".") -> GitClient:
    """Get or create global git client instance."""
    global _git_client
    if _git_client is None:
        _git_client = GitClient(repo_path)
    return _git_client

logger.info("Git client module initialized successfully")