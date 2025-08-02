from pathlib import Path

# File paths
NOTES_FOLDER = Path("notes")  # Folder containing all markdown files to monitor
DIFF_PATH = Path("diffs")
LIVING_NOTE_PATH = Path("notes/living_note.md")

# Timing settings
CHECK_INTERVAL = 20  # seconds

# OpenAI settings
OPENAI_MODEL = "gpt-4.1-mini"  # Default model for AI summarization
OPENAI_API_KEY = None  # Set via environment variable OPENAI_API_KEY

# AI Update settings (separate from file monitoring frequency)
AI_UPDATE_INTERVAL = 12  # hours - how often AI processing runs (default: twice daily)
AI_AUTO_UPDATE_ENABLED = True  # whether AI auto-updates are enabled
LAST_AI_UPDATE_TIMESTAMP = None  # tracks when AI was last run (managed by database)

# Batch AI Processing settings (legacy - kept for compatibility)
BATCH_AI_ENABLED = True  # Enable batch AI processing by default
BATCH_AI_MAX_SIZE = 50  # Maximum number of changes to process in one batch
