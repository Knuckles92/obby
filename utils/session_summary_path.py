"""
Utility to resolve the current Session Summary path based on configuration.

Supports single-file mode or daily-per-file mode.
"""

from pathlib import Path
from datetime import datetime

try:
    from config.settings import (
        SESSION_SUMMARY_MODE,
        SESSION_SUMMARY_PATH,
        SESSION_SUMMARY_DAILY_DIR,
        SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE,
    )
except Exception:
    # Minimal fallbacks if settings are unavailable at import time
    SESSION_SUMMARY_MODE = "single"
    SESSION_SUMMARY_PATH = Path("notes/session_summary.md")
    SESSION_SUMMARY_DAILY_DIR = Path("notes/daily")
    SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE = "Session Summary - {date}.md"


def resolve_session_summary_path(now: datetime | None = None) -> Path:
    """Resolve the current Session Summary path based on mode.

    - daily: notes/daily/"Session Summary - YYYY-MM-DD.md"
    - single: notes/session_summary.md
    """
    if now is None:
        now = datetime.now()

    mode = str(SESSION_SUMMARY_MODE).lower() if SESSION_SUMMARY_MODE is not None else "single"
    if mode == "daily":
        # Ensure directory exists
        try:
            Path(SESSION_SUMMARY_DAILY_DIR).mkdir(parents=True, exist_ok=True)
        except Exception:
            Path("notes/daily").mkdir(parents=True, exist_ok=True)
        date_str = now.strftime("%Y-%m-%d")
        filename = SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE.format(date=date_str)
        return Path(SESSION_SUMMARY_DAILY_DIR) / filename

    # Single-file mode
    path = Path(SESSION_SUMMARY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


