"""Summary context configuration and generation planning models.

This module provides dataclasses for configuring summary generation context
and previewing what will be included in a summary before generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal


@dataclass
class TimeWindow:
    """Time window configuration for summary generation."""

    # Preset options: "1h", "6h", "24h", "7d", "custom"
    preset: Optional[str] = None

    # Custom date range (used when preset is "custom")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Include changes that were already covered in previous summaries
    include_previously_covered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "preset": self.preset,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "include_previously_covered": self.include_previously_covered,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimeWindow:
        """Create from dictionary."""
        return cls(
            preset=data.get("preset"),
            start_date=datetime.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            include_previously_covered=data.get("include_previously_covered", False) or data.get("includePreviouslyCovered", False),
        )

    def get_description(self) -> str:
        """Get human-readable description of time window."""
        if self.preset and self.preset != "custom":
            descriptions = {
                "1h": "last hour",
                "6h": "last 6 hours",
                "24h": "last 24 hours",
                "7d": "last 7 days",
            }
            return descriptions.get(self.preset, f"last {self.preset}")
        elif self.start_date and self.end_date:
            return f"{self.start_date.strftime('%Y-%m-%d %H:%M')} to {self.end_date.strftime('%Y-%m-%d %H:%M')}"
        elif self.start_date:
            return f"since {self.start_date.strftime('%Y-%m-%d %H:%M')}"
        elif self.end_date:
            return f"up to {self.end_date.strftime('%Y-%m-%d %H:%M')}"
        else:
            return "all time"


@dataclass
class FileFilters:
    """File and folder filtering configuration."""

    # Glob patterns to include (e.g., ["*.md", "src/**/*.py"])
    include_patterns: List[str] = field(default_factory=list)

    # Glob patterns to exclude (e.g., ["**/test_*.py", "*.tmp"])
    exclude_patterns: List[str] = field(default_factory=list)

    # Specific file paths to include (absolute or relative)
    specific_paths: List[str] = field(default_factory=list)

    # Whether to use .obbywatch defaults (True by default)
    use_obbywatch_defaults: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "specific_paths": self.specific_paths,
            "use_obbywatch_defaults": self.use_obbywatch_defaults,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileFilters:
        """Create from dictionary."""
        return cls(
            include_patterns=data.get("include_patterns", []),
            exclude_patterns=data.get("exclude_patterns", []),
            specific_paths=data.get("specific_paths", []),
            use_obbywatch_defaults=data.get("use_obbywatch_defaults", True),
        )


@dataclass
class ContentTypeFilters:
    """Content type filtering configuration."""

    # Include recent file changes (diffs)
    include_diffs: bool = True

    # Include existing note content
    include_existing_notes: bool = False

    # Include code files (.py, .ts, .tsx, .js, etc.)
    include_code_files: bool = True

    # Include documentation files (.md)
    include_documentation: bool = True

    # Include deleted files in analysis
    include_deleted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "include_diffs": self.include_diffs,
            "include_existing_notes": self.include_existing_notes,
            "include_code_files": self.include_code_files,
            "include_documentation": self.include_documentation,
            "include_deleted": self.include_deleted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContentTypeFilters:
        """Create from dictionary."""
        return cls(
            include_diffs=data.get("include_diffs", True),
            include_existing_notes=data.get("include_existing_notes", False),
            include_code_files=data.get("include_code_files", True),
            include_documentation=data.get("include_documentation", True),
            include_deleted=data.get("include_deleted", False),
        )


@dataclass
class ScopeControls:
    """Scope and depth controls for summary generation."""

    # Maximum number of files to include in summary (10-200)
    max_files: int = 50

    # Detail level: "brief", "standard", "detailed"
    detail_level: Literal["brief", "standard", "detailed"] = "standard"

    # Focus areas (optional tags/topics to emphasize)
    focus_areas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "max_files": self.max_files,
            "detail_level": self.detail_level,
            "focus_areas": self.focus_areas,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScopeControls:
        """Create from dictionary."""
        return cls(
            max_files=data.get("max_files", 50),
            detail_level=data.get("detail_level", "standard"),
            focus_areas=data.get("focus_areas", []),
        )


@dataclass
class SummaryContextConfig:
    """Complete context configuration for summary generation."""

    time_window: TimeWindow = field(default_factory=TimeWindow)
    file_filters: FileFilters = field(default_factory=FileFilters)
    content_types: ContentTypeFilters = field(default_factory=ContentTypeFilters)
    scope_controls: ScopeControls = field(default_factory=ScopeControls)
    include_previous_summaries: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "time_window": self.time_window.to_dict(),
            "file_filters": self.file_filters.to_dict(),
            "content_types": self.content_types.to_dict(),
            "scope_controls": self.scope_controls.to_dict(),
            "include_previous_summaries": self.include_previous_summaries,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SummaryContextConfig:
        """Create from dictionary."""
        return cls(
            time_window=TimeWindow.from_dict(data.get("time_window", {})),
            file_filters=FileFilters.from_dict(data.get("file_filters", {})),
            content_types=ContentTypeFilters.from_dict(data.get("content_types", {})),
            scope_controls=ScopeControls.from_dict(data.get("scope_controls", {})),
            include_previous_summaries=data.get("include_previous_summaries", False) or data.get("includePreviousSummaries", False),
        )

    @classmethod
    def from_json(cls, json_str: str) -> SummaryContextConfig:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def default(cls) -> SummaryContextConfig:
        """Create default configuration (matches current behavior)."""
        return cls(
            time_window=TimeWindow(preset="auto"),  # Auto = since last update
            file_filters=FileFilters(
                include_patterns=["*.md"],
                use_obbywatch_defaults=True,
            ),
            content_types=ContentTypeFilters(
                include_diffs=True,
                include_existing_notes=False,
                include_code_files=False,
                include_documentation=True,
                include_deleted=False,
            ),
            scope_controls=ScopeControls(
                max_files=50,
                detail_level="standard",
            ),
        )


@dataclass
class MatchedFile:
    """Information about a file matched for summary generation."""

    # File path (relative to project root)
    path: str

    # Change summary (e.g., "5 additions, 2 deletions")
    change_summary: str

    # Last modified timestamp
    last_modified: datetime

    # File size in bytes
    size_bytes: Optional[int] = None

    # Whether file is deleted
    is_deleted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "change_summary": self.change_summary,
            "last_modified": self.last_modified.isoformat(),
            "size_bytes": self.size_bytes,
            "is_deleted": self.is_deleted,
        }


@dataclass
class SummaryGenerationPlan:
    """Preview of what will be included in a summary before generation."""

    # Configuration used for this plan
    context_config: SummaryContextConfig

    # Files that matched the criteria
    matched_files: List[MatchedFile] = field(default_factory=list)

    # Human-readable time range description
    time_range_description: str = ""

    # Estimated scope metrics
    total_files: int = 0
    total_changes: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

    # Summary of applied filters
    filters_applied: List[str] = field(default_factory=list)

    # Warnings or notes about the plan
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "context_config": self.context_config.to_dict(),
            "matched_files": [f.to_dict() for f in self.matched_files],
            "time_range_description": self.time_range_description,
            "total_files": self.total_files,
            "total_changes": self.total_changes,
            "total_lines_added": self.total_lines_added,
            "total_lines_removed": self.total_lines_removed,
            "filters_applied": self.filters_applied,
            "warnings": self.warnings,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SummaryGenerationPlan:
        """Create from dictionary."""
        matched_files = [
            MatchedFile(
                path=f["path"],
                change_summary=f["change_summary"],
                last_modified=datetime.fromisoformat(f["last_modified"]),
                size_bytes=f.get("size_bytes"),
                is_deleted=f.get("is_deleted", False),
            )
            for f in data.get("matched_files", [])
        ]

        return cls(
            context_config=SummaryContextConfig.from_dict(data.get("context_config", {})),
            matched_files=matched_files,
            time_range_description=data.get("time_range_description", ""),
            total_files=data.get("total_files", 0),
            total_changes=data.get("total_changes", 0),
            total_lines_added=data.get("total_lines_added", 0),
            total_lines_removed=data.get("total_lines_removed", 0),
            filters_applied=data.get("filters_applied", []),
            warnings=data.get("warnings", []),
        )
