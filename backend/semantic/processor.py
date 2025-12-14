"""
Semantic Processing Pipeline
============================

Coordinates the semantic analysis pipeline:
1. Detect changed notes (content hash comparison)
2. Extract entities (todos, mentions, tags)
3. Discover relationships between notes
4. Generate insights
5. Cleanup expired insights
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from database.models import db
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


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
        max_runtime_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Run the full processing pipeline.

        Args:
            max_notes: Maximum number of notes to process
            max_runtime_seconds: Maximum runtime in seconds

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
            insights_count = await self._generate_insights()
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

    async def _generate_insights(self) -> int:
        """
        Generate insights from extracted entities.

        Returns:
            Number of insights generated
        """
        insights_generated = 0

        try:
            # Immediate insights (no aging required)
            insights_generated += await self._generate_active_todo_insights()
            insights_generated += await self._generate_todo_summary_insight()
            insights_generated += await self._generate_project_overview_insight()

            # Time-based insights (require aging)
            insights_generated += await self._generate_stale_todo_insights()
            insights_generated += await self._generate_orphan_mention_insights()

        except Exception as e:
            logger.error(f"Error generating insights: {e}")

        return insights_generated

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
