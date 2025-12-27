"""
Working Context Service
=======================

Builds a contextual understanding of the user's recent work activity
to enable intelligent, context-aware insight generation.

The working context includes:
- Recent files with recency scores
- Active projects detected from file clustering
- Work trajectory (what the user seems to be focusing on)
- Hot topics (frequently appearing tags/mentions)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import Counter
from pathlib import Path

from database.models import db
from database.migration_semantic_insights_v2 import get_config, update_last_context_build

logger = logging.getLogger(__name__)


@dataclass
class RecentFile:
    """A recently modified file with recency scoring."""
    path: str
    last_modified: datetime
    recency_score: float
    directory: str
    tags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    active_todos: int = 0


@dataclass
class WorkingContext:
    """
    Represents the user's current working context for intelligent insights.

    This context helps the AI understand:
    - What the user has been working on recently
    - Which projects are actively being developed
    - The trajectory/direction of recent work
    - Frequently appearing topics and themes
    """
    recent_files: List[RecentFile]
    active_projects: List[Dict[str, Any]]
    work_trajectory: str
    hot_topics: List[str]
    hot_mentions: List[str]
    pending_todos: List[Dict[str, Any]]
    context_window_days: int
    built_at: datetime

    def to_prompt_context(self) -> str:
        """Format working context for inclusion in AI prompts."""
        lines = []

        # Active projects section
        if self.active_projects:
            lines.append("ACTIVE PROJECTS (by recent activity):")
            for proj in self.active_projects[:5]:
                lines.append(f"  - {proj['name']}: {proj['file_count']} files, "
                           f"activity score {proj['activity_score']:.1f}")
        else:
            lines.append("ACTIVE PROJECTS: None detected")

        lines.append("")

        # Work trajectory
        lines.append(f"RECENT FOCUS: {self.work_trajectory}")
        lines.append("")

        # Hot topics
        if self.hot_topics:
            lines.append(f"HOT TOPICS: {', '.join(self.hot_topics[:10])}")
        if self.hot_mentions:
            lines.append(f"FREQUENT MENTIONS: {', '.join(self.hot_mentions[:5])}")

        lines.append("")

        # Summary stats
        lines.append(f"ACTIVITY SUMMARY (last {self.context_window_days} days):")
        lines.append(f"  - {len(self.recent_files)} files modified")
        lines.append(f"  - {len(self.pending_todos)} pending todos across notes")

        return "\n".join(lines)


class WorkingContextService:
    """
    Service for building and managing working context.

    Analyzes recent file activity, entities, and patterns to create
    a contextual understanding of the user's current work focus.
    """

    # Recency decay thresholds (hours -> score)
    RECENCY_THRESHOLDS = [
        (24, 1.0),      # Last 24 hours
        (72, 0.7),      # 1-3 days
        (168, 0.4),     # 3-7 days
        (336, 0.2),     # 7-14 days
        (720, 0.1),     # 14-30 days
    ]

    def __init__(self):
        """Initialize the working context service."""
        self._cached_context: Optional[WorkingContext] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_minutes = 10  # Refresh context every 10 minutes

    def get_context_config(self) -> Dict[str, Any]:
        """Get the current context configuration."""
        return get_config()

    async def build_context(self, force_refresh: bool = False) -> WorkingContext:
        """
        Build or retrieve the working context.

        Args:
            force_refresh: If True, rebuild context even if cached

        Returns:
            WorkingContext with current work activity analysis
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.debug("Returning cached working context")
            return self._cached_context

        logger.info("Building new working context...")

        config = self.get_context_config()
        context_window_days = config.get('context_window_days', 14)

        # Step 1: Get recent files with recency scores
        recent_files = self._get_recent_files(context_window_days)

        # Step 2: Detect active projects from file clustering
        active_projects = self._detect_active_projects(recent_files)

        # Step 3: Extract hot topics (tags and themes)
        hot_topics, hot_mentions = self._extract_hot_topics(recent_files)

        # Step 4: Get pending todos
        pending_todos = self._get_pending_todos(context_window_days)

        # Step 5: Build work trajectory summary
        work_trajectory = self._build_trajectory_summary(
            recent_files, active_projects, hot_topics
        )

        context = WorkingContext(
            recent_files=recent_files,
            active_projects=active_projects,
            work_trajectory=work_trajectory,
            hot_topics=hot_topics,
            hot_mentions=hot_mentions,
            pending_todos=pending_todos,
            context_window_days=context_window_days,
            built_at=datetime.now()
        )

        # Update cache
        self._cached_context = context
        self._cache_timestamp = datetime.now()

        # Record that we built context
        update_last_context_build()

        logger.info(f"Built working context: {len(recent_files)} files, "
                   f"{len(active_projects)} projects, {len(pending_todos)} todos")

        return context

    def _is_cache_valid(self) -> bool:
        """Check if cached context is still valid."""
        if self._cached_context is None or self._cache_timestamp is None:
            return False
        age = datetime.now() - self._cache_timestamp
        return age.total_seconds() < (self._cache_ttl_minutes * 60)

    def _calculate_recency_score(self, last_modified: datetime) -> float:
        """
        Calculate recency score based on how recently a file was modified.

        More recent files get higher scores (1.0 max, 0.1 min).
        """
        now = datetime.now()
        age_hours = (now - last_modified).total_seconds() / 3600

        for threshold_hours, score in self.RECENCY_THRESHOLDS:
            if age_hours <= threshold_hours:
                return score

        return 0.05  # Very old files

    def _get_recent_files(self, context_window_days: int) -> List[RecentFile]:
        """Get files modified within the context window with recency scores."""
        try:
            cutoff = datetime.now() - timedelta(days=context_window_days)

            # Get recent files from file_states
            query = """
                SELECT fs.file_path, fs.last_modified
                FROM file_states fs
                WHERE fs.file_path LIKE '%.md'
                  AND fs.last_modified > ?
                ORDER BY fs.last_modified DESC
                LIMIT 200
            """
            results = db.execute_query(query, (cutoff.isoformat(),))

            recent_files = []
            for row in results:
                file_path = row['file_path']
                last_modified = row['last_modified']

                # Parse timestamp
                if isinstance(last_modified, str):
                    last_modified = datetime.fromisoformat(last_modified)

                recency_score = self._calculate_recency_score(last_modified)

                # Extract directory for project detection
                path_obj = Path(file_path)
                directory = str(path_obj.parent) if path_obj.parent != path_obj else ""

                # Get entities for this file
                tags, mentions, active_todos = self._get_file_entities(file_path)

                recent_files.append(RecentFile(
                    path=file_path,
                    last_modified=last_modified,
                    recency_score=recency_score,
                    directory=directory,
                    tags=tags,
                    mentions=mentions,
                    active_todos=active_todos
                ))

            return recent_files

        except Exception as e:
            logger.error(f"Failed to get recent files: {e}")
            return []

    def _get_file_entities(self, file_path: str) -> tuple:
        """Get tags, mentions, and todo count for a file."""
        try:
            # Get tags
            tag_query = """
                SELECT entity_value FROM note_entities
                WHERE note_path = ? AND entity_type = 'tag'
            """
            tag_results = db.execute_query(tag_query, (file_path,))
            tags = [row['entity_value'] for row in tag_results]

            # Get mentions
            mention_query = """
                SELECT entity_value FROM note_entities
                WHERE note_path = ? AND entity_type IN ('mention', 'person')
            """
            mention_results = db.execute_query(mention_query, (file_path,))
            mentions = [row['entity_value'] for row in mention_results]

            # Get active todo count
            todo_query = """
                SELECT COUNT(*) as cnt FROM note_entities
                WHERE note_path = ? AND entity_type = 'todo' AND status = 'active'
            """
            todo_result = db.execute_query(todo_query, (file_path,))
            active_todos = todo_result[0]['cnt'] if todo_result else 0

            return tags, mentions, active_todos

        except Exception as e:
            logger.warning(f"Failed to get entities for {file_path}: {e}")
            return [], [], 0

    def _detect_active_projects(self, recent_files: List[RecentFile]) -> List[Dict[str, Any]]:
        """
        Detect active projects by clustering files by directory.

        Projects are weighted by:
        - Number of files
        - Recency scores of files
        - Presence of project-related tags
        """
        project_scores = {}

        for file in recent_files:
            # Use top-level directory as project identifier
            parts = Path(file.directory).parts
            if not parts:
                project_name = "Root"
            else:
                # Use first meaningful directory level
                project_name = parts[0] if parts[0] not in ('.', '..') else (
                    parts[1] if len(parts) > 1 else "Root"
                )

            if project_name not in project_scores:
                project_scores[project_name] = {
                    'name': project_name,
                    'file_count': 0,
                    'total_recency': 0,
                    'files': [],
                    'tags': set()
                }

            project_scores[project_name]['file_count'] += 1
            project_scores[project_name]['total_recency'] += file.recency_score
            project_scores[project_name]['files'].append(file.path)
            project_scores[project_name]['tags'].update(file.tags)

        # Calculate activity scores
        projects = []
        for name, data in project_scores.items():
            activity_score = (
                data['file_count'] * 0.3 +
                data['total_recency'] * 0.7
            )
            projects.append({
                'name': name,
                'file_count': data['file_count'],
                'activity_score': round(activity_score, 2),
                'files': data['files'][:5],  # Top 5 files
                'tags': list(data['tags'])[:10]  # Top 10 tags
            })

        # Sort by activity score
        projects.sort(key=lambda x: x['activity_score'], reverse=True)

        return projects[:10]  # Top 10 projects

    def _extract_hot_topics(self, recent_files: List[RecentFile]) -> tuple:
        """Extract frequently appearing tags and mentions weighted by recency."""
        tag_counter = Counter()
        mention_counter = Counter()

        for file in recent_files:
            weight = file.recency_score

            for tag in file.tags:
                tag_counter[tag] += weight

            for mention in file.mentions:
                mention_counter[mention] += weight

        # Get top topics
        hot_topics = [tag for tag, _ in tag_counter.most_common(15)]
        hot_mentions = [mention for mention, _ in mention_counter.most_common(10)]

        return hot_topics, hot_mentions

    def _get_pending_todos(self, context_window_days: int) -> List[Dict[str, Any]]:
        """Get pending todos from recent notes."""
        try:
            cutoff = datetime.now() - timedelta(days=context_window_days)

            query = """
                SELECT ne.note_path, ne.entity_value, ne.context, ne.extracted_at,
                       fs.last_modified
                FROM note_entities ne
                JOIN file_states fs ON ne.note_path = fs.file_path
                WHERE ne.entity_type = 'todo'
                  AND ne.status = 'active'
                  AND fs.last_modified > ?
                ORDER BY fs.last_modified DESC
                LIMIT 50
            """
            results = db.execute_query(query, (cutoff.isoformat(),))

            todos = []
            for row in results:
                last_modified = row['last_modified']
                if isinstance(last_modified, str):
                    last_modified = datetime.fromisoformat(last_modified)

                todos.append({
                    'note_path': row['note_path'],
                    'todo_text': row['entity_value'],
                    'context': row['context'],
                    'recency_score': self._calculate_recency_score(last_modified),
                    'age_days': (datetime.now() - last_modified).days
                })

            return todos

        except Exception as e:
            logger.error(f"Failed to get pending todos: {e}")
            return []

    def _build_trajectory_summary(
        self,
        recent_files: List[RecentFile],
        active_projects: List[Dict[str, Any]],
        hot_topics: List[str]
    ) -> str:
        """
        Build a natural language summary of work trajectory.

        This describes what the user seems to be focusing on recently.
        """
        if not recent_files:
            return "No recent activity detected."

        parts = []

        # Describe recent activity level
        very_recent = len([f for f in recent_files if f.recency_score >= 0.7])
        if very_recent > 5:
            parts.append(f"High activity ({very_recent} files in the last few days)")
        elif very_recent > 0:
            parts.append(f"Moderate activity ({very_recent} recent files)")
        else:
            parts.append("Activity has slowed recently")

        # Describe project focus
        if active_projects:
            top_project = active_projects[0]
            parts.append(f"focused primarily on '{top_project['name']}'")

            if len(active_projects) > 1:
                secondary = [p['name'] for p in active_projects[1:3]]
                parts.append(f"with some work in {', '.join(secondary)}")

        # Describe topic trends
        if hot_topics:
            parts.append(f"involving themes like {', '.join(hot_topics[:3])}")

        return "; ".join(parts) + "."

    def invalidate_cache(self):
        """Force cache invalidation."""
        self._cached_context = None
        self._cache_timestamp = None
        logger.debug("Working context cache invalidated")


# Global service instance
_service_instance: Optional[WorkingContextService] = None


def get_working_context_service() -> WorkingContextService:
    """Get the global working context service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = WorkingContextService()
    return _service_instance
