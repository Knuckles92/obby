"""
File Activity Insight Plugin

Calculates total file changes, modifications, and activity metrics
for a given time period.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import logging

from ..base import BaseInsight, InsightCategory, InsightMetadata, InsightSize
from database.queries import FileQueries

logger = logging.getLogger(__name__)


class FileActivityInsight(BaseInsight):
    """
    Tracks overall file activity including total changes,
    files modified, and change distribution.
    """

    def get_metadata(self) -> InsightMetadata:
        return InsightMetadata(
            id="file_activity",
            title="Total Changes",
            description="Total file changes and activity in the time period",
            icon="Activity",
            color="var(--color-primary)",
            category=InsightCategory.ACTIVITY,
            default_size=InsightSize.MEDIUM,
            supports_drill_down=True
        )

    def calculate(
        self,
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate file activity metrics for the time range.

        Returns:
            {
                "value": <total number of changes>,
                "label": "changes",
                "trend": "up" | "down" | "stable",
                "trendValue": <percentage change from previous period>,
                "details": {
                    "filesModified": <number of unique files>,
                    "changeTypes": {
                        "modified": <count>,
                        "created": <count>,
                        "deleted": <count>
                    }
                },
                "status": "success" | "warning" | "error"
            }
        """
        try:
            # Get comprehensive analysis for the time range
            analysis = FileQueries.get_comprehensive_time_analysis(
                start_time=start_date,
                end_time=end_date,
                watch_handler=None  # Will auto-initialize with strict filtering
            )

            summary = analysis.get('summary', {})
            total_changes = summary.get('totalChanges', 0)
            files_affected = summary.get('filesAffected', 0)
            change_types = summary.get('changeTypes', {})

            # Calculate trend by comparing with previous period
            period_duration = end_date - start_date
            previous_start = start_date - period_duration
            previous_analysis = FileQueries.get_comprehensive_time_analysis(
                start_time=previous_start,
                end_time=start_date,
                watch_handler=None
            )
            previous_total = previous_analysis.get('summary', {}).get('totalChanges', 0)

            # Calculate trend
            trend = "stable"
            trend_value = 0.0
            if previous_total > 0:
                trend_value = ((total_changes - previous_total) / previous_total) * 100
                if trend_value > 5:
                    trend = "up"
                elif trend_value < -5:
                    trend = "down"

            # Determine status based on activity level
            status = "success"
            if total_changes == 0:
                status = "warning"

            return {
                "value": f"{total_changes:,}",
                "label": "changes" if total_changes != 1 else "change",
                "trend": trend,
                "trendValue": round(trend_value, 1),
                "details": {
                    "filesModified": files_affected,
                    "changeTypes": {
                        "modified": change_types.get('modified', 0),
                        "created": change_types.get('created', 0),
                        "deleted": change_types.get('deleted', 0)
                    },
                    "linesAdded": summary.get('linesAdded', 0),
                    "linesRemoved": summary.get('linesRemoved', 0),
                    "netLinesChanged": summary.get('netLinesChanged', 0)
                },
                "status": status,
                "message": f"Tracked {files_affected} files with {total_changes} changes"
            }

        except Exception as e:
            logger.error(f"Error calculating file activity insight: {e}")
            return {
                "value": "0",
                "label": "changes",
                "status": "error",
                "message": f"Error calculating activity: {str(e)}"
            }
