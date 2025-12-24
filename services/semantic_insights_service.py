"""
Semantic Insights Service
=========================

Service layer for managing semantic insights:
- CRUD operations on semantic_insights table
- User actions (dismiss, pin, mark_done)
- Statistics and filtering
- Processing trigger and status
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from database.models import db

logger = logging.getLogger(__name__)


class SemanticInsightsService:
    """
    Service layer for semantic insights operations.

    Provides methods for:
    - Retrieving insights with filtering
    - Performing user actions on insights
    - Getting statistics
    - Triggering processing
    """

    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize the semantic insights service.

        Args:
            working_dir: Base directory for file operations
        """
        self.working_dir = working_dir or Path.cwd()
        self._scheduler = None

    @property
    def scheduler(self):
        """Lazy load the scheduler to avoid circular imports."""
        if self._scheduler is None:
            from backend.semantic.scheduler import get_semantic_scheduler
            self._scheduler = get_semantic_scheduler(working_dir=self.working_dir)
        return self._scheduler

    def get_insights(
        self,
        insight_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get semantic insights with optional filtering.

        Args:
            insight_type: Filter by insight type (e.g., 'stale_todo', 'orphan_mention')
            status: Filter by status (e.g., 'new', 'viewed', 'dismissed', 'pinned')
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Dict with insights list and metadata
        """
        try:
            # Build query conditions
            conditions = []
            params = []

            if insight_type:
                conditions.append("insight_type = ?")
                params.append(insight_type)

            if status:
                conditions.append("status = ?")
                params.append(status)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get insights
            query = f"""
                SELECT *
                FROM semantic_insights
                WHERE {where_clause}
                ORDER BY
                    CASE status
                        WHEN 'pinned' THEN 0
                        WHEN 'new' THEN 1
                        WHEN 'viewed' THEN 2
                        ELSE 3
                    END,
                    priority DESC,
                    created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            results = db.execute_query(query, tuple(params))

            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM semantic_insights
                WHERE {where_clause}
            """
            count_params = params[:-2]  # Exclude limit and offset
            count_result = db.execute_query(count_query, tuple(count_params) if count_params else ())
            total = count_result[0]['total'] if count_result else 0

            # Format insights
            insights = []
            for row in results:
                insight = self._format_insight(row)
                insights.append(insight)

            # Get counts by type and status
            meta = self._get_meta_stats()

            return {
                "insights": insights,
                "meta": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    **meta
                }
            }

        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            return {"insights": [], "meta": {"total": 0, "error": str(e)}}

    def get_insight_by_id(self, insight_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single insight by ID.

        Args:
            insight_id: The insight ID

        Returns:
            Insight dict or None if not found
        """
        try:
            result = db.execute_query(
                "SELECT * FROM semantic_insights WHERE id = ?",
                (insight_id,)
            )
            if result:
                # Mark as viewed if new
                if result[0]['status'] == 'new':
                    db.execute_update(
                        "UPDATE semantic_insights SET status = 'viewed', viewed_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), insight_id)
                    )
                return self._format_insight(result[0])
            return None

        except Exception as e:
            logger.error(f"Error getting insight {insight_id}: {e}")
            return None

    def perform_action(
        self,
        insight_id: int,
        action: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform a user action on an insight.

        Args:
            insight_id: The insight ID
            action: Action to perform (dismiss, pin, unpin, mark_done, open_note)
            data: Optional additional data for the action

        Returns:
            Result dict with success status
        """
        try:
            valid_actions = ['dismiss', 'pin', 'unpin', 'mark_done', 'open_note', 'restore']

            if action not in valid_actions:
                return {"success": False, "error": f"Invalid action: {action}"}

            # Get current insight
            insight = db.execute_query(
                "SELECT * FROM semantic_insights WHERE id = ?",
                (insight_id,)
            )
            if not insight:
                return {"success": False, "error": "Insight not found"}

            # Perform action
            if action == 'dismiss':
                db.execute_update(
                    "UPDATE semantic_insights SET status = 'dismissed', user_action = ? WHERE id = ?",
                    (f'dismissed:{datetime.now().isoformat()}', insight_id)
                )

            elif action == 'pin':
                db.execute_update(
                    "UPDATE semantic_insights SET status = 'pinned', user_action = ? WHERE id = ?",
                    (f'pinned:{datetime.now().isoformat()}', insight_id)
                )

            elif action == 'unpin':
                db.execute_update(
                    "UPDATE semantic_insights SET status = 'viewed', user_action = ? WHERE id = ?",
                    (f'unpinned:{datetime.now().isoformat()}', insight_id)
                )

            elif action == 'restore':
                db.execute_update(
                    "UPDATE semantic_insights SET status = 'new', user_action = ? WHERE id = ?",
                    (f'restored:{datetime.now().isoformat()}', insight_id)
                )

            elif action == 'mark_done':
                # Mark the insight as actioned
                db.execute_update(
                    "UPDATE semantic_insights SET status = 'actioned', user_action = ? WHERE id = ?",
                    (f'marked_done:{datetime.now().isoformat()}', insight_id)
                )
                # Also update the underlying entity if it's a todo
                self._mark_todo_done(insight[0])

            elif action == 'open_note':
                # Just record the action (actual navigation happens in frontend)
                db.execute_update(
                    "UPDATE semantic_insights SET user_action = ? WHERE id = ?",
                    (f'opened_note:{datetime.now().isoformat()}', insight_id)
                )

            logger.info(f"Performed action '{action}' on insight {insight_id}")
            return {"success": True, "action": action, "insight_id": insight_id}

        except Exception as e:
            logger.error(f"Error performing action on insight {insight_id}: {e}")
            return {"success": False, "error": str(e)}

    def _mark_todo_done(self, insight: Dict[str, Any]):
        """Mark the underlying todo entity as completed."""
        try:
            if insight.get('insight_type') != 'stale_todo':
                return

            evidence = json.loads(insight.get('evidence', '{}'))
            source_notes = json.loads(insight.get('source_notes', '[]'))

            if source_notes:
                note_path = source_notes[0].get('path')
                todo_text = evidence.get('todo_text')

                if note_path and todo_text:
                    db.execute_update("""
                        UPDATE note_entities
                        SET status = 'completed', updated_at = ?
                        WHERE note_path = ?
                          AND entity_type = 'todo'
                          AND entity_value = ?
                    """, (datetime.now().isoformat(), note_path, todo_text))

        except Exception as e:
            logger.warning(f"Could not mark todo as done: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about semantic insights.

        Returns:
            Dict with various stats
        """
        try:
            # Counts by type
            type_counts = db.execute_query("""
                SELECT insight_type, COUNT(*) as count
                FROM semantic_insights
                WHERE status NOT IN ('dismissed', 'actioned')
                GROUP BY insight_type
            """)

            # Counts by status
            status_counts = db.execute_query("""
                SELECT status, COUNT(*) as count
                FROM semantic_insights
                GROUP BY status
            """)

            # New insights count
            new_count = db.execute_query("""
                SELECT COUNT(*) as count
                FROM semantic_insights
                WHERE status = 'new'
            """)

            # Entity stats
            entity_counts = db.execute_query("""
                SELECT entity_type, COUNT(*) as count
                FROM note_entities
                GROUP BY entity_type
            """)

            return {
                "byType": {r['insight_type']: r['count'] for r in type_counts},
                "byStatus": {r['status']: r['count'] for r in status_counts},
                "newCount": new_count[0]['count'] if new_count else 0,
                "entityCounts": {r['entity_type']: r['count'] for r in entity_counts}
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    async def trigger_processing(self) -> Dict[str, Any]:
        """
        Trigger a manual processing run.

        Returns:
            Processing status
        """
        try:
            result = await self.scheduler.trigger_manual_run()
            return result

        except Exception as e:
            logger.error(f"Error triggering processing: {e}")
            return {"error": str(e)}

    def get_processing_status(self) -> Dict[str, Any]:
        """
        Get current processing status.

        Returns:
            Status dict with scheduler info
        """
        try:
            return self.scheduler.get_status()
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return {"error": str(e)}

    def _format_insight(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Format a database row as an insight dict."""
        # Convert sqlite3.Row to dict for .get() support
        row = dict(row)

        try:
            source_notes = json.loads(row.get('source_notes', '[]'))
            evidence = json.loads(row.get('evidence', '{}'))
        except json.JSONDecodeError:
            source_notes = []
            evidence = {}

        return {
            "id": row['id'],
            "type": row['insight_type'],
            "title": row['title'],
            "summary": row['summary'],
            "confidence": row.get('confidence', 1.0),
            "priority": row.get('priority', 0),
            "status": row['status'],
            "sourceNotes": source_notes,
            "evidence": evidence,
            "actions": self._get_available_actions(row['insight_type'], row['status']),
            "createdAt": row['created_at'],
            "viewedAt": row.get('viewed_at'),
            "userAction": row.get('user_action')
        }

    def _get_available_actions(self, insight_type: str, status: str) -> List[str]:
        """Get available actions for an insight based on type and status."""
        actions = ['open_note']

        if status == 'pinned':
            actions.append('unpin')
        elif status != 'dismissed':
            actions.append('pin')

        if status != 'dismissed':
            actions.append('dismiss')

        if status == 'dismissed':
            actions.append('restore')

        if insight_type == 'stale_todo' and status not in ('dismissed', 'actioned'):
            actions.append('mark_done')

        return actions

    def _get_meta_stats(self) -> Dict[str, Any]:
        """Get counts by type and status for metadata."""
        try:
            type_counts = db.execute_query("""
                SELECT insight_type, COUNT(*) as count
                FROM semantic_insights
                WHERE status NOT IN ('dismissed', 'actioned')
                GROUP BY insight_type
            """)

            status_counts = db.execute_query("""
                SELECT status, COUNT(*) as count
                FROM semantic_insights
                GROUP BY status
            """)

            return {
                "byType": {r['insight_type']: r['count'] for r in type_counts},
                "byStatus": {r['status']: r['count'] for r in status_counts}
            }
        except Exception:
            return {"byType": {}, "byStatus": {}}

    async def generate_suggested_actions(self, insight_id: int) -> Dict[str, Any]:
        """
        Generate AI-suggested actions for a todo insight.
        Returns cached actions if they exist, otherwise generates new ones.
        
        Args:
            insight_id: The insight ID
            
        Returns:
            Dict with success status and list of suggested actions
        """
        try:
            # Get the insight
            insight = db.execute_query(
                "SELECT * FROM semantic_insights WHERE id = ?",
                (insight_id,)
            )
            
            if not insight:
                return {"success": False, "error": "Insight not found"}
            
            insight_row = dict(insight[0])
            insight_type = insight_row.get('insight_type')
            
            # Only generate actions for todo-type insights
            if insight_type not in ('stale_todo', 'active_todos'):
                return {"success": False, "error": "Suggested actions only available for todo insights"}
            
            # Check if cached suggested actions exist
            cached_actions = insight_row.get('suggested_actions')
            if cached_actions:
                try:
                    actions = json.loads(cached_actions)
                    if isinstance(actions, list) and len(actions) > 0:
                        logger.info(f"Returning cached suggested actions for insight {insight_id}")
                        return {
                            "success": True,
                            "actions": actions,
                            "cached": True
                        }
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse cached suggested actions for insight {insight_id}, regenerating")
            
            # Parse evidence and source notes
            try:
                evidence = json.loads(insight_row.get('evidence', '{}'))
                source_notes = json.loads(insight_row.get('source_notes', '[]'))
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid insight data"}
            
            todo_text = evidence.get('todo_text', '')
            note_path = source_notes[0].get('path', '') if source_notes else ''
            note_name = evidence.get('note_name', '')
            context = source_notes[0].get('snippet', '') if source_notes else ''
            
            if not todo_text:
                return {"success": False, "error": "Todo text not found in insight"}
            
            # Use Claude Agent to generate suggested actions
            try:
                from claude_agent_sdk import query, ClaudeAgentOptions
                from pathlib import Path
                
                # Build prompt for generating actions
                prompt = f"""Given this todo item:

Todo: {todo_text}
Note: {note_path}
Context: {context[:200] if context else 'No context available'}

Suggest 2-4 actionable next steps the user might want to take with this todo. Each action should be:
- Specific and actionable
- Written as a natural language command/question that could be sent to an AI assistant
- Focused on helping the user make progress on this todo

Return your suggestions as a JSON array of objects with this structure:
[
  {{"text": "action text here", "description": "brief description"}},
  ...
]

Example format:
[
  {{"text": "Break down '{todo_text}' into smaller subtasks", "description": "Decompose into manageable steps"}},
  {{"text": "Add a deadline for '{todo_text}'", "description": "Set a target completion date"}},
  {{"text": "Move '{todo_text}' to a project planning note", "description": "Organize into project structure"}}
]

Generate 2-4 relevant actions now:"""

                system_prompt = """You are a helpful assistant that suggests actionable next steps for todo items. 
Your suggestions should be practical, specific, and help users make progress on their tasks.
Return only valid JSON, no additional text."""

                options = ClaudeAgentOptions(
                    cwd=str(self.working_dir),
                    allowed_tools=[],  # No file access needed for this
                    max_turns=2,
                    system_prompt=system_prompt
                )
                
                result_text = []
                async for message in query(prompt=prompt, options=options):
                    message_type = message.__class__.__name__
                    if message_type == "AssistantMessage":
                        if hasattr(message, 'content'):
                            for block in message.content:
                                if hasattr(block, 'text'):
                                    result_text.append(block.text)
                
                # Parse the JSON response
                full_response = "\n".join(result_text)
                
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\[.*\]', full_response, re.DOTALL)
                if json_match:
                    actions_json = json_match.group(0)
                    actions = json.loads(actions_json)
                else:
                    # Fallback: try parsing the whole response
                    actions = json.loads(full_response)
                
                # Validate and format actions
                if not isinstance(actions, list):
                    actions = [actions] if isinstance(actions, dict) else []
                
                # Ensure we have 2-4 actions
                actions = actions[:4]  # Limit to 4
                if len(actions) < 2:
                    # Fallback actions if AI didn't generate enough
                    fallback_actions = [
                        {"text": f"Complete '{todo_text}'", "description": "Mark this todo as done"},
                        {"text": f"Break down '{todo_text}' into subtasks", "description": "Decompose into smaller steps"}
                    ]
                    actions = actions + fallback_actions[:2-len(actions)]
                
                # Clean up actions
                formatted_actions = []
                for action in actions:
                    if isinstance(action, dict):
                        text = action.get('text', '')
                        description = action.get('description', '')
                        if text:
                            formatted_actions.append({
                                "text": text,
                                "description": description or text
                            })
                
                if not formatted_actions:
                    return {"success": False, "error": "Failed to generate valid actions"}
                
                # Cache the generated actions in the database
                actions_to_cache = formatted_actions[:4]  # Ensure max 4
                try:
                    db.execute_update(
                        "UPDATE semantic_insights SET suggested_actions = ? WHERE id = ?",
                        (json.dumps(actions_to_cache), insight_id)
                    )
                    logger.info(f"Cached {len(actions_to_cache)} suggested actions for insight {insight_id}")
                except Exception as e:
                    logger.warning(f"Failed to cache suggested actions: {e}")
                
                logger.info(f"Generated {len(actions_to_cache)} suggested actions for insight {insight_id}")
                return {
                    "success": True,
                    "actions": actions_to_cache,
                    "cached": False
                }
                
            except ImportError:
                logger.warning("Claude Agent SDK not available for generating suggested actions")
                # Return fallback actions
                fallback_actions = [
                    {"text": f"Complete '{todo_text}'", "description": "Mark this todo as done"},
                    {"text": f"Break down '{todo_text}' into subtasks", "description": "Decompose into smaller steps"},
                    {"text": f"Add a deadline for '{todo_text}'", "description": "Set a target completion date"},
                    {"text": f"Move '{todo_text}' to a project planning note", "description": "Organize into project structure"}
                ]
                
                # Cache fallback actions too
                try:
                    db.execute_update(
                        "UPDATE semantic_insights SET suggested_actions = ? WHERE id = ?",
                        (json.dumps(fallback_actions), insight_id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache fallback actions: {e}")
                
                return {
                    "success": True,
                    "actions": fallback_actions,
                    "cached": False
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response for suggested actions: {e}")
                return {"success": False, "error": f"Failed to parse AI response: {str(e)}"}
            except Exception as e:
                logger.error(f"Error generating suggested actions: {e}")
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            logger.error(f"Error generating suggested actions for insight {insight_id}: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_semantic_insights_service: Optional[SemanticInsightsService] = None


def get_semantic_insights_service(
    working_dir: Optional[Path] = None
) -> SemanticInsightsService:
    """
    Get or create the singleton service instance.

    Args:
        working_dir: Base directory for file operations

    Returns:
        SemanticInsightsService instance
    """
    global _semantic_insights_service

    if _semantic_insights_service is None:
        _semantic_insights_service = SemanticInsightsService(working_dir=working_dir)

    return _semantic_insights_service
