from pathlib import Path

# File paths
NOTES_FOLDER = Path("notes")  # Default folder containing all markdown files to monitor

def get_configured_notes_folder():
    """Get the configured monitoring directory from database, with fallback to default"""
    try:
        from database.models import ConfigModel
        configured_dir = ConfigModel.get('monitoringDirectory', str(NOTES_FOLDER))
        return Path(configured_dir)
    except Exception:
        # Fallback if database is not available yet
        return NOTES_FOLDER
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
OPENAI_MODEL = "gpt-5-mini"  # Default model for AI summarization
OPENAI_API_KEY = None  # Set via environment variable OPENAI_API_KEY

# OpenAI generation temperatures (centralized)
# You can override any of these at runtime if desired.
OPENAI_TEMPERATURES = {
    "diff_summary": 0.7,
    "minimal_summary": 0.7,
    "proposed_questions": 0.7,
    "session_title": 0.6,
    "events_summary": 0.7,
    "tree_summary": 0.7,
    "insights": 0.7,
    "batch_summary": 0.7,
}

# OpenAI token limits (centralized)
# These are per-feature caps for `max_completion_tokens` (or equivalent). Override at runtime if needed.
OPENAI_TOKEN_LIMITS = {
    "diff_summary": 25000,
    "minimal_summary": 800,
    "proposed_questions": 5000,
    "session_title": 50,
    "events_summary": 5000,
    "tree_summary": 5000,
    "insights": 30000,
    "batch_summary": 25000,
    "chat": 2000,
}

# AI Sources fallback (safety net)
# NOTE: This switch is a last‑resort safety mechanism. Keep it OFF by default.
# When enabled, if a model response unexpectedly omits the required 'Sources' section,
# the app will synthesize a minimal '### Sources' block using the already-known file list
# and lightweight model assistance. Intended only as a contingency to preserve provenance.
AI_SOURCES_FALLBACK_ENABLED = False

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
