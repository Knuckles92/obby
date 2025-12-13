"""
Orphan Mentions Insight Plugin
==============================

Finds people, projects, or topics mentioned only once and never
referenced again - potentially forgotten follow-ups.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from ..base import BaseInsight, InsightCategory, InsightMetadata, InsightSize
from database.models import db

logger = logging.getLogger(__name__)


class OrphanMentionsInsight(BaseInsight):
    """
    Find mentions that appear only once across all notes.

    Identifies @mentions, [[links]], and #tags that were used once
    and never referenced again - potential forgotten follow-ups.
    """

    def get_metadata(self) -> InsightMetadata:
        return InsightMetadata(
            id="orphan_mentions",
            title="Orphaned Mentions",
            description="People, projects, or topics mentioned once and dropped",
            icon="UserX",
            color="var(--color-rose)",
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
        Calculate orphaned mentions for the time range.

        Config options:
            - days_recent: Exclude mentions newer than X days (default: 3)
            - entity_types: List of entity types to check (default: mention, person, link, tag)
            - max_items: Maximum items to return (default: 10)

        Returns:
            {
                "value": <count of orphan mentions>,
                "label": "orphaned mentions",
                "items": [...],
                "status": "success" | "warning" | "error"
            }
        """
        config = config or {}
        days_recent = config.get('days_recent', 3)
        entity_types = config.get('entity_types', ['mention', 'person', 'link', 'tag'])
        max_items = config.get('max_items', 10)

        try:
            recent_threshold = (datetime.now() - timedelta(days=days_recent)).isoformat()

            # Build entity types filter
            type_placeholders = ','.join(['?' for _ in entity_types])

            # Query for orphaned mentions (entities that appear only once)
            query = f"""
                SELECT
                    entity_type,
                    entity_value,
                    MIN(note_path) as note_path,
                    MIN(context) as context,
                    MIN(line_number) as line_number,
                    MIN(extracted_at) as extracted_at,
                    COUNT(*) as occurrence_count
                FROM note_entities
                WHERE entity_type IN ({type_placeholders})
                  AND extracted_at < ?
                GROUP BY entity_type, entity_value
                HAVING occurrence_count = 1
                ORDER BY extracted_at DESC
                LIMIT ?
            """
            params = tuple(entity_types) + (recent_threshold, max_items)
            orphans = db.execute_query(query, params)

            # Get total count
            count_query = f"""
                SELECT COUNT(*) as count FROM (
                    SELECT entity_value
                    FROM note_entities
                    WHERE entity_type IN ({type_placeholders})
                      AND extracted_at < ?
                    GROUP BY entity_type, entity_value
                    HAVING COUNT(*) = 1
                )
            """
            count_params = tuple(entity_types) + (recent_threshold,)
            count_result = db.execute_query(count_query, count_params)
            total_count = count_result[0]['count'] if count_result else 0

            # Format items for display
            items = []
            for orphan in orphans:
                days_old = (datetime.now() - datetime.fromisoformat(orphan['extracted_at'])).days
                items.append({
                    'entityType': orphan['entity_type'],
                    'value': orphan['entity_value'],
                    'notePath': orphan['note_path'],
                    'lineNumber': orphan.get('line_number'),
                    'context': orphan.get('context', '')[:150],
                    'daysOld': days_old,
                    'extractedAt': orphan['extracted_at']
                })

            # Group by entity type for summary
            by_type = {}
            for item in items:
                t = item['entityType']
                by_type[t] = by_type.get(t, 0) + 1

            # Determine status
            status = "success"
            message = "No orphaned mentions found"
            if total_count > 0:
                status = "warning" if total_count > 5 else "success"
                message = f"Found {total_count} one-time mentions that might need follow-up"

            return {
                "value": total_count,
                "label": "orphaned mentions" if total_count != 1 else "orphaned mention",
                "trend": "stable",
                "items": items,
                "details": {
                    "daysRecent": days_recent,
                    "totalFound": total_count,
                    "showing": len(items),
                    "byType": by_type
                },
                "status": status,
                "message": message,
                "chart": self._build_type_chart(by_type) if by_type else None
            }

        except Exception as e:
            logger.error(f"Error calculating orphan mentions insight: {e}")
            return {
                "value": 0,
                "label": "orphaned mentions",
                "status": "error",
                "message": f"Error: {str(e)}"
            }

    def _build_type_chart(self, by_type: Dict[str, int]) -> Optional[Dict[str, Any]]:
        """Build a chart showing orphan distribution by type."""
        if not by_type:
            return None

        # Map entity types to display names
        display_names = {
            'mention': '@mentions',
            'person': 'People',
            'link': '[[Links]]',
            'tag': '#Tags',
            'project': 'Projects',
            'concept': 'Concepts'
        }

        return {
            "type": "bar",
            "data": [
                {"label": display_names.get(k, k), "value": v}
                for k, v in sorted(by_type.items(), key=lambda x: -x[1])
            ]
        }

    def get_schema(self) -> Dict[str, Any]:
        """Return the expected data schema for this insight."""
        return {
            "value": "number",
            "label": "string",
            "items": [{
                "entityType": "string",
                "value": "string",
                "notePath": "string",
                "lineNumber": "number?",
                "context": "string?",
                "daysOld": "number",
                "extractedAt": "string"
            }],
            "details": {
                "daysRecent": "number",
                "totalFound": "number",
                "showing": "number",
                "byType": "object"
            },
            "chart": "object?",
            "status": "'success' | 'warning' | 'error'",
            "message": "string"
        }
