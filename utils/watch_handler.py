"""
Watch pattern handler for .obbywatch files.
Specifies directories that Obby should monitor for changes.
"""

import fnmatch
import logging
from pathlib import Path
from typing import List, Set


class WatchHandler:
    """Handles .obbywatch file parsing and directory specification."""
    
    def __init__(self, utils_folder: Path = None):
        """
        Initialize the watch handler.
        
        Args:
            utils_folder: Base folder that contains the `.obbywatch` file. If not
                provided, defaults to the project root (current working directory).
        """
        # Default to project root if not provided
        self.utils_folder = Path(utils_folder) if utils_folder is not None else Path.cwd()
        self.watch_file = self.utils_folder / ".obbywatch"
        self.watch_patterns: Set[str] = set()
        self.load_watch_patterns()
    
    def load_watch_patterns(self):
        """Load watch patterns from .obbywatch file."""
        self.watch_patterns.clear()
        
        if not self.watch_file.exists():
            # Create a default .obbywatch file with common directories
            self.create_default_watch_file()
        
        try:
            with open(self.watch_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        self.watch_patterns.add(line)
            
            logging.info(f"Loaded {len(self.watch_patterns)} watch patterns from .obbywatch")
        except Exception as e:
            logging.error(f"Error loading .obbywatch: {e}")
    
    def create_default_watch_file(self):
        """Create a default .obbywatch file with common directories."""
        default_content = """# Obby watch file
# This file specifies directories that Obby should monitor for changes
# Use glob patterns (* and ?) and one pattern per line
# Lines starting with # are comments

# Default directories to watch
notes/
docs/
*.md

# Example patterns:
# project_notes/
# research/
# writing/
# *.txt
"""
        
        try:
            with open(self.watch_file, 'w', encoding='utf-8') as f:
                f.write(default_content)
            logging.info(f"Created default .obbywatch file")
        except Exception as e:
            logging.error(f"Error creating .obbywatch: {e}")
    
    def should_watch(self, file_path: Path, base_path: Path = None) -> bool:
        """
        Check if a file/directory should be watched based on watch patterns.
        
        Args:
            file_path: Path to the file/directory to check
            base_path: Base path to calculate relative path from (defaults to utils parent)
            
        Returns:
            bool: True if the file should be watched, False otherwise
        """
        if not self.watch_patterns:
            # If no patterns specified, watch everything
            return True
        
        # Use utils folder (where .obbywatch lives) as base path if not specified
        if base_path is None:
            base_path = self.utils_folder
        
        # Get relative path from base path
        try:
            rel_path = file_path.relative_to(base_path)
            rel_path_str = str(rel_path).replace('\\', '/')  # Use forward slashes for consistency
        except ValueError:
            # File is outside base path, don't watch
            return False
        
        # Check against each watch pattern
        for pattern in self.watch_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                if file_path.is_dir() and fnmatch.fnmatch(rel_path_str + '/', pattern):
                    return True
                # Also check if file is inside a watched directory
                path_parts = rel_path_str.split('/')
                for i in range(len(path_parts)):
                    partial_path = '/'.join(path_parts[:i+1]) + '/'
                    if fnmatch.fnmatch(partial_path, pattern):
                        return True
            else:
                # Handle file patterns
                if fnmatch.fnmatch(rel_path_str, pattern):
                    return True
                # Also check just the filename
                if fnmatch.fnmatch(file_path.name, pattern):
                    return True
        
        return False
    
    def get_watch_directories(self, base_path: Path = None) -> List[Path]:
        """
        Get list of directories that should be watched based on patterns.
        
        Args:
            base_path: Base path to resolve patterns from (defaults to utils parent)
            
        Returns:
            List[Path]: List of directory paths to watch
        """
        if base_path is None:
            base_path = self.utils_folder
        
        watch_dirs = []
        
        for pattern in self.watch_patterns:
            # Handle directory patterns
            if pattern.endswith('/'):
                pattern_path = base_path / pattern.rstrip('/')
                if pattern_path.exists() and pattern_path.is_dir():
                    watch_dirs.append(pattern_path)
            else:
                # For file patterns, add the parent directory
                if '*' in pattern or '?' in pattern:
                    # For glob patterns, add the base directory
                    watch_dirs.append(base_path)
                else:
                    # For specific files, add their parent directory
                    file_path = base_path / pattern
                    if file_path.exists():
                        if file_path.is_dir():
                            watch_dirs.append(file_path)
                        else:
                            watch_dirs.append(file_path.parent)
        
        # Remove duplicates and return
        return list(set(watch_dirs))
    
    def reload_patterns(self):
        """Reload watch patterns from file."""
        self.load_watch_patterns()
