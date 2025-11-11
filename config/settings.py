from pathlib import Path
import os

# File paths
NOTES_FOLDER = Path("notes")  # Default folder containing all markdown files to monitor

def get_configured_notes_folder():
    """Get the configured monitoring directory from database, with fallback to default"""
    try:
        from database.models import ConfigModel
        configured_dir = ConfigModel.get('monitoringDirectory', str(NOTES_FOLDER))
        return Path(configured_dir)
    except Exception:
        # Fallback if database is no t available yet
        return NOTES_FOLDER
DIFF_PATH = Path("diffs")

# Session Summary configuration
# Mode can be "single" (append to one file) or "daily" (one file per day)
SESSION_SUMMARY_MODE = "daily"

# Single-file fallback path (used when SESSION_SUMMARY_MODE == "single")
SESSION_SUMMARY_PATH = Path("output/session_summary.md")

# Daily mode configuration (used when SESSION_SUMMARY_MODE == "daily")
# The daily summaries will be created inside this directory with the filename format below
SESSION_SUMMARY_DAILY_DIR = Path("output/daily")
# Filename may include {date} placeholder in YYYY-MM-DD format
SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE = "Session Summary - {date}.md"

# Timing settings
CHECK_INTERVAL = 20  # seconds

# File monitoring settings
FILE_WATCHER_DEBOUNCE_DELAY = 0.5  # seconds - debounce delay for watchdog events
PERIODIC_SCAN_ENABLED = True  # Enable periodic scanning (backup to watchdog)
WATCHDOG_COORDINATION_ENABLED = True  # Skip periodic scans when watchdog is active
VERBOSE_MONITORING_LOGS = False  # Enable verbose monitoring logs for debugging

# ============================================================================
# AI SETTINGS - Claude Agent SDK
# ============================================================================

# Claude Model Selection
CLAUDE_MODEL = "haiku"  # Default model for Claude: "sonnet", "opus", "haiku"
# Can be overridden with OBBY_CLAUDE_MODEL environment variable
# API Key: Set via ANTHROPIC_API_KEY environment variable

# Real-time Summary Processing
SUMMARY_DEBOUNCE_WINDOW = 30  # seconds - wait time to batch rapid file changes before summarizing
SUMMARY_AUTO_UPDATE_ENABLED = True  # Enable automatic summary generation on file changes
MAX_FILES_PER_SUMMARY = 50  # Maximum number of changed files to include in one summary

# Claude Tool Permissions for Summaries
CLAUDE_SUMMARY_ALLOWED_TOOLS = ["Read", "Grep", "Glob"]  # Tools Claude can use for exploration
CLAUDE_SUMMARY_MAX_TURNS = 15  # Maximum exploration turns for session summaries
CLAUDE_FILE_SUMMARY_MAX_TURNS = 10  # Maximum turns for individual file summaries

# Summary Output Validation
CLAUDE_VALIDATION_RETRY_ENABLED = True  # Retry with stricter prompt if format validation fails
CLAUDE_FALLBACK_ON_ERROR = True  # Use deterministic fallback if Claude errors or format fails

# AI Sources section handling
# NOTE: With Claude's new format, Sources are required in every summary.
# This setting controls fallback behavior if Sources section is missing.
AI_SOURCES_FALLBACK_ENABLED = False  # Keep OFF - validation should catch missing Sources

# File change validation settings
FILE_SIZE_CHANGE_VALIDATION = True  # Check file size before processing changes
FILE_MTIME_CHANGE_VALIDATION = True  # Check modification time before processing changes
CONTENT_HASH_VALIDATION = True  # Always validate content hash (recommended)

# ============================================================================
# AGENT LOGGING - Transparency and Debugging
# ============================================================================

# Agent logging configuration
AGENT_LOGGING_ENABLED = True  # Enable comprehensive agent logging to database
AGENT_LOG_VERBOSITY = 'normal'  # Verbosity level: 'minimal', 'normal', 'verbose'
AGENT_LOG_INCLUDE_PROMPTS = False  # Include full prompts in logs (for 'verbose' mode)
AGENT_LOG_INCLUDE_RESPONSES = False  # Include full responses in logs (for 'verbose' mode)

# Log retention (manual cleanup via admin panel)
# No automatic cleanup - logs are retained indefinitely until manually deleted
AGENT_LOG_AUTO_CLEANUP_ENABLED = False  # Disable automatic cleanup by default
AGENT_LOG_RETENTION_DAYS = None  # No automatic retention limit (manual cleanup only)

# ============================================================================
# GO MICROSERVICES - Feature Flags for Gradual Rollout
# ============================================================================

# Feature flags for gradual rollout
USE_GO_FILE_WATCHER = os.getenv("USE_GO_FILE_WATCHER", "false").lower() == "true"
GO_FILE_WATCHER_HOST = os.getenv("GO_FILE_WATCHER_HOST", "localhost")
GO_FILE_WATCHER_PORT = int(os.getenv("GO_FILE_WATCHER_PORT", "50051"))

USE_GO_CONTENT_TRACKER = os.getenv("USE_GO_CONTENT_TRACKER", "false").lower() == "true"
GO_CONTENT_TRACKER_HOST = os.getenv("GO_CONTENT_TRACKER_HOST", "localhost")
GO_CONTENT_TRACKER_PORT = int(os.getenv("GO_CONTENT_TRACKER_PORT", "50052"))

# Rollout percentage (0-100) for gradual migration
GO_WATCHER_ROLLOUT_PERCENTAGE = int(os.getenv("GO_WATCHER_ROLLOUT_PERCENTAGE", "0"))
GO_TRACKER_ROLLOUT_PERCENTAGE = int(os.getenv("GO_TRACKER_ROLLOUT_PERCENTAGE", "0"))

# Emergency rollback flag
EMERGENCY_ROLLBACK_TO_PYTHON = os.getenv("EMERGENCY_ROLLBACK", "false").lower() == "true"
