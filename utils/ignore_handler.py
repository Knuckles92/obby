"""
Ignore pattern handler for .obbyignore files.
Supports glob patterns and basic ignore syntax similar to .gitignore.
"""

import fnmatch
import logging
from pathlib import Path
from typing import List, Set


class IgnoreHandler:
    """Handles .obbyignore file parsing and pattern matching."""
    
    def __init__(self, utils_folder: Path, notes_folder: Path = None):
        """
        Initialize the ignore handler.
        
        Args:
            utils_folder: Path to the utils folder containing .obbyignore file
            notes_folder: Path to the folder containing notes (for relative path calculation)
        """
        self.utils_folder = Path(utils_folder)
        self.notes_folder = Path(notes_folder) if notes_folder else self.utils_folder.parent
        self.ignore_file = self.utils_folder / ".obbyignore"
        self.ignore_patterns: Set[str] = set()
        self.load_ignore_patterns()
    
    def load_ignore_patterns(self):
        """Load ignore patterns from .obbyignore file."""
        self.ignore_patterns.clear()
        
        if not self.ignore_file.exists():
            # Create a default .obbyignore file with common patterns
            self.create_default_ignore_file()
        
        try:
            with open(self.ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        self.ignore_patterns.add(line)
            
            logging.info(f"Loaded {len(self.ignore_patterns)} ignore patterns from .obbyignore")
        except Exception as e:
            logging.error(f"Error loading .obbyignore: {e}")
    
    def create_default_ignore_file(self):
        """Create a default .obbyignore file with common patterns."""
        default_content = """# Obby ignore file
# This file specifies patterns for files and directories that Obby should ignore
# Use glob patterns (* and ?) and one pattern per line
# Lines starting with # are comments

# Living note file (to prevent feedback loops)
living_note.md
daily/

# Temporary files
*.tmp
*.temp
*~
.DS_Store
Thumbs.db

# Version control
.git/
.svn/

# Common editor files
.vscode/
.idea/
*.swp
*.swo
"""
        
        try:
            with open(self.ignore_file, 'w', encoding='utf-8') as f:
                f.write(default_content)
            logging.info(f"Created default .obbyignore file")
        except Exception as e:
            logging.error(f"Error creating .obbyignore: {e}")
    
    def should_ignore(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored based on ignore patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file should be ignored, False otherwise
        """
        if not self.ignore_patterns:
            return False
        
        # Get relative path from notes folder
        try:
            rel_path = file_path.relative_to(self.notes_folder)
            rel_path_str = str(rel_path).replace('\\', '/')  # Use forward slashes for consistency
        except ValueError:
            # File is outside notes folder, don't ignore
            return False
        
        # Check against each ignore pattern
        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                if file_path.is_dir() and fnmatch.fnmatch(rel_path_str + '/', pattern):
                    return True
                # Also check if file is inside an ignored directory
                if fnmatch.fnmatch(rel_path_str.split('/')[0] + '/', pattern):
                    return True
            else:
                # Handle file patterns
                if fnmatch.fnmatch(rel_path_str, pattern):
                    return True
                # Also check just the filename
                if fnmatch.fnmatch(file_path.name, pattern):
                    return True
        
        return False
    
    def reload_if_changed(self):
        """Reload ignore patterns if .obbyignore file has been modified."""
        if self.ignore_file.exists():
            try:
                current_mtime = self.ignore_file.stat().st_mtime
                if not hasattr(self, '_last_mtime') or current_mtime != self._last_mtime:
                    self.load_ignore_patterns()
                    self._last_mtime = current_mtime
            except Exception as e:
                logging.error(f"Error checking .obbyignore modification time: {e}")
