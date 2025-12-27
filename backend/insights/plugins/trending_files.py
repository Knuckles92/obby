"""
Trending Files Insight Plugin

Identifies the most frequently modified files and tracks
which files are receiving the most attention.
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
import logging
from pathlib import Path

from ..base import BaseInsight, InsightCategory, InsightMetadata, InsightSize
from database.queries import FileQueries

logger = logging.getLogger(__name__)


class TrendingFilesInsight(BaseInsight):
    """
    Tracks files with the most activity and change frequency.
    """

    def get_metadata(self) -> InsightMetadata:
        return InsightMetadata(
            id="trending_files",
            title="Trending Files",
            description="Most frequently modified files in the time period",
            icon="TrendingUp",
            color="var(--color-success)",
            category=InsightCategory.TRENDS,
            default_size=InsightSize.LARGE,
            supports_drill_down=True
        )

    def calculate(
        self,
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate trending files based on modification frequency.

        Returns:
            {
                "value": <number of trending files>,
                "label": "trending files",
                "details": {
                    "topFiles": [
                        {
                            "path": <file path>,
                            "name": <file name>,
                            "changeCount": <number of changes>,
                            "linesAdded": <lines added>,
                            "linesRemoved": <lines removed>,
                            "lastModified": <timestamp>
                        },
                        ...
                    ]
                },
                "chart": {
                    "type": "list",
                    "data": [...]
                }
            }
        """
        try:
            # Get comprehensive analysis for the time range
            analysis = FileQueries.get_comprehensive_time_analysis(
                start_time=start_date,
                end_time=end_date,
                watch_handler=None
            )

            file_metrics = analysis.get('fileMetrics', [])

            if not file_metrics:
                return {
                    "value": "0",
                    "label": "trending files",
                    "status": "warning",
                    "message": "No file activity detected in this time range"
                }

            # Process top files (already sorted by change_count in query)
            top_files = []
            for metric in file_metrics[:10]:  # Top 10 files
                file_path = metric['file_path']
                path_obj = Path(file_path)

                top_files.append({
                    "path": file_path,
                    "name": path_obj.name,
                    "directory": str(path_obj.parent) if path_obj.parent != Path('.') else "",
                    "changeCount": metric['change_count'],
                    "linesAdded": metric['total_lines_added'] or 0,
                    "linesRemoved": metric['total_lines_removed'] or 0,
                    "netChange": (metric['total_lines_added'] or 0) - (metric['total_lines_removed'] or 0),
                    "lastModified": metric['last_modified'],
                    "firstModified": metric['first_modified']
                })

            # Calculate file extension distribution
            extension_counts = {}
            for metric in file_metrics:
                file_path = metric['file_path']
                ext = Path(file_path).suffix or 'no extension'
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

            # Sort extensions by count
            top_extensions = sorted(
                extension_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            return {
                "value": str(len(file_metrics)),
                "label": "active files" if len(file_metrics) != 1 else "active file",
                "details": {
                    "topExtensions": [
                        f"{ext} ({count})"
                        for ext, count in top_extensions
                    ],
                    "totalFilesModified": len(file_metrics)
                },
                "chart": {
                    "type": "list",
                    "data": top_files[:5]  # Top 5 for chart visualization
                },
                "status": "success",
                "message": f"Tracking {len(file_metrics)} modified files"
            }

        except Exception as e:
            logger.error(f"Error calculating trending files insight: {e}")
            return {
                "value": "0",
                "label": "trending files",
                "status": "error",
                "message": f"Error calculating trending files: {str(e)}"
            }
