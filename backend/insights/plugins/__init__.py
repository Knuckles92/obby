"""
Insight plugin implementations.

Each plugin calculates a specific type of insight based on monitored file data.
"""

from .file_activity import FileActivityInsight
from .peak_activity import PeakActivityInsight
from .trending_files import TrendingFilesInsight
from .code_metrics import CodeMetricsInsight

__all__ = [
    "FileActivityInsight",
    "PeakActivityInsight",
    "TrendingFilesInsight",
    "CodeMetricsInsight",
]
