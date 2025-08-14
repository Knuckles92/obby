"""
Utility to resolve the current Living Note path based on configuration.

Supports single-file mode or daily-per-file mode.
"""

from pathlib import Path
from datetime import datetime

try:
    from config.settings import (
        LIVING_NOTE_MODE,
        LIVING_NOTE_PATH,
        LIVING_NOTE_DAILY_DIR,
        LIVING_NOTE_DAILY_FILENAME_TEMPLATE,
    )
except Exception:
    # Minimal fallbacks if settings are unavailable at import time
    LIVING_NOTE_MODE = "single"
    LIVING_NOTE_PATH = Path("notes/living_note.md")
    LIVING_NOTE_DAILY_DIR = Path("notes/daily")
    LIVING_NOTE_DAILY_FILENAME_TEMPLATE = "Living Note - {date}.md"


def resolve_living_note_path(now: datetime | None = None) -> Path:
    """Resolve the current Living Note path based on mode.

    - daily: notes/daily/"Living Note - YYYY-MM-DD.md"
    - single: notes/living_note.md
    """
    if now is None:
        now = datetime.now()

    mode = str(LIVING_NOTE_MODE).lower() if LIVING_NOTE_MODE is not None else "single"
    if mode == "daily":
        # Ensure directory exists
        try:
            Path(LIVING_NOTE_DAILY_DIR).mkdir(parents=True, exist_ok=True)
        except Exception:
            Path("notes/daily").mkdir(parents=True, exist_ok=True)
        date_str = now.strftime("%Y-%m-%d")
        filename = LIVING_NOTE_DAILY_FILENAME_TEMPLATE.format(date=date_str)
        return Path(LIVING_NOTE_DAILY_DIR) / filename

    # Single-file mode
    path = Path(LIVING_NOTE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


