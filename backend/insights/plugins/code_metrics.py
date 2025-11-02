"""
Code Metrics Insight Plugin

Analyzes code changes including lines added/removed, change size
distribution, and code churn metrics.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import logging

from ..base import BaseInsight, InsightCategory, InsightMetadata, InsightSize
from database.queries import FileQueries

logger = logging.getLogger(__name__)


class CodeMetricsInsight(BaseInsight):
    """
    Tracks code-level metrics like lines changed, change size, and churn.
    """

    def get_metadata(self) -> InsightMetadata:
        return InsightMetadata(
            id="code_metrics",
            title="Lines Changed",
            description="Lines added and removed across all files",
            icon="Code",
            color="var(--color-info)",
            category=InsightCategory.CODE,
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
        Calculate code metrics.

        Returns:
            {
                "value": <net lines changed>,
                "label": "lines changed",
                "trend": "up" | "down" | "stable",
                "details": {
                    "linesAdded": <total lines added>,
                    "linesRemoved": <total lines removed>,
                    "netChange": <net change>,
                    "averageChangeSize": <average lines per change>,
                    "changeSizeDistribution": {
                        "small": <count of changes < 10 lines>,
                        "medium": <count of changes 10-100 lines>,
                        "large": <count of changes > 100 lines>
                    }
                },
                "chart": {
                    "type": "comparison",
                    "data": {
                        "added": <lines added>,
                        "removed": <lines removed>
                    }
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

            summary = analysis.get('summary', {})
            diffs = analysis.get('diffs', [])

            lines_added = summary.get('linesAdded', 0)
            lines_removed = summary.get('linesRemoved', 0)
            net_change = summary.get('netLinesChanged', 0)
            total_changes = summary.get('totalChanges', 0)

            if total_changes == 0:
                return {
                    "value": "0",
                    "label": "lines changed",
                    "status": "warning",
                    "message": "No code changes detected in this time range"
                }

            # Calculate average change size
            average_change_size = (lines_added + lines_removed) / total_changes if total_changes > 0 else 0

            # Calculate change size distribution
            size_distribution = {
                "small": 0,    # < 10 lines
                "medium": 0,   # 10-100 lines
                "large": 0     # > 100 lines
            }

            for diff in diffs:
                change_size = (diff.get('linesAdded', 0) or 0) + (diff.get('linesRemoved', 0) or 0)
                if change_size < 10:
                    size_distribution["small"] += 1
                elif change_size <= 100:
                    size_distribution["medium"] += 1
                else:
                    size_distribution["large"] += 1

            # Determine trend (positive net change = up, negative = down)
            trend = "stable"
            if net_change > 10:
                trend = "up"
            elif net_change < -10:
                trend = "down"

            # Format the primary value
            net_change_formatted = f"+{net_change:,}" if net_change >= 0 else f"{net_change:,}"

            return {
                "value": net_change_formatted,
                "label": "lines net change",
                "trend": trend,
                "trendValue": net_change,
                "details": {
                    "linesAdded": lines_added,
                    "linesRemoved": lines_removed,
                    "netChange": net_change,
                    "averageChangeSize": round(average_change_size, 1),
                    "changeSizeDistribution": size_distribution,
                    "totalChanges": total_changes
                },
                "chart": {
                    "type": "comparison",
                    "data": {
                        "added": lines_added,
                        "removed": lines_removed,
                        "net": net_change
                    }
                },
                "status": "success",
                "message": f"{lines_added:,} lines added, {lines_removed:,} removed"
            }

        except Exception as e:
            logger.error(f"Error calculating code metrics insight: {e}")
            return {
                "value": "0",
                "label": "lines changed",
                "status": "error",
                "message": f"Error calculating code metrics: {str(e)}"
            }
