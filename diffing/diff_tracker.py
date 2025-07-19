import difflib
from pathlib import Path
from utils.file_helpers import read_lines, create_timestamp

class DiffTracker:
    """Handles diff generation for tracked files."""
    
    def __init__(self, note_path, diff_path):
        self.note_path = Path(note_path)
        self.diff_path = Path(diff_path)
        self.last_file_lines = {}  # Track previous state per file
    
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
        print(f"[!] Change detected in {file_name}")
        
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
        
        # Save diff to file
        timestamp = create_timestamp()
        base_name = file_name.replace('.md', '')
        diff_file = self.diff_path / f"{base_name}.diff.{timestamp}.txt"
        diff_content = "\n".join(diff)
        diff_file.write_text(diff_content)
        print(f"    ↪ Diff saved to {diff_file}")
        
        # Update in-memory state for this file
        self.last_file_lines[file_key] = current_lines
        
        return True, diff_content
