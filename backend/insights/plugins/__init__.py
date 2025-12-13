"""
Insight plugin implementations.

Each plugin calculates a specific type of insight based on monitored file data.

Activity Plugins (Tier 1):
- FileActivityInsight: Total file changes and activity
- PeakActivityInsight: Peak activity hours and days
- TrendingFilesInsight: Most frequently changed files
- CodeMetricsInsight: Code quality metrics

Semantic Plugins (Tier 2):
- StaleTodosInsight: Todos not addressed recently
- OrphanMentionsInsight: One-time mentions that might need follow-up
"""

from .file_activity import FileActivityInsight
from .peak_activity import PeakActivityInsight
from .trending_files import TrendingFilesInsight
from .code_metrics import CodeMetricsInsight
from .stale_todos import StaleTodosInsight
from .orphan_mentions import OrphanMentionsInsight

__all__ = [
    # Activity plugins
    "FileActivityInsight",
    "PeakActivityInsight",
    "TrendingFilesInsight",
    "CodeMetricsInsight",
    # Semantic plugins
    "StaleTodosInsight",
    "OrphanMentionsInsight",
]
