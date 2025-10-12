import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

from ai.openai_client import OpenAIClient


logger = logging.getLogger(__name__)


class SessionSummaryService:
    """Service layer for all Session Summary operations.

    Centralizes update, content, and settings logic so routes stay thin.
    """

    def __init__(self, session_summary_path: str):
        # Base path provided by caller; final path may be dynamically resolved (daily mode)
        self.session_summary_path = Path(session_summary_path)
        self.settings_path = Path('config/session_summary_settings.json')
        self.format_path = Path('config/format.md')
        # Use singleton pattern to get the OpenAI client
        self.openai_client = OpenAIClient.get_instance()
        # Warm-up will be performed automatically on first use if needed
        logger.info("Session summary service initialized with singleton OpenAI client")
        # Ensure format.md is in config if legacy file exists
        try:
            from utils.migrations import migrate_format_md
            migrate_format_md()
        except Exception:
            pass

        # Load dynamic session summary configuration (daily vs single file)
        try:
            from config.settings import (
                SESSION_SUMMARY_MODE,
                SESSION_SUMMARY_DAILY_DIR,
                SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE,
                SESSION_SUMMARY_PATH as SESSION_SUMMARY_SINGLE_PATH,
            )
            self._SESSION_SUMMARY_MODE = str(SESSION_SUMMARY_MODE).lower()
            self._SESSION_SUMMARY_DAILY_DIR = Path(SESSION_SUMMARY_DAILY_DIR)
            self._SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE = SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE
            self._SESSION_SUMMARY_SINGLE_PATH = Path(SESSION_SUMMARY_SINGLE_PATH)
        except Exception:
            # Fallback defaults
            self._SESSION_SUMMARY_MODE = "single"
            self._SESSION_SUMMARY_DAILY_DIR = Path('notes/daily')
            self._SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE = "Session Summary - {date}.md"
            self._SESSION_SUMMARY_SINGLE_PATH = Path('notes/session_summary.md')

        # Apply lightweight migration to keep legacy session summary entries aligned
        self._migrate_legacy_entries()

    def _resolve_session_summary_path(self, now: datetime = None) -> Path:
        """Resolve current session summary file path based on configured mode."""
        if now is None:
            now = datetime.now()
        if self._SESSION_SUMMARY_MODE == "daily":
            self._SESSION_SUMMARY_DAILY_DIR.mkdir(parents=True, exist_ok=True)
            date_str = now.strftime('%Y-%m-%d')
            filename = self._SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE.format(date=date_str)
            resolved = self._SESSION_SUMMARY_DAILY_DIR / filename
        else:
            self._SESSION_SUMMARY_SINGLE_PATH.parent.mkdir(parents=True, exist_ok=True)
            resolved = self._SESSION_SUMMARY_SINGLE_PATH
        # Cache resolved path
        self.session_summary_path = resolved
        return resolved

    def _migrate_legacy_entries(self) -> None:
        """Update legacy session summary records to the new taxonomy."""
        try:
            from database.models import db

            db.execute_update(
                "UPDATE semantic_entries SET source_type = 'session_summary' WHERE source_type = 'living_note'"
            )
            db.execute_update(
                "UPDATE semantic_entries SET type = 'session_summary_summary' WHERE type = 'living_note_summary'"
            )
            db.execute_update(
                "UPDATE semantic_entries SET impact = 'brief' WHERE impact = 'minor'"
            )
            db.execute_update(
                """
                UPDATE semantic_entries
                SET source_type = 'session_summary_auto'
                WHERE source_type = 'session_summary'
                  AND (
                    markdown_file_path IS NULL OR
                    markdown_file_path = '' OR
                    markdown_file_path NOT LIKE 'output/summaries/%'
                  )
                """
            )
        except Exception as migration_error:
            logger.debug(f"Session summary migration skipped: {migration_error}")

    # ---------- Content ----------
    def get_content(self):
        try:
            current_path = self._resolve_session_summary_path()
            if current_path.exists():
                content = current_path.read_text(encoding='utf-8')
                stat = current_path.stat()
                last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
            else:
                content = "# Session Summary\n\nNo content yet. Start monitoring to see automated summaries appear here."
                last_updated = datetime.now().isoformat()

            return {
                'content': content,
                'path': str(current_path),
                'exists': current_path.exists(),
                'lastUpdated': last_updated,
                'wordCount': len(content.split()) if content else 0,
            }
        except Exception as e:
            logger.error(f"Failed to read session summary: {e}")
            raise

    def clear(self):
        try:
            current_path = self._resolve_session_summary_path()
            current_path.parent.mkdir(parents=True, exist_ok=True)
            with open(current_path, 'w', encoding='utf-8') as f:
                f.write("# Session Summary\n\nCleared at " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
            return {
                'success': True,
                'message': 'Session summary cleared successfully'
            }
        except Exception as e:
            logger.error(f"Failed to clear session summary: {e}")
            raise

    # ---------- Settings ----------
    def get_settings(self):
        try:
            # Defaults
            default_settings = {
                "enabled": True,
                "update_frequency": "immediate",
                "include_metadata": True,
                "max_summary_length": 500,
                "format_template": "## Summary\n\n{summary}\n\n## Key Changes\n\n{changes}\n\n---\n\n"
            }

            if self.settings_path.exists():
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = default_settings

            # Load format template if present
            if self.format_path.exists():
                with open(self.format_path, 'r', encoding='utf-8') as f:
                    settings['format_template'] = f.read()

            return {
                'settings': settings,
                'settings_path': str(self.settings_path),
                'format_path': str(self.format_path)
            }
        except Exception as e:
            logger.error(f"Failed to get session summary settings: {e}")
            raise

    def save_settings(self, data: dict):
        try:
            if not data:
                raise ValueError('No settings provided')

            # Extract format template separately
            format_template = data.get('format_template', '')
            if 'format_template' in data:
                del data['format_template']

            # Ensure config directory exists
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Save settings (without format_template)
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Save format template
            if format_template:
                with open(self.format_path, 'w', encoding='utf-8') as f:
                    f.write(format_template)

            return {
                'success': True,
                'message': 'Settings saved successfully',
                'settings_path': str(self.settings_path),
                'format_path': str(self.format_path)
            }
        except Exception as e:
            logger.error(f"Failed to save session summary settings: {e}")
            raise

    # ---------- Update ----------
    def update(self, force: bool = False):
        """Update the session summary by summarizing diffs since last update.

        Returns dict with success, updated, message, and summary when applicable.
        """
        try:
            t_total_start = time.perf_counter()
            
            # Warm up the OpenAI client before starting
            try:
                logger.info("Session summary update: warming up OpenAI client...")
                self.openai_client.warm_up()
                logger.info("Session summary update: OpenAI client warmed up successfully")
            except Exception as warm_up_error:
                logger.warning(f"OpenAI client warm-up failed (non-fatal): {warm_up_error}")
                # Continue anyway as the client might still work
            
            # Resolve target path (daily or single)
            target_path = self._resolve_session_summary_path()

            # Cursor window
            from database.models import ConfigModel
            last_ts_str = ConfigModel.get('session_summary_last_update', None)
            window_start = datetime.fromisoformat(last_ts_str) if last_ts_str else datetime.now() - timedelta(hours=4)

            # Optional file filtering
            watch_handler = None
            try:
                from utils.watch_handler import WatchHandler
                root_folder = Path(__file__).parent.parent
                watch_handler = WatchHandler(root_folder)
                logger.info(f"Session summary: initialized WatchHandler with root_folder: {root_folder}")
                logger.info(f"Session summary: loaded watch patterns: {watch_handler.watch_patterns}")
                logger.info(f"Session summary: watch file path: {watch_handler.watch_file}")
            except Exception as e:
                logger.debug(f"Watch patterns unavailable, proceeding without filter: {e}")

            # Fetch diffs
            from database.queries import FileQueries
            t_diffs_start = time.perf_counter()
            all_diffs = FileQueries.get_diffs_since(window_start, limit=200, watch_handler=watch_handler)
            t_diffs = time.perf_counter() - t_diffs_start
            logger.info(f"Session summary timing: get_diffs_since took {t_diffs:.3f}s (window_start={window_start.isoformat()})")
            
            # Exclude the session summary file itself to prevent feedback loops
            target_path = self._resolve_session_summary_path().resolve()
            diffs = []
            excluded_count = 0
            for diff in all_diffs:
                diff_path = Path(diff.get('filePath', '')).resolve()
                if diff_path == target_path:
                    excluded_count += 1
                    logger.debug(f"Excluding session summary file from its own update: {diff_path}")
                    continue
                # Exclude internal semantic index file and non-markdown files to avoid stale context pollution
                file_path_str = str(diff_path)
                if file_path_str.lower().endswith('semantic_index.json'):
                    excluded_count += 1
                    logger.debug(f"Excluding internal semantic index file from diffs: {diff_path}")
                    continue
                if not file_path_str.lower().endswith('.md'):
                    # Only summarize note markdown changes for the session summary
                    excluded_count += 1
                    continue
                diffs.append(diff)
            
            logger.info(f"Session summary: excluded {excluded_count} self-references, processing {len(diffs)} actual content diffs")

            # Fallback to recent diffs to avoid empty updates
            if not diffs:
                t_recent_start = time.perf_counter()
                all_recent_diffs = FileQueries.get_recent_diffs(limit=10, watch_handler=watch_handler)
                t_recent = time.perf_counter() - t_recent_start
                logger.info(f"Session summary timing: get_recent_diffs took {t_recent:.3f}s")
                # Also exclude session summary file from recent diffs
                recent_diffs = []
                for diff in all_recent_diffs:
                    diff_path = Path(diff.get('filePath', '')).resolve()
                    file_path_str = str(diff_path)
                    if diff_path == target_path:
                        continue
                    if file_path_str.lower().endswith('semantic_index.json'):
                        continue
                    if not file_path_str.lower().endswith('.md'):
                        continue
                    recent_diffs.append(diff)
                if recent_diffs:
                    diffs = recent_diffs
                    logger.info(f"Session summary: using {len(recent_diffs)} recent diffs (excluded session summary file)")
                elif not force:
                    return {
                        'success': True,
                        'message': 'No diffs since last update',
                        'updated': False
                    }
                else:
                    # When forced but no diffs found, return success without processing
                    logger.info("Session summary: forced update requested but no content changes found")
                    return {
                        'success': True,
                        'message': 'No new changes to summarize',
                        'updated': False,
                        'individual_summary_created': False
                    }

            # Build AI context and metrics
            if diffs:
                combined_parts = []
                max_items = min(len(diffs), 12)
                files_for_ai = []
                for d in diffs[:max_items]:
                    file_path = d.get('filePath') or d.get('path') or 'unknown'
                    files_for_ai.append(file_path)
                    ts = d.get('timestamp') or ''
                    diff_text = d.get('diffContent') or ''
                    if isinstance(diff_text, str) and len(diff_text) > 800:
                        diff_text = diff_text[:800] + "\n..."
                    combined_parts.append(f"File: {file_path} ({ts})\n{diff_text}")
                context_text = "\n\n---\n\n".join(combined_parts)
                logger.info(f"Session summary: sending {len(files_for_ai)} files to AI: {files_for_ai}")
            else:
                context_text = ""
                logger.info("Session summary: no diffs to send to AI")

            total_changes = len(diffs)
            files_affected = len({d.get('filePath') for d in diffs})
            # Filter out zero-change diffs to avoid counting meaningless +0/-0 entries
            meaningful_diffs = [d for d in diffs if int(d.get('linesAdded') or 0) > 0 or int(d.get('linesRemoved') or 0) > 0]
            lines_added = sum(int(d.get('linesAdded') or 0) for d in meaningful_diffs)
            lines_removed = sum(int(d.get('linesRemoved') or 0) for d in meaningful_diffs)
            notes_added_count = len({d.get('filePath') for d in diffs if (str(d.get('changeType')).lower() == 'created' and str(d.get('filePath') or '').lower().endswith('.md'))})

            # AI-generated summary bullets and proposed questions with error handling
            t_ai_start = time.perf_counter()
            
            # Try to generate summary (with embedded Sources) with fallback
            summary_bullets = "- no meaningful changes"
            if context_text:
                try:
                    logger.info("Session summary: generating AI summary (with Sources)...")
                    summary_bullets = self.openai_client.summarize_minimal(context_text, files_used=files_for_ai)
                    logger.info("Session summary: AI summary generated successfully")
                except Exception as e:
                    logger.error(f"Failed to generate AI summary (using fallback): {e}")
                    # Fallback to basic summary from metrics
                    if diffs:
                        summary_bullets = f"- {files_affected} files changed with {lines_added} lines added and {lines_removed} lines removed"
                    else:
                        summary_bullets = "- no meaningful changes detected"

            # Optional safety-net: if model omitted Sources, append via helper
            try:
                from config import settings as cfg
                if context_text and files_for_ai and cfg.AI_SOURCES_FALLBACK_ENABLED:
                    lower = summary_bullets.lower()
                    if '## sources' not in lower and '### sources' not in lower:
                        sources_md = self.openai_client.generate_sources_section(files_for_ai, context_snippet=context_text)
                        if sources_md and sources_md.strip():
                            summary_bullets = summary_bullets.rstrip() + "\n\n" + sources_md.strip()
            except Exception:
                pass
            
            t_ai_summary = time.perf_counter() - t_ai_start
            
            # Try to generate questions with graceful fallback
            t_ai_q_start = time.perf_counter()
            questions_text = ""
            if context_text:
                try:
                    logger.info("Session summary: generating proposed questions...")
                    questions_text = self.openai_client.generate_proposed_questions(context_text)
                    logger.info("Session summary: proposed questions generated successfully")
                except Exception as e:
                    logger.error(f"Failed to generate proposed questions (skipping): {e}")
                    # Questions are optional, so we can continue without them
                    questions_text = ""
            
            t_ai_questions = time.perf_counter() - t_ai_q_start
            logger.info(f"Session summary timing: AI summarize_minimal={t_ai_summary:.3f}s, generate_proposed_questions={t_ai_questions:.3f}s")
            
            # Metrics section formatted consistently with a header (like Questions)
            parts = [
                "### Metrics",
                "",
                f"- Total changes: {total_changes}",
                f"- Files affected: {files_affected}",
                f"- Lines: +{lines_added}/-{lines_removed}",
                f"- New notes: {notes_added_count}",
            ]
            if summary_bullets:
                parts.append(summary_bullets)
            if questions_text and questions_text.strip():
                # Add a proper markdown heading and spacing for questions section
                parts.append("")
                parts.append("### Proposed Questions for AI Agent")
                parts.append("")
                parts.append(questions_text.strip())

            summary_block = "\n".join(parts)

            # Update the session summary file with structured append (with error handling)
            t_write_start = time.perf_counter()
            success = False
            try:
                logger.info("Session summary: updating session summary file...")
                success = self.openai_client.update_session_summary(
                    str(target_path),
                    summary_block,
                    change_type="content",
                    settings={"writingStyle": "bullet-points", "summaryLength": "brief", "includeMetrics": True},
                )
                logger.info(f"Session summary: file update success={success}")
            except Exception as e:
                logger.error(f"Failed to update session summary file: {e}")
                # Try a simple fallback write without AI processing
                try:
                    logger.info("Session summary: attempting fallback file write...")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    existing_content = ""
                    if target_path.exists():
                        existing_content = target_path.read_text(encoding='utf-8')
                    
                    # Simple append with timestamp
                    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    new_content = f"{existing_content}\n\n---\n\n## Update: {timestamp_str}\n\n{summary_block}\n"
                    target_path.write_text(new_content, encoding='utf-8')
                    success = True
                    logger.info("Session summary: fallback file write successful")
                except Exception as fallback_error:
                    logger.error(f"Fallback file write also failed: {fallback_error}")
                    success = False
            
            t_write = time.perf_counter() - t_write_start
            logger.info(f"Session summary timing: update_session_summary (file write + semantic index) took {t_write:.3f}s")
            
            if not success:
                return {
                    'success': False,
                    'message': 'Failed to update session summary file',
                    'updated': False
                }

            # Also create individual summary file for pagination
            t_individual_start = time.perf_counter()
            individual_summary_created = self._create_individual_summary(summary_block)
            t_individual = time.perf_counter() - t_individual_start
            logger.info(f"Session summary timing: _create_individual_summary took {t_individual:.3f}s (created={bool(individual_summary_created)})")
            if individual_summary_created:
                logger.info("Individual summary file created successfully")
                # Notify summary note SSE clients
                self._notify_summary_note_clients()

            # Advance cursor
            try:
                t_cursor_start = time.perf_counter()
                latest_ts = diffs[-1]['timestamp'] if diffs else datetime.now().isoformat()
                latest_ts_str = latest_ts if isinstance(latest_ts, str) else latest_ts.isoformat()
                ConfigModel.set('session_summary_last_update', latest_ts_str, 'Session summary last update')
                t_cursor = time.perf_counter() - t_cursor_start
                logger.info(f"Session summary timing: ConfigModel.set cursor update took {t_cursor:.3f}s")
            except Exception:
                ConfigModel.set('session_summary_last_update', datetime.now().isoformat(), 'Session summary last update')

            t_total = time.perf_counter() - t_total_start
            logger.info(f"Session summary timing: total update duration {t_total:.3f}s")
            return {
                'success': True,
                'message': 'Session summary updated from diffs since last check',
                'updated': True,
                'summary': summary_block,
                'individual_summary_created': individual_summary_created
            }

        except Exception as e:
            logger.error(f"Failed to update session summary: {e}")
            raise

    def _create_individual_summary(self, summary_block: str) -> bool:
        """Create an individual summary with dual-write: markdown file + database entry.
        
        Args:
            summary_block: The summary content to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from services.summary_note_service import SummaryNoteService
            from database.models import db
            
            # Create timestamp and formatted content
            now = datetime.now()
            
            # Format content with header and footer
            formatted_content = self._format_individual_summary(summary_block, now)
            
            # Create the markdown summary file (existing functionality)
            summary_service = SummaryNoteService()
            file_result = summary_service.create_summary(formatted_content, now)
            
            if not file_result.get('success', False):
                logger.error("Failed to create markdown summary file")
                return False
            
            # Extract semantic metadata from summary content using AI client (with fallback)
            metadata = {}
            try:
                logger.info("Session summary: extracting semantic metadata...")
                metadata = self.openai_client.extract_semantic_metadata(summary_block)
                logger.info(f"Session summary: semantic metadata extracted: topics={len(metadata.get('topics', []))}, keywords={len(metadata.get('keywords', []))}")
            except Exception as e:
                logger.error(f"Failed to extract semantic metadata (using defaults): {e}")
                # Fallback to basic metadata
                metadata = {
                    'summary': summary_block[:200] if len(summary_block) > 200 else summary_block,
                    'impact': 'moderate',
                    'topics': ['code-changes'],
                    'keywords': ['update', 'changes']
                }
            
            # Get the markdown file path
            markdown_filename = file_result.get('filename', '')
            markdown_file_path = f"output/summaries/{markdown_filename}"
            
            # Create database entry with semantic metadata
            try:
                # Insert semantic entry (connection manager handles transactions)
                semantic_query = """
                    INSERT INTO semantic_entries 
                    (timestamp, date, time, type, summary, impact, file_path, searchable_text, 
                     markdown_file_path, source_type, version_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                # Create searchable text
                searchable_text = f"{metadata.get('summary', '')} {' '.join(metadata.get('topics', []))} {' '.join(metadata.get('keywords', []))} {metadata.get('impact', '')}".lower()
                
                params = (
                    now.isoformat(),
                    now.strftime('%Y-%m-%d'),
                    now.strftime('%H:%M:%S'),
                    'session_summary_summary',
                    metadata.get('summary', summary_block[:200]),  # Fallback to truncated summary_block
                    metadata.get('impact', 'moderate'),
                    markdown_file_path,  # Use markdown file path as file_path
                    searchable_text,
                    markdown_file_path,  # This is the key linking field
                    'session_summary',
                    None  # version_id not applicable for session summaries
                )
                
                db.execute_update(semantic_query, params)
                
                # Get the inserted entry ID
                entry_id_result = db.execute_query("SELECT last_insert_rowid() as id")
                entry_id = entry_id_result[0]['id'] if entry_id_result else None
                
                if entry_id:
                    # Insert topics
                    topics = metadata.get('topics', [])
                    if topics:
                        topic_params = [(entry_id, topic.strip()) for topic in topics if topic.strip()]
                        if topic_params:
                            db.execute_many(
                                "INSERT INTO semantic_topics (entry_id, topic) VALUES (?, ?)",
                                topic_params
                            )
                    
                    # Insert keywords
                    keywords = metadata.get('keywords', [])
                    if keywords:
                        keyword_params = [(entry_id, keyword.strip()) for keyword in keywords if keyword.strip()]
                        if keyword_params:
                            db.execute_many(
                                "INSERT INTO semantic_keywords (entry_id, keyword) VALUES (?, ?)",
                                keyword_params
                            )
                
                logger.info(f"Created hybrid summary: file={markdown_filename}, db_entry={entry_id}, topics={len(metadata.get('topics', []))}, keywords={len(metadata.get('keywords', []))}")
                return True
                
            except Exception as db_error:
                logger.error(f"Database error in dual-write, cleaning up file: {db_error}")
                
                # Clean up the created markdown file since database failed
                try:
                    import os
                    file_path = Path(summary_service.summaries_dir) / markdown_filename
                    if file_path.exists():
                        os.remove(file_path)
                        logger.info(f"Cleaned up orphaned file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up file after database error: {cleanup_error}")
                
                return False
            
        except Exception as e:
            logger.error(f"Failed to create individual summary: {e}")
            return False
    
    def _format_individual_summary(self, summary_block: str, timestamp: datetime) -> str:
        """Format the summary content for individual file storage.
        
        Args:
            summary_block: Raw summary content
            timestamp: Creation timestamp
            
        Returns:
            str: Formatted markdown content
        """
        try:
            # Format timestamp for display
            date_str = timestamp.strftime('%Y-%m-%d %H:%M')
            day_name = timestamp.strftime('%A, %B %d, %Y at %I:%M %p')
            
            # Create formatted content
            content_parts = [
                f"# Summary - {date_str}",
                "",
                f"*Created: {day_name}*",
                "",
                "---",
                "",
                summary_block,
                "",
                "---",
                "",
                "*Generated automatically by Obby*"
            ]
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Failed to format individual summary: {e}")
            return summary_block  # Fallback to original content
    
    def _notify_summary_note_clients(self):
        """Notify summary note SSE clients about new summary creation."""
        try:
            # Import here to avoid circular imports
            from routes.summary_note import notify_summary_note_change
            notify_summary_note_change('created')
        except Exception as e:
            logger.debug(f"Failed to notify summary note clients: {e}")
