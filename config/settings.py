from pathlib import Path

# File paths
NOTES_FOLDER = Path("notes")  # Folder containing all markdown files to monitor
DIFF_PATH = Path("diffs")

# Living Note configuration
# Mode can be "single" (append to one file) or "daily" (one file per day)
LIVING_NOTE_MODE = "daily"

# Single-file fallback path (used when LIVING_NOTE_MODE == "single")
LIVING_NOTE_PATH = Path("output/living_note.md")

# Daily mode configuration (used when LIVING_NOTE_MODE == "daily")
# The daily notes will be created inside this directory with the filename format below
LIVING_NOTE_DAILY_DIR = Path("output/daily")
# Filename may include {date} placeholder in YYYY-MM-DD format
LIVING_NOTE_DAILY_FILENAME_TEMPLATE = "Living Note - {date}.md"

# Timing settings
CHECK_INTERVAL = 20  # seconds

# File monitoring settings
FILE_WATCHER_DEBOUNCE_DELAY = 0.5  # seconds - debounce delay for watchdog events
PERIODIC_SCAN_ENABLED = True  # Enable periodic scanning (backup to watchdog)
WATCHDOG_COORDINATION_ENABLED = True  # Skip periodic scans when watchdog is active
VERBOSE_MONITORING_LOGS = False  # Enable verbose monitoring logs for debugging

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

# File change validation settings
FILE_SIZE_CHANGE_VALIDATION = True  # Check file size before processing changes
FILE_MTIME_CHANGE_VALIDATION = True  # Check modification time before processing changes
CONTENT_HASH_VALIDATION = True  # Always validate content hash (recommended)
