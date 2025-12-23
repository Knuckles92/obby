"""
File Service
Handles file read, write, and search operations with security validation
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class FileService:
    """Service layer for file operations with security and monitoring integration"""

    def __init__(self, root_folder: Path):
        """
        Initialize file service

        Args:
            root_folder: Root directory for the application (contains .obbywatch)
        """
        self.root_folder = Path(root_folder).resolve()

        # Import handlers for validation
        try:
            from utils.watch_handler import WatchHandler
            from utils.ignore_handler import IgnoreHandler
            from config.settings import get_configured_notes_folder

            self.watch_handler = WatchHandler(self.root_folder)
            notes_folder = get_configured_notes_folder()
            self.ignore_handler = IgnoreHandler(self.root_folder, notes_folder)
            self.notes_folder = Path(notes_folder).resolve()

            logger.info(f"File service initialized with root: {self.root_folder}")
            logger.info(f"Configured notes folder: {self.notes_folder}")
        except Exception as e:
            logger.error(f"Failed to initialize file service: {e}")
            raise

    def _validate_file_path(self, file_path: str) -> Path:
        """
        Validate file path is within watched directories and not ignored

        Args:
            file_path: Relative or absolute file path

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path is invalid or not allowed
        """
        # Normalize path separators (handle both forward and back slashes)
        file_path = file_path.replace('\\', '/')

        # Handle WSL style paths on Windows (/mnt/c/...)
        if os.name == 'nt' and (file_path.startswith('/mnt/') or file_path.startswith('mnt/')):
            # Normalize to start with /mnt/
            wsl_path = file_path if file_path.startswith('/') else '/' + file_path
            parts = wsl_path.split('/')
            if len(parts) >= 3:
                drive_letter = parts[2].upper()
                remaining_path = '/'.join(parts[3:])
                file_path = f"{drive_letter}:/{remaining_path}"
                logger.debug(f"Normalized WSL path {wsl_path} to Windows path {file_path}")

        # Convert to Path
        path = Path(file_path)

        # Handle absolute paths that might be missing leading slash due to URL collapsing
        # e.g. "mnt/d/..." -> "/mnt/d/..."
        if not path.is_absolute() and os.name != 'nt':
             if file_path.startswith('mnt/'):
                 path = Path('/' + file_path)
        elif not path.is_absolute() and os.name == 'nt':
            # Check if it looks like a Windows path missing a drive letter but starts with / or \
            if file_path.startswith('/'):
                 # It's an absolute path from the current drive root
                 pass
            elif len(file_path) > 1 and file_path[1] == ':':
                 # It's a Windows absolute path
                 pass
            else:
                # Truly relative path
                pass

        # Resolve to absolute path
        if not path.is_absolute():
            # Check if path already starts with notes folder name
            notes_folder_name = self.notes_folder.name
            if path.parts and path.parts[0] == notes_folder_name:
                # Path is relative to root folder (e.g., "notes/file.md")
                path = (self.root_folder / path).resolve()
            else:
                # Path is relative to notes folder (e.g., "file.md")
                path = (self.notes_folder / path).resolve()
        else:
            path = path.resolve()

        # Security check: Ensure path is within notes folder or watched directories
        try:
            # Check if path is within notes folder
            path.relative_to(self.notes_folder)
        except ValueError:
            # Not in notes folder, check if it's in a watched directory
            if not self.watch_handler.should_watch(path):
                raise ValueError(
                    f"Path '{file_path}' is not within watched directories. "
                    f"Allowed paths must be within: {self.notes_folder}"
                )

        # Check if path should be ignored
        if self.ignore_handler.should_ignore(path):
            raise ValueError(f"Path '{file_path}' matches ignore patterns and cannot be accessed")

        # Additional security: Prevent directory traversal
        if ".." in path.parts:
            raise ValueError(f"Path '{file_path}' contains invalid directory traversal")

        return path

    def read_file_content(self, file_path: str) -> Dict[str, Any]:
        """
        Read file content with metadata

        Args:
            file_path: Path to file (relative or absolute)

        Returns:
            Dict with content, metadata, and file info

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is invalid
            PermissionError: If file cannot be read
        """
        try:
            validated_path = self._validate_file_path(file_path)

            if not validated_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if not validated_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            # Read file content
            with open(validated_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get file stats
            stat = validated_path.stat()

            # Calculate relative path from root folder (consistent with tree/search)
            try:
                relative_path = validated_path.relative_to(self.root_folder)
                relative_path_str = str(relative_path).replace('\\', '/')
            except ValueError:
                # Fallback if not within root (shouldn't happen after validation)
                relative_path_str = str(validated_path).replace('\\', '/')

            return {
                'content': content,
                'path': str(validated_path),
                'relativePath': relative_path_str,
                'name': validated_path.name,
                'size': stat.st_size,
                'lastModified': int(stat.st_mtime),
                'extension': validated_path.suffix,
                'readable': True
            }

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def write_file_content(self, file_path: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
        """
        Write file content with atomic operation and optional backup

        Args:
            file_path: Path to file (relative or absolute)
            content: Content to write
            create_backup: Whether to create a backup before writing

        Returns:
            Dict with success status and file info

        Raises:
            ValueError: If path is invalid
            PermissionError: If file cannot be written
        """
        try:
            validated_path = self._validate_file_path(file_path)

            # Create parent directories if they don't exist
            validated_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file exists and backup is requested
            backup_path = None
            if create_backup and validated_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = validated_path.with_suffix(f'{validated_path.suffix}.bak.{timestamp}')
                shutil.copy2(validated_path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Atomic write: Write to temp file, then rename
            temp_path = validated_path.with_suffix(f'{validated_path.suffix}.tmp')
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Atomic rename
                temp_path.replace(validated_path)
                logger.info(f"Successfully wrote file: {validated_path}")

            except Exception as e:
                # Clean up temp file on error
                if temp_path.exists():
                    temp_path.unlink()
                raise

            # Get updated file stats
            stat = validated_path.stat()

            # Calculate relative path from root folder (consistent with tree/search)
            try:
                relative_path = validated_path.relative_to(self.root_folder)
                relative_path_str = str(relative_path).replace('\\', '/')
            except ValueError:
                # Fallback if not within root (shouldn't happen after validation)
                relative_path_str = str(validated_path).replace('\\', '/')

            # Trigger file monitoring system to detect the change
            try:
                from core.file_tracker import file_tracker
                # Trigger scan of this specific file
                file_tracker.process_file_change(str(validated_path), 'modified')
                logger.debug(f"Triggered monitoring for: {validated_path}")
            except Exception as e:
                logger.warning(f"Could not trigger file monitoring: {e}")

            return {
                'success': True,
                'path': str(validated_path),
                'relativePath': relative_path_str,
                'name': validated_path.name,
                'size': stat.st_size,
                'lastModified': int(stat.st_mtime),
                'backupCreated': backup_path is not None,
                'backupPath': str(backup_path) if backup_path else None
            }

        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise

    def search_files(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Fuzzy search across watched files

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of matching files with scores and metadata
        """
        try:
            results = []
            query_lower = query.lower()

            # Search through all watched markdown files
            if self.notes_folder.exists():
                for file_path in self.notes_folder.rglob('*.md'):
                    if not file_path.is_file():
                        continue

                    # Skip hidden files
                    if any(part.startswith('.') for part in file_path.parts):
                        continue

                    # Check if file should be ignored
                    if self.ignore_handler.should_ignore(file_path):
                        continue

                    # Check if file is watched
                    if not self.watch_handler.should_watch(file_path.resolve()):
                        continue

                    try:
                        # Calculate fuzzy match score
                        # Path relative to root folder (includes notes/ prefix)
                        relative_path = file_path.relative_to(self.root_folder)
                        file_name = file_path.stem
                        path_str = str(relative_path).replace('\\', '/')

                        # Score calculation (higher is better)
                        score = 0

                        # Exact match in filename
                        if query_lower in file_name.lower():
                            score += 100
                            # Boost for exact prefix match
                            if file_name.lower().startswith(query_lower):
                                score += 50

                        # Match in path
                        if query_lower in path_str.lower():
                            score += 50

                        # Character-by-character fuzzy matching
                        query_chars = list(query_lower)
                        search_text = (file_name + " " + path_str).lower()
                        char_idx = 0
                        consecutive = 0

                        for i, char in enumerate(search_text):
                            if char_idx < len(query_chars) and char == query_chars[char_idx]:
                                score += 10 + consecutive * 5  # Bonus for consecutive matches
                                consecutive += 1
                                char_idx += 1
                            else:
                                consecutive = 0

                        # Only include if all characters matched
                        if char_idx == len(query_chars) or score > 0:
                            stat = file_path.stat()
                            results.append({
                                'path': str(file_path),
                                'relativePath': str(relative_path),
                                'name': file_path.name,
                                'score': score,
                                'size': stat.st_size,
                                'lastModified': int(stat.st_mtime),
                                'extension': file_path.suffix,
                                'matchType': 'filename' if score >= 100 else 'path' if score >= 50 else 'fuzzy'
                            })

                    except Exception as e:
                        logger.debug(f"Error processing file {file_path} for search: {e}")
                        continue

            # Sort by score (descending) and limit results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:max_results]

        except Exception as e:
            logger.error(f"Failed to search files with query '{query}': {e}")
            raise

    def get_file_tree(self, max_depth: int = 5) -> Dict[str, Any]:
        """
        Build hierarchical file tree for watched directories

        Args:
            max_depth: Maximum depth to traverse

        Returns:
            Dict representing file tree structure
        """
        try:
            def build_tree(path: Path, current_depth: int = 0) -> Optional[Dict[str, Any]]:
                """Recursively build file tree"""
                if current_depth > max_depth or not path.exists():
                    return None

                # Skip hidden directories and files
                if path.name.startswith('.'):
                    return None

                # Check ignore patterns
                if self.ignore_handler.should_ignore(path):
                    return None

                node = {
                    'name': path.name,
                    'path': str(path),
                    'type': 'directory' if path.is_dir() else 'file',
                }

                if path.is_file():
                    # Only include markdown files
                    if not path.suffix == '.md':
                        return None

                    # Check if file is watched
                    if not self.watch_handler.should_watch(path.resolve()):
                        return None

                    try:
                        stat = path.stat()
                        # Calculate path relative to root folder (includes notes/ prefix)
                        relative_path = path.relative_to(self.root_folder)
                        node.update({
                            'relativePath': str(relative_path).replace('\\', '/'),  # Normalize to forward slashes
                            'size': stat.st_size,
                            'lastModified': int(stat.st_mtime),
                            'extension': path.suffix
                        })
                    except Exception as e:
                        logger.debug(f"Error getting stats for {path}: {e}")

                    return node

                # For directories, add children
                children = []
                try:
                    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                        child_node = build_tree(child, current_depth + 1)
                        if child_node:
                            children.append(child_node)
                except (OSError, PermissionError) as e:
                    logger.debug(f"Cannot read directory {path}: {e}")

                if children:
                    node['children'] = children
                    node['childCount'] = len(children)

                return node

            tree = build_tree(self.notes_folder)
            return tree if tree else {'name': 'notes', 'type': 'directory', 'children': []}

        except Exception as e:
            logger.error(f"Failed to build file tree: {e}")
            raise


# Singleton instance
_file_service_instance: Optional[FileService] = None


def get_file_service() -> FileService:
    """Get or create singleton FileService instance"""
    global _file_service_instance

    if _file_service_instance is None:
        from pathlib import Path
        root_folder = Path(__file__).parent.parent
        _file_service_instance = FileService(root_folder)

    return _file_service_instance
