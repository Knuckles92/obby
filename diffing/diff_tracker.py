import difflib
import logging
from pathlib import Path
from utils.file_helpers import read_lines
from database.models import DiffModel, FileStateModel
import hashlib

class DiffTracker:
    """Handles diff generation for tracked files."""
    
    def __init__(self, note_path, diff_path):
        self.note_path = Path(note_path)
        self.diff_path = Path(diff_path)  # Kept for backward compatibility
        self.last_file_lines = {}  # Legacy cache, migrating to database
    
    def check_for_changes(self):
        """Check if the file has changed since last check."""
        current_lines = read_lines(self.note_path)
        file_key = str(self.note_path)
        
        # Get previous state for this file
        previous_lines = self.last_file_lines.get(file_key, [])
        
        if current_lines != previous_lines:
            return self._process_change(current_lines, file_key)
        return False, None
    
    def _process_change(self, current_lines, file_key):
        """Process a detected change by creating diff."""
        file_name = self.note_path.name
        logging.info(f"Change detected in {file_name}")
        
        # Get previous state for this file
        previous_lines = self.last_file_lines.get(file_key, [])
        
        # Create diff
        diff = difflib.unified_diff(
            previous_lines,
            current_lines,
            fromfile="previous",
            tofile="current",
            lineterm=""
        )
        
        # Save diff to database instead of file
        diff_content = "\n".join(diff)
        diff_id = DiffModel.insert(
            file_path=str(self.note_path),
            diff_content=diff_content
        )
        
        if diff_id:
            logging.info(f"Diff saved to database with ID: {diff_id}")
        else:
            logging.error(f"Failed to save diff to database for {file_name}")
        
        # Update database file state instead of in-memory storage
        content_hash = hashlib.sha256('\n'.join(current_lines).encode('utf-8')).hexdigest()
        FileStateModel.update_state(
            file_path=file_key,
            content_hash=content_hash,
            line_count=len(current_lines)
        )
        
        # Clear in-memory cache (transitioning to database)
        self.last_file_lines[file_key] = current_lines
        
        return True, diff_content
