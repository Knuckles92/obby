"""
Stale Todos Insight Plugin
==========================

Finds action items (todos) that haven't been completed or referenced
for a configurable number of days.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from ..base import BaseInsight, InsightCategory, InsightMetadata, InsightSize
from database.models import db

logger = logging.getLogger(__name__)


class StaleTodosInsight(BaseInsight):
    """
    Find todos not completed or referenced since X days.

    Queries the note_entities table for active todos and identifies
    ones that are older than a configurable threshold.
    """

    def get_metadata(self) -> InsightMetadata:
        return InsightMetadata(
            id="stale_todos",
            title="Stale Action Items",
            description="Todos and tasks that haven't been addressed recently",
            icon="Clock",
            color="var(--color-amber)",
            category=InsightCategory.SEMANTIC,
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
        Calculate stale todos for the time range.

        Config options:
            - days_threshold: Number of days before a todo is considered stale (default: 7)
            - max_items: Maximum items to return (default: 10)

        Returns:
            {
                "value": <count of stale todos>,
                "label": "stale items",
                "items": [...],
                "status": "success" | "warning" | "error"
            }
        """
        config = config or {}
        days_threshold = config.get('days_threshold', 7)
        max_items = config.get('max_items', 10)

        try:
            threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()

            # Query for stale todos
            query = """
                SELECT
                    ne.id,
                    ne.note_path,
                    ne.entity_value,
                    ne.context,
                    ne.line_number,
                    ne.extracted_at,
                    sps.last_entity_extraction
                FROM note_entities ne
                LEFT JOIN semantic_processing_state sps ON ne.note_path = sps.note_path
                WHERE ne.entity_type = 'todo'
                  AND ne.status = 'active'
                  AND ne.extracted_at < ?
                ORDER BY ne.extracted_at ASC
                LIMIT ?
            """
            stale_todos = db.execute_query(query, (threshold_date, max_items))

            # Get total count
            count_query = """
                SELECT COUNT(*) as count
                FROM note_entities
                WHERE entity_type = 'todo'
                  AND status = 'active'
                  AND extracted_at < ?
            """
            count_result = db.execute_query(count_query, (threshold_date,))
            total_count = count_result[0]['count'] if count_result else 0

            # Format items for display
            items = []
            for todo in stale_todos:
                days_old = (datetime.now() - datetime.fromisoformat(todo['extracted_at'])).days
                items.append({
                    'id': todo['id'],
                    'text': todo['entity_value'][:100],
                    'notePath': todo['note_path'],
                    'lineNumber': todo.get('line_number'),
                    'context': todo.get('context', '')[:150],
                    'daysOld': days_old,
                    'extractedAt': todo['extracted_at']
                })

            # Determine status
            status = "success"
            message = f"No stale action items found"
            if total_count > 0:
                status = "warning"
                message = f"Found {total_count} action items older than {days_threshold} days"

            return {
                "value": total_count,
                "label": "stale items" if total_count != 1 else "stale item",
                "trend": "up" if total_count > 5 else "stable",
                "items": items,
                "details": {
                    "daysThreshold": days_threshold,
                    "totalFound": total_count,
                    "showing": len(items)
                },
                "status": status,
                "message": message,
                "chart": self._build_age_chart(stale_todos) if items else None
            }

        except Exception as e:
            logger.error(f"Error calculating stale todos insight: {e}")
            return {
                "value": 0,
                "label": "stale items",
                "status": "error",
                "message": f"Error: {str(e)}"
            }

    def _build_age_chart(self, todos: List[Dict]) -> Optional[Dict[str, Any]]:
        """Build a chart showing todo age distribution."""
        if not todos:
            return None

        # Group by age buckets
        buckets = {'1 week': 0, '2 weeks': 0, '1 month': 0, '1+ month': 0}

        for todo in todos:
            try:
                days = (datetime.now() - datetime.fromisoformat(todo['extracted_at'])).days
                if days <= 7:
                    buckets['1 week'] += 1
                elif days <= 14:
                    buckets['2 weeks'] += 1
                elif days <= 30:
                    buckets['1 month'] += 1
                else:
                    buckets['1+ month'] += 1
            except Exception:
                pass

        return {
            "type": "bar",
            "data": [{"label": k, "value": v} for k, v in buckets.items() if v > 0]
        }

    def get_schema(self) -> Dict[str, Any]:
        """Return the expected data schema for this insight."""
        return {
            "value": "number",
            "label": "string",
            "items": [{
                "id": "number",
                "text": "string",
                "notePath": "string",
                "lineNumber": "number?",
                "context": "string?",
                "daysOld": "number",
                "extractedAt": "string"
            }],
            "details": {
                "daysThreshold": "number",
                "totalFound": "number",
                "showing": "number"
            },
            "chart": "object?",
            "status": "'success' | 'warning' | 'error'",
            "message": "string"
        }
