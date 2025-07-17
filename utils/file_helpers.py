from pathlib import Path
from datetime import datetime

def read_lines(path):
    """Read lines from a file, return empty list if file doesn't exist."""
    if path.exists():
        return path.read_text().splitlines()
    return []

def ensure_directories(*paths):
    """Create directories if they don't exist."""
    for path in paths:
        Path(path).mkdir(exist_ok=True)

def create_timestamp():
    """Create a timestamp string for filenames."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def setup_test_file(note_path):
    """Create test file if it doesn't exist."""
    if not note_path.exists():
        note_path.parent.mkdir(exist_ok=True)
        note_path.write_text("# My Notes\n\nThis is a test file for obby to watch.\nTry editing this file to see obby in action!\n")
        print(f"✓ Created {note_path}")
