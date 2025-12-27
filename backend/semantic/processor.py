"""
Semantic Processing Pipeline
============================

Coordinates the semantic analysis pipeline:
1. Detect changed notes (content hash comparison)
2. Extract entities (todos, mentions, tags)
3. Build working context (recent activity, projects, trajectory)
4. Generate contextual insights with AI
5. Cleanup expired insights
"""

import logging
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from database.models import db
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


# Contextual insight generation prompt
CONTEXTUAL_INSIGHT_SYSTEM_PROMPT = """You are a thoughtful assistant analyzing a user's Obsidian notes to provide helpful, contextual insights.

Your job is to identify actionable insights that matter RIGHT NOW based on:
- What the user is currently working on (active projects)
- Recent activity patterns
- The relationship between items and current focus

You are NOT just summarizing - you are identifying things that need attention, decisions, or action.

IMPORTANT - Diversity guidance:
When generating insights, prefer variety across different files/notes. Avoid generating multiple insights about the same file unless each insight is genuinely distinct and important. If one file has many items, pick only the most significant 1-2 rather than creating several insights about it.

For each insight you generate, you MUST provide:

1. TITLE: Brief description of what you found (5-10 words, be specific)

2. REASONING: Explain WHY this matters to the user right now. Consider:
   - Is this relevant to their active projects?
   - Is timing significant (deadline, staleness)?
   - What's the consequence of action/inaction?

3. CONTEXT_SPECIFIC_ACTIONS: Generate 2-3 actions SPECIFIC to THIS item:
   - NOT generic ("add deadline") but specific to this exact situation
   - Include rationale for why each action makes sense
   - Consider the user's current work context

4. CATEGORY: Classify as one of:
   - immediate_action: Needs attention within 24 hours
   - trend: Pattern worth noting
   - recommendation: Suggested improvement
   - observation: Interesting finding

Return your response as a JSON array of insight objects with this structure:
{
  "title": "string",
  "reasoning": "string (2-3 sentences explaining WHY this matters now)",
  "category": "immediate_action|trend|recommendation|observation",
  "insight_type": "stale_todo|active_todos|orphan_mention|connection|theme",
  "source_note": "path/to/note.md",
  "todo_text": "the actual todo text if applicable",
  "context_awareness": {
    "recency_score": 0.0-1.0,
    "project_context": ["relevant", "projects"],
    "relevance_factors": ["why", "this", "matters"]
  },
  "context_specific_actions": [
    {
      "text": "Specific action description",
      "rationale": "Why this action makes sense for this situation",
      "action_type": "complete|modify|archive|expand|delegate"
    }
  ],
  "priority": 1-5,
  "confidence": 0.0-1.0
}

Focus on QUALITY over quantity. Only generate insights that truly matter. Maximum 10 insights."""


class SemanticProcessor:
    """
    Coordinates the semantic analysis pipeline for notes.

    Manages the flow from detecting changed notes through entity extraction
    to generating actionable insights.
    """

    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize the semantic processor.

        Args:
            working_dir: Base directory for file operations
        """
        self.working_dir = working_dir or Path.cwd()
        self.entity_extractor = EntityExtractor(working_dir=self.working_dir, use_ai=True)

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get_notes_needing_processing(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find notes that have changed since last processing.

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of note dicts with path and content
        """
        try:
            # Get all tracked files from file_states table
            query = """
                SELECT fs.file_path, fs.content_hash, fs.last_modified
                FROM file_states fs
                LEFT JOIN semantic_processing_state sps ON fs.file_path = sps.note_path
                WHERE fs.file_path LIKE '%.md'
                  AND (sps.content_hash IS NULL OR sps.content_hash != fs.content_hash)
                ORDER BY fs.last_modified DESC
                LIMIT ?
            """
            results = db.execute_query(query, (limit,))

            notes = []
            for row in results:
                note_path = row['file_path']
                # Read actual content
                try:
                    full_path = self.working_dir / note_path
                    if full_path.exists():
                        content = full_path.read_text(encoding='utf-8')
                        notes.append({
                            'path': note_path,
                            'content': content,
                            'content_hash': self.calculate_content_hash(content)
                        })
                except Exception as e:
                    logger.warning(f"Could not read {note_path}: {e}")

            logger.info(f"Found {len(notes)} notes needing processing")
            return notes

        except Exception as e:
            logger.error(f"Error getting notes needing processing: {e}")
            return []

    async def process_note(self, note_path: str, content: str) -> Dict[str, Any]:
        """
        Process a single note: extract entities and store in database.

        Args:
            note_path: Path to the note
            content: Note content

        Returns:
            Processing result dict
        """
        result = {
            'note_path': note_path,
            'entities_extracted': 0,
            'success': False,
            'error': None
        }

        try:
            # Extract entities
            entities = await self.entity_extractor.extract_entities(note_path, content)
            result['entities_extracted'] = len(entities)

            # Store entities in database
            if entities:
                self._store_entities(note_path, entities)

            # Update processing state
            content_hash = self.calculate_content_hash(content)
            self._update_processing_state(note_path, content_hash)

            result['success'] = True
            logger.info(f"Processed {note_path}: {len(entities)} entities")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error processing {note_path}: {e}")

        return result

    def _store_entities(self, note_path: str, entities: List[Dict[str, Any]]):
        """Store extracted entities in the database."""
        try:
            # Clear existing entities for this note
            db.execute_update(
                "DELETE FROM note_entities WHERE note_path = ?",
                (note_path,)
            )

            # Insert new entities
            for entity in entities:
                db.execute_update("""
                    INSERT INTO note_entities (
                        note_path, entity_type, entity_value, context,
                        status, line_number, extracted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.get('note_path', note_path),
                    entity.get('entity_type'),
                    entity.get('entity_value'),
                    entity.get('context'),
                    entity.get('status', 'active'),
                    entity.get('line_number'),
                    entity.get('extracted_at', datetime.now().isoformat())
                ))

            logger.debug(f"Stored {len(entities)} entities for {note_path}")

        except Exception as e:
            logger.error(f"Error storing entities: {e}")
            raise

    def _update_processing_state(self, note_path: str, content_hash: str):
        """Update the processing state for a note."""
        try:
            db.execute_update("""
                INSERT OR REPLACE INTO semantic_processing_state (
                    note_path, content_hash, last_entity_extraction
                ) VALUES (?, ?, ?)
            """, (note_path, content_hash, datetime.now().isoformat()))

        except Exception as e:
            logger.error(f"Error updating processing state: {e}")

    async def run_processing_pipeline(
        self,
        max_notes: int = 50,
        max_runtime_seconds: int = 300,
        cleanup_before_generate: bool = True
    ) -> Dict[str, Any]:
        """
        Run the full processing pipeline.

        Args:
            max_notes: Maximum number of notes to process
            max_runtime_seconds: Maximum runtime in seconds
            cleanup_before_generate: If True, delete non-pinned insights before generating new ones

        Returns:
            Processing run summary
        """
        start_time = datetime.now()
        run_id = self._start_scheduler_run()

        summary = {
            'run_id': run_id,
            'started_at': start_time.isoformat(),
            'notes_processed': 0,
            'entities_extracted': 0,
            'insights_generated': 0,
            'errors': []
        }

        try:
            # Get notes needing processing
            notes = self.get_notes_needing_processing(limit=max_notes)

            for note in notes:
                # Check runtime limit
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > max_runtime_seconds:
                    logger.info(f"Runtime limit reached ({max_runtime_seconds}s)")
                    break

                # Process note
                result = await self.process_note(note['path'], note['content'])
                summary['notes_processed'] += 1
                summary['entities_extracted'] += result.get('entities_extracted', 0)

                if result.get('error'):
                    summary['errors'].append({
                        'note': note['path'],
                        'error': result['error']
                    })

            # Generate insights from extracted entities
            insights_count = await self._generate_insights(cleanup=cleanup_before_generate)
            summary['insights_generated'] = insights_count

        except Exception as e:
            summary['errors'].append({'error': str(e)})
            logger.error(f"Processing pipeline error: {e}")

        finally:
            # Complete scheduler run
            summary['completed_at'] = datetime.now().isoformat()
            summary['runtime_seconds'] = (datetime.now() - start_time).total_seconds()
            self._complete_scheduler_run(run_id, summary)

        logger.info(f"Processing complete: {summary['notes_processed']} notes, "
                   f"{summary['entities_extracted']} entities, "
                   f"{summary['insights_generated']} insights")

        return summary

    def _start_scheduler_run(self) -> int:
        """Start a new scheduler run and return its ID."""
        try:
            db.execute_update("""
                INSERT INTO insight_scheduler_runs (started_at)
                VALUES (?)
            """, (datetime.now().isoformat(),))
            # Get the actual inserted row ID
            result = db.execute_query("SELECT last_insert_rowid() as id")
            return result[0]['id'] if result else 0
        except Exception as e:
            logger.error(f"Error starting scheduler run: {e}")
            return 0

    def _complete_scheduler_run(self, run_id: int, summary: Dict[str, Any]):
        """Complete a scheduler run with summary."""
        try:
            import json
            errors_json = json.dumps(summary.get('errors', []))

            db.execute_update("""
                UPDATE insight_scheduler_runs
                SET completed_at = ?,
                    runtime_seconds = ?,
                    notes_processed = ?,
                    insights_generated = ?,
                    errors = ?
                WHERE id = ?
            """, (
                summary.get('completed_at'),
                summary.get('runtime_seconds'),
                summary.get('notes_processed'),
                summary.get('insights_generated'),
                errors_json,
                run_id
            ))
        except Exception as e:
            logger.error(f"Error completing scheduler run: {e}")

    def _cleanup_non_pinned_insights(self) -> int:
        """
        Delete existing insights that are not pinned.
        
        Returns:
            Number of insights deleted
        """
        try:
            result = db.execute_update("""
                DELETE FROM semantic_insights
                WHERE status != 'pinned'
            """)
            
            logger.info(f"Cleaned up {result} non-pinned insights before refresh")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up non-pinned insights: {e}")
            return 0

    async def _generate_insights(self, cleanup: bool = True) -> int:
        """
        Generate contextual insights from extracted entities using AI.

        Args:
            cleanup: If True, delete non-pinned insights before generating new ones

        Returns:
            Number of insights generated
        """
        # Only cleanup if requested (for incremental mode, we keep existing insights)
        if cleanup:
            self._cleanup_non_pinned_insights()

        insights_generated = 0

        try:
            # Use the new contextual insight generation
            insights_generated = await self._generate_contextual_insights()

        except Exception as e:
            logger.error(f"Error generating contextual insights: {e}")
            # Fall back to legacy pattern-based insights if AI fails
            logger.info("Falling back to legacy insight generation")
            insights_generated = await self._generate_legacy_insights()

        return insights_generated

    async def _generate_legacy_insights(self) -> int:
        """Legacy pattern-based insight generation (fallback)."""
        insights_generated = 0

        try:
            insights_generated += await self._generate_active_todo_insights()
            insights_generated += await self._generate_todo_summary_insight()
            insights_generated += await self._generate_project_overview_insight()
            insights_generated += await self._generate_stale_todo_insights()
            insights_generated += await self._generate_orphan_mention_insights()
        except Exception as e:
            logger.error(f"Error in legacy insight generation: {e}")

        return insights_generated

    async def _generate_contextual_insights(self) -> int:
        """
        Generate contextual insights using AI with working context awareness.

        This is the new approach that:
        1. Builds a working context (recent activity, projects, trajectory)
        2. Gathers entities to analyze
        3. Calls Claude with full context to generate intelligent insights
        4. Stores insights with reasoning and context-specific actions

        Returns:
            Number of insights generated
        """
        try:
            from services.working_context_service import get_working_context_service
            from claude_agent_sdk import query, ClaudeAgentOptions
        except ImportError as e:
            logger.warning(f"Dependencies not available for contextual insights: {e}")
            return await self._generate_legacy_insights()

        try:
            # Step 1: Build working context
            context_service = get_working_context_service()
            working_context = await context_service.build_context(force_refresh=True)

            # Step 2: Gather entities to analyze
            entities_data = self._gather_entities_for_analysis(working_context.context_window_days)

            if not entities_data['todos'] and not entities_data['mentions']:
                logger.info("No entities to analyze for insights")
                return 0

            # Step 3: Build the analysis prompt
            prompt = self._build_contextual_insight_prompt(working_context, entities_data)

            # Step 4: Call Claude for contextual analysis
            options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                allowed_tools=[],  # No tools needed for analysis
                max_turns=1,
                system_prompt=CONTEXTUAL_INSIGHT_SYSTEM_PROMPT
            )

            result_text = []
            async for message in query(prompt=prompt, options=options):
                message_type = message.__class__.__name__
                if message_type == "AssistantMessage":
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                result_text.append(block.text)

            full_response = "\n".join(result_text)

            # Step 5: Parse and store insights
            insights = self._parse_contextual_insights(full_response)
            stored_count = self._store_contextual_insights(insights)

            logger.info(f"Generated {stored_count} contextual insights")
            return stored_count

        except Exception as e:
            logger.error(f"Contextual insight generation failed: {e}", exc_info=True)
            return await self._generate_legacy_insights()

    def _gather_entities_for_analysis(self, context_window_days: int) -> Dict[str, Any]:
        """Gather entities within the context window for analysis."""
        cutoff = (datetime.now() - timedelta(days=context_window_days)).isoformat()

        result = {
            'todos': [],
            'mentions': [],
            'tags': [],
            'projects': []
        }

        try:
            # Get active todos with context
            todo_query = """
                SELECT ne.note_path, ne.entity_value, ne.context, ne.status,
                       ne.extracted_at, fs.last_modified
                FROM note_entities ne
                LEFT JOIN file_states fs ON ne.note_path = fs.file_path
                WHERE ne.entity_type = 'todo'
                  AND ne.status = 'active'
                ORDER BY fs.last_modified DESC
                LIMIT 30
            """
            todos = db.execute_query(todo_query)
            result['todos'] = [dict(t) for t in todos]

            # Get mentions that might be orphaned
            mention_query = """
                SELECT entity_value, MIN(note_path) as note_path,
                       MIN(context) as context, COUNT(*) as occurrence_count
                FROM note_entities
                WHERE entity_type IN ('mention', 'person', 'link')
                  AND extracted_at > ?
                GROUP BY entity_value
                HAVING occurrence_count <= 2
                LIMIT 20
            """
            mentions = db.execute_query(mention_query, (cutoff,))
            result['mentions'] = [dict(m) for m in mentions]

            # Get tag distribution
            tag_query = """
                SELECT entity_value, COUNT(*) as count
                FROM note_entities
                WHERE entity_type = 'tag'
                GROUP BY entity_value
                ORDER BY count DESC
                LIMIT 15
            """
            tags = db.execute_query(tag_query)
            result['tags'] = [dict(t) for t in tags]

            # Get projects
            project_query = """
                SELECT entity_value, COUNT(DISTINCT note_path) as note_count
                FROM note_entities
                WHERE entity_type = 'project'
                GROUP BY entity_value
                ORDER BY note_count DESC
                LIMIT 10
            """
            projects = db.execute_query(project_query)
            result['projects'] = [dict(p) for p in projects]

        except Exception as e:
            logger.error(f"Error gathering entities: {e}")

        return result

    def _build_contextual_insight_prompt(
        self,
        working_context: Any,
        entities_data: Dict[str, Any]
    ) -> str:
        """Build the prompt for contextual insight generation."""
        lines = []

        # Add working context
        lines.append("=== WORKING CONTEXT ===")
        lines.append(working_context.to_prompt_context())
        lines.append("")

        # Add entities to analyze
        lines.append("=== ITEMS TO ANALYZE ===")
        lines.append("")

        # Todos
        if entities_data['todos']:
            lines.append("PENDING TODOS:")
            for i, todo in enumerate(entities_data['todos'][:20], 1):
                age_str = ""
                if todo.get('extracted_at'):
                    try:
                        extracted = datetime.fromisoformat(todo['extracted_at'])
                        age_days = (datetime.now() - extracted).days
                        age_str = f" [{age_days} days old]"
                    except:
                        pass
                lines.append(f"  {i}. [{todo['note_path']}]{age_str}")
                lines.append(f"     Todo: {todo['entity_value'][:100]}")
                if todo.get('context'):
                    lines.append(f"     Context: {todo['context'][:150]}")
                lines.append("")

        # Potential orphan mentions
        if entities_data['mentions']:
            lines.append("POTENTIAL ORPHAN MENTIONS (appear 1-2 times):")
            for m in entities_data['mentions'][:10]:
                lines.append(f"  - '{m['entity_value']}' in {m['note_path']} "
                           f"(appears {m['occurrence_count']} time(s))")
            lines.append("")

        # Tag overview
        if entities_data['tags']:
            tag_summary = ", ".join([f"#{t['entity_value']}({t['count']})"
                                    for t in entities_data['tags'][:10]])
            lines.append(f"TAG DISTRIBUTION: {tag_summary}")
            lines.append("")

        lines.append("=== YOUR TASK ===")
        lines.append("Analyze the items above in the context of the user's recent work.")
        lines.append("Generate insights that are SPECIFIC and ACTIONABLE.")
        lines.append("Focus on what matters NOW given their current projects and focus.")
        lines.append("")
        lines.append("Return ONLY a JSON array of insights. No other text.")

        return "\n".join(lines)

    def _parse_contextual_insights(self, response: str) -> List[Dict[str, Any]]:
        """Parse the AI response to extract insight JSON."""
        insights = []

        # Try to find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                raw_insights = json.loads(json_match.group())
                for insight in raw_insights:
                    if isinstance(insight, dict) and 'title' in insight:
                        # Validate and normalize the insight
                        normalized = {
                            'title': insight.get('title', 'Untitled Insight'),
                            'reasoning': insight.get('reasoning', ''),
                            'summary': insight.get('reasoning', '')[:200],  # Use reasoning as summary
                            'category': insight.get('category', 'observation'),
                            'insight_type': insight.get('insight_type', 'active_todos'),
                            'source_note': insight.get('source_note', ''),
                            'todo_text': insight.get('todo_text', ''),
                            'context_awareness': insight.get('context_awareness', {}),
                            'context_specific_actions': insight.get('context_specific_actions', []),
                            'priority': insight.get('priority', 2),
                            'confidence': insight.get('confidence', 0.8)
                        }
                        insights.append(normalized)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse insight JSON: {e}")
                logger.debug(f"Response was: {response[:500]}")
        else:
            logger.warning("No JSON array found in AI response")
            logger.debug(f"Response was: {response[:500]}")

        return insights

    def _store_contextual_insights(self, insights: List[Dict[str, Any]]) -> int:
        """Store parsed contextual insights in the database."""
        stored = 0

        for insight in insights:
            try:
                # Prepare source_notes JSON
                source_notes = []
                if insight.get('source_note'):
                    source_notes.append({
                        'path': insight['source_note'],
                        'snippet': insight.get('todo_text', '')[:100]
                    })

                # Prepare evidence JSON
                evidence = {
                    'todo_text': insight.get('todo_text', ''),
                    'generated_by': 'contextual_ai',
                    'generated_at': datetime.now().isoformat()
                }

                # Store the insight
                db.execute_update("""
                    INSERT INTO semantic_insights (
                        insight_type, title, summary, source_notes,
                        evidence, confidence, priority, status,
                        reasoning, context_awareness, insight_category,
                        suggested_actions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    insight['insight_type'],
                    insight['title'],
                    insight['summary'],
                    json.dumps(source_notes),
                    json.dumps(evidence),
                    insight['confidence'],
                    insight['priority'],
                    'new',
                    insight['reasoning'],
                    json.dumps(insight['context_awareness']),
                    insight['category'],
                    json.dumps(insight['context_specific_actions'])
                ))
                stored += 1

            except Exception as e:
                logger.error(f"Failed to store insight '{insight.get('title')}': {e}")

        return stored

    async def _generate_stale_todo_insights(self, days_threshold: int = 7) -> int:
        """Generate insights for stale todos."""
        try:
            import json
            threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()

            # Find todos that are old and still active
            query = """
                SELECT ne.*, sps.last_entity_extraction
                FROM note_entities ne
                JOIN semantic_processing_state sps ON ne.note_path = sps.note_path
                WHERE ne.entity_type = 'todo'
                  AND ne.status = 'active'
                  AND ne.extracted_at < ?
                ORDER BY ne.extracted_at ASC
                LIMIT 10
            """
            stale_todos = db.execute_query(query, (threshold_date,))

            count = 0
            for todo in stale_todos:
                # Check if insight already exists
                existing = db.execute_query("""
                    SELECT id FROM semantic_insights
                    WHERE insight_type = 'stale_todo'
                      AND source_notes LIKE ?
                      AND status NOT IN ('dismissed', 'actioned')
                """, (f'%{todo["note_path"]}%',))

                if not existing:
                    source_notes = json.dumps([{
                        'path': todo['note_path'],
                        'snippet': todo.get('context', '')[:100]
                    }])

                    evidence = json.dumps({
                        'todo_text': todo['entity_value'],
                        'created_at': todo['extracted_at'],
                        'line_number': todo.get('line_number')
                    })

                    db.execute_update("""
                        INSERT INTO semantic_insights (
                            insight_type, title, summary, source_notes,
                            evidence, confidence, priority, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'stale_todo',
                        f'Stale action item',
                        f'"{todo["entity_value"][:50]}..." has been pending for {days_threshold}+ days',
                        source_notes,
                        evidence,
                        0.8,  # confidence
                        2,    # priority
                        'new'
                    ))
                    count += 1

            logger.info(f"Generated {count} stale todo insights")
            return count

        except Exception as e:
            logger.error(f"Error generating stale todo insights: {e}")
            return 0

    async def _generate_orphan_mention_insights(self, days_recent: int = 3) -> int:
        """Generate insights for orphaned mentions."""
        try:
            import json
            recent_threshold = (datetime.now() - timedelta(days=days_recent)).isoformat()

            # Find mentions that appear only once and aren't recent
            query = """
                SELECT entity_value, MIN(note_path) as note_path,
                       MIN(context) as context, COUNT(*) as count
                FROM note_entities
                WHERE entity_type IN ('mention', 'person', 'link')
                  AND extracted_at < ?
                GROUP BY entity_value
                HAVING count = 1
                LIMIT 10
            """
            orphans = db.execute_query(query, (recent_threshold,))

            count = 0
            for orphan in orphans:
                # Check if insight already exists
                existing = db.execute_query("""
                    SELECT id FROM semantic_insights
                    WHERE insight_type = 'orphan_mention'
                      AND summary LIKE ?
                      AND status NOT IN ('dismissed', 'actioned')
                """, (f'%{orphan["entity_value"]}%',))

                if not existing:
                    source_notes = json.dumps([{
                        'path': orphan['note_path'],
                        'snippet': orphan.get('context', '')[:100]
                    }])

                    evidence = json.dumps({
                        'mention': orphan['entity_value'],
                        'context': orphan.get('context')
                    })

                    db.execute_update("""
                        INSERT INTO semantic_insights (
                            insight_type, title, summary, source_notes,
                            evidence, confidence, priority, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'orphan_mention',
                        f'Orphaned mention',
                        f'"{orphan["entity_value"]}" was mentioned once and never referenced again',
                        source_notes,
                        evidence,
                        0.7,  # confidence
                        1,    # priority
                        'new'
                    ))
                    count += 1

            logger.info(f"Generated {count} orphan mention insights")
            return count

        except Exception as e:
            logger.error(f"Error generating orphan mention insights: {e}")
            return 0

    async def _generate_active_todo_insights(self) -> int:
        """Generate insights for active (unchecked) todos - no aging required."""
        try:
            import json

            # Find all active todos
            query = """
                SELECT ne.note_path, ne.entity_value, ne.context, ne.line_number
                FROM note_entities ne
                WHERE ne.entity_type = 'todo'
                  AND ne.status = 'active'
                ORDER BY ne.extracted_at DESC
                LIMIT 20
            """
            active_todos = db.execute_query(query)

            count = 0
            for todo in active_todos:
                todo_dict = dict(todo)  # Convert Row to dict for .get() support

                # Check if insight already exists for this specific todo
                existing = db.execute_query("""
                    SELECT id FROM semantic_insights
                    WHERE insight_type = 'active_todos'
                      AND evidence LIKE ?
                      AND status NOT IN ('dismissed', 'actioned')
                """, (f'%{todo_dict["entity_value"][:50]}%',))

                if not existing:
                    # Get note filename for display
                    note_name = todo_dict['note_path'].split('/')[-1].replace('.md', '')

                    source_notes = json.dumps([{
                        'path': todo_dict['note_path'],
                        'snippet': (todo_dict.get('context') or '')[:100]
                    }])

                    evidence = json.dumps({
                        'todo_text': todo_dict['entity_value'],
                        'line_number': todo_dict.get('line_number'),
                        'note_name': note_name
                    })

                    db.execute_update("""
                        INSERT INTO semantic_insights (
                            insight_type, title, summary, source_notes,
                            evidence, confidence, priority, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'active_todos',
                        f'Action item in {note_name}',
                        f'{todo_dict["entity_value"][:80]}',
                        source_notes,
                        evidence,
                        1.0,  # confidence - we know it's there
                        3,    # high priority for active todos
                        'new'
                    ))
                    count += 1

            logger.info(f"Generated {count} active todo insights")
            return count

        except Exception as e:
            logger.error(f"Error generating active todo insights: {e}")
            return 0

    async def _generate_todo_summary_insight(self) -> int:
        """Generate a summary insight showing todo counts across notes."""
        try:
            import json

            # Get todo statistics
            stats_query = """
                SELECT
                    COUNT(*) as total_todos,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    COUNT(DISTINCT note_path) as notes_with_todos
                FROM note_entities
                WHERE entity_type = 'todo'
            """
            stats = db.execute_query(stats_query)

            if not stats or stats[0]['total_todos'] == 0:
                return 0

            stat = stats[0]
            active = stat['active_count'] or 0
            completed = stat['completed_count'] or 0
            notes_count = stat['notes_with_todos'] or 0

            # Check if summary insight already exists (only one at a time)
            existing = db.execute_query("""
                SELECT id FROM semantic_insights
                WHERE insight_type = 'todo_summary'
                  AND status NOT IN ('dismissed', 'actioned')
            """)

            if existing:
                # Update existing summary instead of creating new
                evidence = json.dumps({
                    'active_count': active,
                    'completed_count': completed,
                    'notes_with_todos': notes_count,
                    'updated_at': datetime.now().isoformat()
                })

                db.execute_update("""
                    UPDATE semantic_insights
                    SET summary = ?, evidence = ?
                    WHERE id = ?
                """, (
                    f'{active} active, {completed} completed across {notes_count} notes',
                    evidence,
                    existing[0]['id']
                ))
                return 0  # Updated, not created

            # Create new summary
            source_notes = json.dumps([])  # No specific source for summary

            evidence = json.dumps({
                'active_count': active,
                'completed_count': completed,
                'notes_with_todos': notes_count
            })

            db.execute_update("""
                INSERT INTO semantic_insights (
                    insight_type, title, summary, source_notes,
                    evidence, confidence, priority, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'todo_summary',
                'Todo Overview',
                f'{active} active, {completed} completed across {notes_count} notes',
                source_notes,
                evidence,
                1.0,
                1,  # lower priority - it's informational
                'new'
            ))

            logger.info("Generated todo summary insight")
            return 1

        except Exception as e:
            logger.error(f"Error generating todo summary insight: {e}")
            return 0

    async def _generate_project_overview_insight(self) -> int:
        """Generate insights showing discovered projects."""
        try:
            import json

            # Get all projects with their note counts
            query = """
                SELECT entity_value, COUNT(DISTINCT note_path) as note_count,
                       GROUP_CONCAT(DISTINCT note_path) as notes
                FROM note_entities
                WHERE entity_type = 'project'
                GROUP BY entity_value
                ORDER BY note_count DESC
                LIMIT 10
            """
            projects = db.execute_query(query)

            if not projects:
                return 0

            count = 0
            for project in projects:
                # Check if insight already exists for this project
                existing = db.execute_query("""
                    SELECT id FROM semantic_insights
                    WHERE insight_type = 'project_overview'
                      AND title LIKE ?
                      AND status NOT IN ('dismissed', 'actioned')
                """, (f'%{project["entity_value"]}%',))

                if not existing:
                    note_list = project['notes'].split(',') if project['notes'] else []
                    source_notes = json.dumps([{'path': p} for p in note_list[:5]])

                    evidence = json.dumps({
                        'project_name': project['entity_value'],
                        'note_count': project['note_count'],
                        'notes': note_list
                    })

                    db.execute_update("""
                        INSERT INTO semantic_insights (
                            insight_type, title, summary, source_notes,
                            evidence, confidence, priority, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'project_overview',
                        f'Project: {project["entity_value"]}',
                        f'Found in {project["note_count"]} note{"s" if project["note_count"] > 1 else ""}',
                        source_notes,
                        evidence,
                        0.9,
                        2,
                        'new'
                    ))
                    count += 1

            logger.info(f"Generated {count} project overview insights")
            return count

        except Exception as e:
            logger.error(f"Error generating project overview insights: {e}")
            return 0

    def cleanup_expired_insights(self, days_old: int = 30):
        """Remove old dismissed or expired insights."""
        try:
            threshold = (datetime.now() - timedelta(days=days_old)).isoformat()

            result = db.execute_update("""
                DELETE FROM semantic_insights
                WHERE status = 'dismissed'
                  AND created_at < ?
            """, (threshold,))

            logger.info(f"Cleaned up {result} expired insights")

        except Exception as e:
            logger.error(f"Error cleaning up insights: {e}")

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about semantic processing."""
        try:
            # Entity counts by type
            entity_counts = db.execute_query("""
                SELECT entity_type, COUNT(*) as count
                FROM note_entities
                GROUP BY entity_type
            """)

            # Insight counts by type and status
            insight_counts = db.execute_query("""
                SELECT insight_type, status, COUNT(*) as count
                FROM semantic_insights
                GROUP BY insight_type, status
            """)

            # Recent runs
            recent_runs = db.execute_query("""
                SELECT * FROM insight_scheduler_runs
                ORDER BY started_at DESC
                LIMIT 5
            """)

            return {
                'entity_counts': {r['entity_type']: r['count'] for r in entity_counts},
                'insight_counts': [dict(r) for r in insight_counts],
                'recent_runs': [dict(r) for r in recent_runs]
            }

        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}
