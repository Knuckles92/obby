"""
Peak Activity Insight Plugin

Identifies the most active time periods (hours, days) based on
file changes and activity patterns.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from collections import defaultdict
import logging

from ..base import BaseInsight, InsightCategory, InsightMetadata, InsightSize
from database.queries import FileQueries

logger = logging.getLogger(__name__)


class PeakActivityInsight(BaseInsight):
    """
    Analyzes activity patterns to identify peak activity times.
    """

    def get_metadata(self) -> InsightMetadata:
        return InsightMetadata(
            id="peak_activity",
            title="Peak Activity",
            description="Most active time periods during the day",
            icon="Zap",
            color="var(--color-accent)",
            category=InsightCategory.TRENDS,
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
        Calculate peak activity periods.

        Returns:
            {
                "value": <peak hour, e.g., "3 PM">,
                "label": "peak hour",
                "chart": {
                    "type": "bar",
                    "data": [
                        {"hour": "12 AM", "value": 5},
                        ...
                    ]
                },
                "details": {
                    "peakDay": <most active day>,
                    "totalHoursActive": <number of hours with activity>,
                    "activityDistribution": {...}
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

            diffs = analysis.get('diffs', [])

            if not diffs:
                return {
                    "value": "N/A",
                    "label": "peak hour",
                    "status": "warning",
                    "message": "No activity detected in this time range"
                }

            # Group changes by hour of day
            hourly_activity = defaultdict(int)
            daily_activity = defaultdict(int)

            for diff in diffs:
                try:
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(diff['timestamp'].replace('Z', '+00:00'))

                    # Track by hour (0-23)
                    hour = timestamp.hour
                    hourly_activity[hour] += 1

                    # Track by day of week (0=Monday, 6=Sunday)
                    day = timestamp.strftime('%A')
                    daily_activity[day] += 1

                except Exception as e:
                    logger.warning(f"Error parsing timestamp {diff.get('timestamp')}: {e}")
                    continue

            # Find peak hour
            peak_hour = max(hourly_activity.items(), key=lambda x: x[1]) if hourly_activity else (0, 0)
            peak_hour_num, peak_hour_count = peak_hour

            # Format peak hour as 12-hour time
            peak_hour_formatted = datetime.strptime(f"{peak_hour_num}", "%H").strftime("%I %p").lstrip('0')

            # Find peak day
            peak_day = max(daily_activity.items(), key=lambda x: x[1]) if daily_activity else ("N/A", 0)
            peak_day_name, peak_day_count = peak_day

            # Prepare hourly chart data
            chart_data = []
            for hour in range(24):
                hour_label = datetime.strptime(f"{hour}", "%H").strftime("%I %p").lstrip('0')
                chart_data.append({
                    "hour": hour_label,
                    "value": hourly_activity.get(hour, 0),
                    "percentage": int((hourly_activity.get(hour, 0) / len(diffs)) * 100) if diffs else 0
                })

            # Calculate active hours (hours with any activity)
            active_hours = len([h for h in hourly_activity.values() if h > 0])

            return {
                "value": peak_hour_formatted,
                "label": "peak hour",
                "chart": {
                    "type": "bar",
                    "data": chart_data
                },
                "details": {
                    "peakDay": peak_day_name,
                    "peakDayCount": peak_day_count,
                    "totalHoursActive": active_hours,
                    "peakHourCount": peak_hour_count,
                    "activityDistribution": {
                        day: count for day, count in daily_activity.items()
                    }
                },
                "status": "success",
                "message": f"Peak activity at {peak_hour_formatted} with {peak_hour_count} changes"
            }

        except Exception as e:
            logger.error(f"Error calculating peak activity insight: {e}")
            return {
                "value": "Error",
                "label": "peak hour",
                "status": "error",
                "message": f"Error calculating peak activity: {str(e)}"
            }
