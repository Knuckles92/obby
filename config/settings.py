from pathlib import Path

# File paths
NOTES_FOLDER = Path("notes")  # Folder containing all markdown files to monitor
SNAPSHOT_PATH = Path("snapshots")
DIFF_PATH = Path("diffs")
LIVING_NOTE_PATH = Path("notes/living_note.md")

# Timing settings
CHECK_INTERVAL = 20  # seconds

# OpenAI settings (for future use)
OPENAI_MODEL = "gpt-4.1-mini"
OPENAI_API_KEY = None  # Set via environment variable
