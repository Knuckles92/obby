from pathlib import Path

# File paths
NOTES_FOLDER = Path("notes")  # Folder containing all markdown files to monitor
DIFF_PATH = Path("diffs")
LIVING_NOTE_PATH = Path("notes/living_note.md")

# Timing settings
CHECK_INTERVAL = 20  # seconds

# OpenAI settings
OPENAI_MODEL = "gpt-4o-mini"  # Default model for AI summarization
OPENAI_API_KEY = None  # Set via environment variable OPENAI_API_KEY
