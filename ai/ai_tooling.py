"""AI tooling utilities and helper classes.

This module currently provides a grep-based notes search tool that can be
invoked from higher-level agent workflows. The design keeps the execution
surface small while capturing enough structured data to experiment with
agentic loops later on.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


class ToolExecutionError(RuntimeError):
    """Raised when an AI tool cannot complete its task."""


@dataclass
class SearchMatch:
    """Single match produced by the notes search tool."""

    file_path: Path
    line_number: int
    snippet: str

    def absolute_path(self, notes_root: Path) -> Path:
        """Return the absolute path assuming the provided notes root."""
        return notes_root / self.file_path


@dataclass
class ToolResult:
    """Standardised response envelope for AI tool results."""

    success: bool
    query: str
    matches: List[SearchMatch]
    raw_output: str
    command: Sequence[str]
    error: Optional[str] = None

    def format_for_agent(self) -> str:
        """Return a compact string representation for agent consumption."""
        if not self.matches:
            return f"No matches for '{self.query}'."

        lines = [f"Search results for '{self.query}':"]
        for match in self.matches:
            relative_path = match.file_path.as_posix()
            lines.append(f"- {relative_path}:{match.line_number} → {match.snippet.strip()}")
        return "\n".join(lines)


class NotesSearchTool:
    """Execute grep-based searches over the `notes/` directory.

    The tool is intentionally lightweight so that it can slot into different
    agent orchestration patterns. A typical loop might:
    1. Inspect the current task and decide whether file search is required.
    2. Call ``NotesSearchTool.run`` with an appropriate query string.
    3. Feed ``ToolResult.format_for_agent`` back into the language model to
       determine follow-up actions (e.g., open a specific file or ask the user).

    Future iterations can wrap this tool with planners or routers without
    changing the core behaviour implemented here.
    """

    name = "notes_search"
    description = "Search local notes with ripgrep/grep and return structured matches."

    def __init__(self, notes_dir: Optional[Path] = None, max_matches: int = 20):
        self.notes_dir = notes_dir or Path(__file__).resolve().parent.parent / "notes"
        self.max_matches = max_matches
        self._command = self._select_command()

    def run(self, query: str, max_matches: Optional[int] = None) -> ToolResult:
        """Execute the search and return structured results."""
        if not query:
            raise ValueError("query must be a non-empty string")

        if not self.notes_dir.exists() or not self.notes_dir.is_dir():
            raise ToolExecutionError(f"Notes directory not found: {self.notes_dir}")

        command_name, base_args = self._command
        match_limit = max_matches if max_matches is not None else self.max_matches

        command = [command_name, *base_args]
        if match_limit:
            command.extend(["-m", str(match_limit)])
        command.append(query)
        command.append(".")

        logger.debug("Running notes search: %s", " ".join(command))

        completed = subprocess.run(
            command,
            cwd=str(self.notes_dir),
            capture_output=True,
            text=True,
        )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()

        if completed.returncode not in (0, 1):
            error_message = stderr or f"Search command failed with code {completed.returncode}"
            logger.error("Notes search command failed: %s", error_message)
            raise ToolExecutionError(error_message)

        matches = self._parse_matches(stdout.splitlines()) if stdout else []
        success = completed.returncode == 0

        return ToolResult(
            success=success,
            query=query,
            matches=matches,
            raw_output=stdout,
            command=command,
            error=stderr or None,
        )

    def _parse_matches(self, lines: Sequence[str]) -> List[SearchMatch]:
        """Convert raw grep output into structured matches."""
        matches: List[SearchMatch] = []
        for line in lines:
            if not line or line.startswith("--"):
                continue

            parts = line.split(":", 2)
            if len(parts) < 3:
                logger.debug("Skipping unparsable search line: %s", line)
                continue

            path_str, line_number_str, snippet = parts
            try:
                line_number = int(line_number_str)
            except ValueError:
                logger.debug("Skipping line with non-integer number: %s", line)
                continue

            match_path = Path(path_str)
            matches.append(SearchMatch(match_path, line_number, snippet))
        return matches

    def _select_command(self) -> Tuple[str, List[str]]:
        """Pick the best available search command with sane defaults."""
        if shutil.which("rg"):
            return ("rg", ["--color=never", "--line-number"])

        if shutil.which("grep"):
            return ("grep", ["-Rin"])

        raise ToolExecutionError("Neither 'rg' nor 'grep' is available on the system")


def get_default_tools() -> List[NotesSearchTool]:
    """Expose default tool instances for quick registration."""
    return [NotesSearchTool()]


__all__ = [
    "NotesSearchTool",
    "ToolExecutionError",
    "ToolResult",
    "SearchMatch",
    "get_default_tools",
]
