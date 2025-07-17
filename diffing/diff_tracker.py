import difflib
from pathlib import Path
from utils.file_helpers import read_lines, create_timestamp

class DiffTracker:
    """Handles diff generation and snapshot management."""
    
    def __init__(self, note_path, snapshot_path, diff_path):
        self.note_path = Path(note_path)
        self.snapshot_path = Path(snapshot_path)
        self.diff_path = Path(diff_path)
        self.last_snapshot_lines = []
    
    def check_for_changes(self):
        """Check if the file has changed since last snapshot."""
        current_lines = read_lines(self.note_path)
        
        if current_lines != self.last_snapshot_lines:
            return self._process_change(current_lines)
        return False, None
    
    def _process_change(self, current_lines):
        """Process a detected change by creating diff and snapshot."""
        print("[!] Change detected in test.md")
        
        # Create diff
        diff = difflib.unified_diff(
            self.last_snapshot_lines,
            current_lines,
            fromfile="previous",
            tofile="current",
            lineterm=""
        )
        
        # Save diff to file
        timestamp = create_timestamp()
        diff_file = self.diff_path / f"test.diff.{timestamp}.txt"
        diff_content = "\n".join(diff)
        diff_file.write_text(diff_content)
        print(f"    ↪ Diff saved to {diff_file}")
        
        # Save new snapshot
        snap_file = self.snapshot_path / f"test.md.{timestamp}.txt"
        snap_file.write_text("\n".join(current_lines))
        print(f"    ↪ Snapshot saved to {snap_file}")
        
        # Update in-memory snapshot
        self.last_snapshot_lines = current_lines
        
        return True, diff_content
    
    def get_latest_snapshot(self):
        """Get the path to the latest snapshot file."""
        files = sorted(self.snapshot_path.glob("*.md"))
        if not files:
            return None
        return files[-1]
