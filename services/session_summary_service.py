import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import time

from ai.claude_agent_client import ClaudeAgentClient
from utils.claude_summary_parser import ClaudeSummaryParser
from utils.summary_context import SummaryContextConfig


logger = logging.getLogger(__name__)


class SessionSummaryService:
    """Service layer for all Session Summary operations.

    Centralizes update, content, and settings logic so routes stay thin.
    Now powered by Claude Agent SDK for autonomous file exploration.
    """

    def __init__(self, session_summary_path: str):
        # Base path provided by caller; final path may be dynamically resolved (daily mode)
        self.session_summary_path = Path(session_summary_path)
        self.settings_path = Path('config/session_summary_settings.json')
        self.format_path = Path('config/format.md')
        # Initialize Claude Agent client
        self.claude_client = ClaudeAgentClient(working_dir=Path.cwd())
        logger.info("Session summary service initialized with Claude Agent SDK")
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

    # ---------- Preview ----------
    def generate_preview(self, context_config: SummaryContextConfig = None):
        """Generate a preview of what will be included in the summary.

        Args:
            context_config: Summary context configuration (uses default if None)

        Returns:
            Preview data dict with matched files, stats, and warnings
        """
        try:
            # Use default config if not provided
            if context_config is None:
                context_config = SummaryContextConfig.default()

            # Initialize watch handler
            watch_handler = None
            try:
                from utils.watch_handler import WatchHandler
                root_folder = Path(__file__).parent.parent
                watch_handler = WatchHandler(root_folder)
            except Exception as e:
                logger.debug(f"Watch patterns unavailable: {e}")

            # Get preview data from FileQueries
            from database.queries import FileQueries
            preview_data = FileQueries.get_preview_data(context_config, watch_handler)

            logger.info(f"Generated preview: {preview_data.get('total_files', 0)} files matched")
            return preview_data

        except Exception as e:
            logger.error(f"Failed to generate preview: {e}")
            raise

    # ---------- Update ----------
    def update(self, force: bool = False, context_config: SummaryContextConfig = None):
        """Update the session summary by having Claude explore changed files.

        Args:
            force: Force update even if no changes detected
            context_config: Optional context configuration for custom time/file filtering

        Returns dict with success, updated, message, and summary when applicable.

        Note: This method wraps the async _update_async() for backward compatibility.
        """
        try:
            # Run async update in event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._update_async(force, context_config))
                    return future.result()
            else:
                # Run in the current event loop
                return loop.run_until_complete(self._update_async(force, context_config))
        except Exception as e:
            logger.error(f"Failed to update session summary: {e}")
            raise

    async def _update_async(self, force: bool = False, context_config: SummaryContextConfig = None):
        """Async implementation of session summary update using Claude Agent SDK.

        Args:
            force: Force update even if no changes detected
            context_config: Optional context configuration for custom time/file filtering

        Returns dict with success, updated, message, and summary when applicable.
        """
        try:
            t_total_start = time.perf_counter()

            # Check Claude availability
            if not self.claude_client.is_available():
                logger.error("Claude Agent SDK not available - check API key and installation")
                return {
                    'success': False,
                    'message': 'Claude Agent SDK not available',
                    'updated': False
                }

            logger.info("Session summary update: Claude Agent SDK ready")

            # Resolve target path (daily or single)
            target_path = self._resolve_session_summary_path()

            # Determine time window based on context_config or cursor
            from database.models import ConfigModel

            if context_config is not None:
                # Use custom context configuration
                logger.info("Using custom context configuration for summary")
                use_custom_context = True

                # Parse time window from context_config
                time_window = context_config.time_window
                if time_window.preset and time_window.preset != "custom" and time_window.preset != "auto":
                    # Parse preset (e.g., "1h", "6h", "24h", "7d")
                    preset = time_window.preset
                    if preset.endswith('h'):
                        hours = int(preset[:-1])
                        window_start = datetime.now() - timedelta(hours=hours)
                    elif preset.endswith('d'):
                        days = int(preset[:-1])
                        window_start = datetime.now() - timedelta(days=days)
                    else:
                        window_start = datetime.now() - timedelta(hours=4)  # Default
                    window_end = datetime.now()

                    # If include_previously_covered is False (default), restrict to changes since last summary
                    if not time_window.include_previously_covered:
                        last_ts_str = ConfigModel.get('session_summary_last_update', None)
                        if last_ts_str:
                            last_summary_time = datetime.fromisoformat(last_ts_str)
                            # Use the more restrictive (later) of the two timestamps
                            if last_summary_time > window_start:
                                logger.info(f"Restricting time window to changes since last summary: {last_summary_time}")
                                window_start = last_summary_time
                elif time_window.preset == "auto":
                    # Auto = since last update (cursor-based)
                    last_ts_str = ConfigModel.get('session_summary_last_update', None)
                    window_start = datetime.fromisoformat(last_ts_str) if last_ts_str else datetime.now() - timedelta(hours=4)
                    window_end = datetime.now()
                else:
                    # Custom date range
                    window_start = time_window.start_date or (datetime.now() - timedelta(hours=4))
                    window_end = time_window.end_date or datetime.now()

                    # If include_previously_covered is False, restrict to changes since last summary
                    if not time_window.include_previously_covered:
                        last_ts_str = ConfigModel.get('session_summary_last_update', None)
                        if last_ts_str:
                            last_summary_time = datetime.fromisoformat(last_ts_str)
                            # Use the more restrictive (later) of the two timestamps
                            if last_summary_time > window_start:
                                logger.info(f"Restricting custom time window to changes since last summary: {last_summary_time}")
                                window_start = last_summary_time
            else:
                # Use default cursor-based window (backward compatibility)
                logger.info("Using cursor-based window (default behavior)")
                use_custom_context = False
                last_ts_str = ConfigModel.get('session_summary_last_update', None)
                window_start = datetime.fromisoformat(last_ts_str) if last_ts_str else datetime.now() - timedelta(hours=4)
                window_end = datetime.now()

            # Calculate time range for Claude
            time_elapsed = window_end - window_start
            if time_elapsed.days > 0:
                time_range = f"last {time_elapsed.days} days"
            elif time_elapsed.seconds > 3600:
                hours = time_elapsed.seconds // 3600
                time_range = f"last {hours} hours"
            else:
                minutes = time_elapsed.seconds // 60
                time_range = f"last {minutes} minutes"

            # Optional file filtering
            watch_handler = None
            try:
                from utils.watch_handler import WatchHandler
                root_folder = Path(__file__).parent.parent
                watch_handler = WatchHandler(root_folder)
                logger.info(f"Session summary: initialized WatchHandler with root_folder: {root_folder}")
                logger.info(f"Session summary: loaded watch patterns: {watch_handler.watch_patterns}")
            except Exception as e:
                logger.debug(f"Watch patterns unavailable, proceeding without filter: {e}")

            # Fetch changed files using appropriate method based on context_config
            from database.queries import FileQueries
            t_query_start = time.perf_counter()

            if use_custom_context:
                # Use get_diffs_in_range with custom filters
                logger.info(f"Session summary: using get_diffs_in_range with custom context")
                all_diffs = FileQueries.get_diffs_in_range(
                    start_time=window_start,
                    end_time=window_end,
                    file_filters=context_config.file_filters,
                    content_type_filters=context_config.content_types,
                    max_files=context_config.scope_controls.max_files,
                    watch_handler=watch_handler
                )
            else:
                # Use get_diffs_since for cursor-based approach (backward compatibility)
                logger.info(f"Session summary: using get_diffs_since (cursor-based)")
                all_diffs = FileQueries.get_diffs_since(window_start, limit=200, watch_handler=watch_handler)

            t_query = time.perf_counter() - t_query_start
            logger.info(f"Session summary timing: query took {t_query:.3f}s (window_start={window_start.isoformat()}, window_end={window_end.isoformat()})")

            # Extract unique file paths, excluding session summary and internal files
            target_path = self._resolve_session_summary_path().resolve()
            changed_files = []
            excluded_count = 0
            seen_paths = set()

            for diff in all_diffs:
                file_path = diff.get('filePath') or diff.get('path')
                if not file_path:
                    continue

                file_path_resolved = Path(file_path).resolve()
                file_path_str = str(file_path_resolved)

                # Skip if already seen
                if file_path_str in seen_paths:
                    continue

                # Exclude session summary file itself
                if file_path_resolved == target_path:
                    excluded_count += 1
                    logger.debug(f"Excluding session summary file: {file_path_str}")
                    continue

                # Exclude internal semantic index
                if file_path_str.lower().endswith('semantic_index.json'):
                    excluded_count += 1
                    logger.debug(f"Excluding semantic index file: {file_path_str}")
                    continue

                # Only include markdown files
                if not file_path_str.lower().endswith('.md'):
                    excluded_count += 1
                    continue

                changed_files.append(file_path_str)
                seen_paths.add(file_path_str)

            logger.info(f"Session summary: excluded {excluded_count} files, {len(changed_files)} files for Claude to explore")

            # Fallback to recent files if none found
            if not changed_files:
                t_recent_start = time.perf_counter()
                all_recent_diffs = FileQueries.get_recent_diffs(limit=10, watch_handler=watch_handler)
                t_recent = time.perf_counter() - t_recent_start
                logger.info(f"Session summary timing: get_recent_diffs took {t_recent:.3f}s")

                seen_paths = set()
                for diff in all_recent_diffs:
                    file_path = diff.get('filePath') or diff.get('path')
                    if not file_path:
                        continue

                    file_path_resolved = Path(file_path).resolve()
                    file_path_str = str(file_path_resolved)

                    if file_path_str in seen_paths:
                        continue
                    if file_path_resolved == target_path:
                        continue
                    if file_path_str.lower().endswith('semantic_index.json'):
                        continue
                    if not file_path_str.lower().endswith('.md'):
                        continue

                    changed_files.append(file_path_str)
                    seen_paths.add(file_path_str)

                if changed_files:
                    logger.info(f"Session summary: using {len(changed_files)} recent files as fallback")
                elif not force:
                    return {
                        'success': True,
                        'message': 'No files changed since last update',
                        'updated': False
                    }
                else:
                    logger.info("Session summary: forced update requested but no files found")
                    return {
                        'success': True,
                        'message': 'No new changes to summarize',
                        'updated': False,
                        'individual_summary_created': False
                    }

            # Limit files to avoid excessive API usage
            from config import settings as cfg
            max_files = cfg.MAX_FILES_PER_SUMMARY
            if len(changed_files) > max_files:
                logger.info(f"Session summary: limiting from {len(changed_files)} to {max_files} files")
                changed_files = changed_files[:max_files]

            # Calculate metrics from diffs
            total_changes = len(all_diffs)
            files_affected = len(changed_files)
            meaningful_diffs = [d for d in all_diffs if int(d.get('linesAdded') or 0) > 0 or int(d.get('linesRemoved') or 0) > 0]
            lines_added = sum(int(d.get('linesAdded') or 0) for d in meaningful_diffs)
            lines_removed = sum(int(d.get('linesRemoved') or 0) for d in meaningful_diffs)
            notes_added_count = len({d.get('filePath') for d in all_diffs if (str(d.get('changeType')).lower() == 'created' and str(d.get('filePath') or '').lower().endswith('.md'))})

            # Build context metadata for Claude if custom context is used
            context_metadata = None
            if use_custom_context and context_config is not None:
                # Build human-readable filter descriptions
                filters_applied = []

                if context_config.file_filters.include_patterns:
                    patterns = ', '.join(context_config.file_filters.include_patterns)
                    filters_applied.append(f"Include: {patterns}")

                if context_config.file_filters.exclude_patterns:
                    patterns = ', '.join(context_config.file_filters.exclude_patterns)
                    filters_applied.append(f"Exclude: {patterns}")

                content_types_list = []
                if context_config.content_types.include_code_files:
                    content_types_list.append("code files")
                if context_config.content_types.include_documentation:
                    content_types_list.append("documentation")
                if context_config.content_types.include_deleted:
                    content_types_list.append("deleted files")

                if content_types_list:
                    filters_applied.append(f"Content types: {', '.join(content_types_list)}")

                # Build context metadata dict
                context_metadata = {
                    'time_window_description': time_range,
                    'filters_applied': filters_applied,
                    'scope_controls': {
                        'max_files': context_config.scope_controls.max_files,
                        'detail_level': context_config.scope_controls.detail_level,
                        'focus_areas': context_config.scope_controls.focus_areas or []
                    },
                    'change_stats': {
                        'total_files': len(all_diffs),
                        'files_analyzed': len(changed_files)
                    }
                }
                logger.info(f"Session summary: prepared context metadata with {len(filters_applied)} filters")

            # Check if we should include previous summaries (from context_config or settings)
            previous_summaries = None
            include_previous = False
            
            # Check context_config first (preferred), then fall back to settings
            if context_config is not None:
                include_previous = getattr(context_config, 'include_previous_summaries', False)
            else:
                try:
                    settings = self.get_settings()
                    include_previous = settings.get('settings', {}).get('includePreviousSummaries', False)
                except Exception as e:
                    logger.debug(f"Session summary: failed to check settings for includePreviousSummaries: {e}")
            
            if include_previous:
                # Read existing summary file content (excluding the header)
                target_path = self._resolve_session_summary_path()
                if target_path.exists():
                    existing_content = target_path.read_text(encoding='utf-8')
                    # Extract summaries (everything after the initial header/description)
                    # Split by "---" separators to get individual summary blocks
                    parts = existing_content.split('\n---\n')
                    if len(parts) > 1:
                        # Skip the first part (header) and get all previous summaries
                        previous_summaries = '\n---\n'.join(parts[1:]).strip()
                        if previous_summaries:
                            logger.info(f"Session summary: including {len(parts) - 1} previous summary sections")
                        else:
                            previous_summaries = None
                            logger.info("Session summary: includePreviousSummaries enabled but no previous summaries found")
                    else:
                        logger.info("Session summary: includePreviousSummaries enabled but file contains only header")
                else:
                    logger.info("Session summary: includePreviousSummaries enabled but summary file doesn't exist yet")

            # Call Claude to generate session summary by exploring files
            t_claude_start = time.perf_counter()
            claude_summary_md = ""

            try:
                logger.info(f"Session summary: calling Claude to explore {len(changed_files)} files...")
                logger.info(f"Session summary: time range = '{time_range}'")
                if context_metadata:
                    logger.info(f"Session summary: passing context metadata with {len(context_metadata.get('filters_applied', []))} filters")
                if previous_summaries:
                    logger.info(f"Session summary: including previous summaries ({len(previous_summaries)} characters)")

                claude_summary_md = await self.claude_client.summarize_session(
                    changed_files=changed_files,
                    time_range=time_range,
                    working_dir=Path.cwd(),
                    context_metadata=context_metadata,
                    previous_summaries=previous_summaries
                )

                logger.info("Session summary: Claude summary generated successfully")
                t_claude = time.perf_counter() - t_claude_start
                logger.info(f"Session summary timing: Claude summarize_session took {t_claude:.3f}s")

            except Exception as e:
                logger.error(f"Failed to generate Claude summary: {e}", exc_info=True)
                t_claude = time.perf_counter() - t_claude_start
                logger.info(f"Session summary timing: Claude call failed after {t_claude:.3f}s")

                # Fallback to basic summary
                claude_summary_md = f"""## Code Changes

**Summary**: {files_affected} files changed during the {time_range} period.

**Change Pattern**: Code modifications

**Impact Assessment**:
- **Scope**: moderate
- **Complexity**: moderate
- **Risk Level**: low

**Topics**: Code Changes

**Technical Keywords**: {', '.join(changed_files[:5])}

**Relationships**: Multiple files modified.

### Sources

{chr(10).join([f"- `{f}` — File modified in this session" for f in changed_files[:10]])}

### Proposed Questions

- What were the main goals of these changes?
- Are there any related files that should be reviewed?

**Note**: Generated as fallback due to error: {str(e)}"""
            
            # Parse Claude's structured summary
            parsed_summary = ClaudeSummaryParser.parse_session_summary(claude_summary_md)
            logger.info(f"Session summary: parsed {len(parsed_summary.get('topics', []))} topics, {len(parsed_summary.get('sources', []))} sources")

            # Build final summary block with Claude's output + metrics
            # Claude's summary is already complete markdown, we just append metrics
            summary_block = claude_summary_md.strip()

            # Append metrics section after Claude's output
            metrics_section = f"""

### Metrics

- Total changes: {total_changes}
- Files affected: {files_affected}
- Lines: +{lines_added}/-{lines_removed}
- New notes: {notes_added_count}"""

            summary_block += metrics_section

            # Write summary to file
            t_write_start = time.perf_counter()
            success = False
            try:
                logger.info("Session summary: writing to file...")
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Create or read existing file
                if not target_path.exists():
                    today = datetime.now().strftime("%Y-%m-%d")
                    initial_content = f"# Session Summary - {today}\n\nThis file contains AI-generated summaries of your development sessions.\n\n---\n\n"
                    existing_content = initial_content
                else:
                    existing_content = target_path.read_text(encoding='utf-8')

                # Append new summary with timestamp separator
                timestamp_str = datetime.now().strftime('%Y-%m-%d %I:%M %p')
                new_content = f"{existing_content}\n\n---\n\n**Update: {timestamp_str}**\n\n{summary_block}\n"

                target_path.write_text(new_content, encoding='utf-8')
                success = True
                logger.info("Session summary: file written successfully")

            except Exception as e:
                logger.error(f"Failed to write session summary file: {e}", exc_info=True)
                success = False

            t_write = time.perf_counter() - t_write_start
            logger.info(f"Session summary timing: file write took {t_write:.3f}s")
            
            if not success:
                return {
                    'success': False,
                    'message': 'Failed to update session summary file',
                    'updated': False
                }

            # Also create individual summary file for pagination with parsed metadata
            t_individual_start = time.perf_counter()
            individual_summary_created = self._create_individual_summary(
                summary_block,
                parsed_metadata=parsed_summary,
                context_config=context_config
            )
            t_individual = time.perf_counter() - t_individual_start
            logger.info(f"Session summary timing: _create_individual_summary took {t_individual:.3f}s (created={bool(individual_summary_created)})")
            if individual_summary_created:
                logger.info("Individual summary file created successfully")
                # Notify summary note SSE clients
                self._notify_summary_note_clients()

            # Advance cursor
            try:
                t_cursor_start = time.perf_counter()
                latest_ts = all_diffs[-1]['timestamp'] if all_diffs else datetime.now().isoformat()
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
                'message': 'Session summary updated with Claude exploration',
                'updated': True,
                'summary': summary_block,
                'parsed_summary': parsed_summary,
                'individual_summary_created': individual_summary_created
            }

        except Exception as e:
            logger.error(f"Failed to update session summary: {e}", exc_info=True)
            raise

    def _create_individual_summary(self, summary_block: str, parsed_metadata: dict = None, context_config: SummaryContextConfig = None) -> bool:
        """Create an individual summary with dual-write: markdown file + database entry.

        Args:
            summary_block: The summary content to save
            parsed_metadata: Optional parsed summary metadata from Claude
            context_config: Optional context configuration used for generation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from services.summary_note_service import SummaryNoteService
            from database.models import db
            
            # Create timestamp and formatted content
            now = datetime.now()

            # Format content with header and footer
            formatted_content = self._format_individual_summary(summary_block, now, context_config)
            
            # Create the markdown summary file (existing functionality)
            summary_service = SummaryNoteService()
            file_result = summary_service.create_summary(formatted_content, now)
            
            if not file_result.get('success', False):
                logger.error("Failed to create markdown summary file")
                return False
            
            # Use parsed Claude metadata if available, otherwise extract from text
            metadata = {}
            if parsed_metadata:
                # Use metadata extracted from Claude's structured output
                logger.info("Session summary: using parsed Claude metadata")
                metadata = ClaudeSummaryParser.extract_semantic_metadata(parsed_metadata)
                # Add summary field (limit to 200 chars for compatibility)
                metadata['summary'] = parsed_metadata.get('summary', summary_block[:200])
                # Map new impact fields to legacy 'impact' field for compatibility
                metadata['impact'] = parsed_metadata.get('impact_scope', 'moderate')
                logger.info(f"Session summary: Claude metadata: topics={len(metadata.get('topics', []))}, keywords={len(metadata.get('keywords', []))}")
            else:
                # Fallback: parse from markdown text
                logger.info("Session summary: parsing metadata from markdown")
                try:
                    parsed = ClaudeSummaryParser.parse_session_summary(summary_block)
                    metadata = ClaudeSummaryParser.extract_semantic_metadata(parsed)
                    metadata['summary'] = parsed.get('summary', summary_block[:200])
                    metadata['impact'] = parsed.get('impact_scope', 'moderate')
                except Exception as e:
                    logger.error(f"Failed to parse metadata (using defaults): {e}")
                    # Ultimate fallback
                    metadata = {
                        'summary': summary_block[:200] if len(summary_block) > 200 else summary_block,
                        'impact': 'moderate',
                        'impact_scope': 'moderate',
                        'impact_complexity': 'moderate',
                        'impact_risk': 'low',
                        'topics': ['code-changes'],
                        'keywords': ['update', 'changes'],
                        'change_pattern': 'Code modifications'
                    }
            
            # Get the markdown file path
            markdown_filename = file_result.get('filename', '')
            markdown_file_path = f"output/summaries/{markdown_filename}"

            # Convert context_config to JSON if provided
            context_metadata_json = None
            if context_config is not None:
                try:
                    context_metadata_json = context_config.to_json()
                    logger.info("Stored context_metadata in summary")
                except Exception as e:
                    logger.warning(f"Failed to serialize context_config: {e}")

            # Create database entry with semantic metadata
            try:
                # Insert semantic entry (connection manager handles transactions)
                semantic_query = """
                    INSERT INTO semantic_entries
                    (timestamp, date, time, type, summary, impact, file_path, searchable_text,
                     markdown_file_path, source_type, version_id, context_metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    None,  # version_id not applicable for session summaries
                    context_metadata_json  # Store context configuration as JSON
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
    
    def _format_individual_summary(self, summary_block: str, timestamp: datetime, context_config: SummaryContextConfig = None) -> str:
        """Format the summary content for individual file storage.

        Args:
            summary_block: Raw summary content
            timestamp: Creation timestamp
            context_config: Optional context configuration used for generation

        Returns:
            str: Formatted markdown content
        """
        try:
            # Format timestamp for display
            date_str = timestamp.strftime('%Y-%m-%d %H:%M')
            day_name = timestamp.strftime('%A, %B %d, %Y at %I:%M %p')

            # Build content parts
            content_parts = [
                f"# Summary - {date_str}",
                "",
                f"*Created: {day_name}*",
                ""
            ]

            # Add generation context section if context_config provided
            if context_config is not None:
                content_parts.extend([
                    "## Generation Context",
                    ""
                ])

                # Time window info
                time_desc = context_config.time_window.get_description()
                content_parts.append(f"**Time Range**: {time_desc}")

                # File filters
                if context_config.file_filters.include_patterns:
                    patterns = ', '.join(f"`{p}`" for p in context_config.file_filters.include_patterns)
                    content_parts.append(f"**Include Patterns**: {patterns}")

                if context_config.file_filters.exclude_patterns:
                    patterns = ', '.join(f"`{p}`" for p in context_config.file_filters.exclude_patterns)
                    content_parts.append(f"**Exclude Patterns**: {patterns}")

                # Content type filters
                content_types = []
                if context_config.content_types.include_code_files:
                    content_types.append("code")
                if context_config.content_types.include_documentation:
                    content_types.append("documentation")
                if context_config.content_types.include_deleted:
                    content_types.append("deleted files")
                if content_types:
                    content_parts.append(f"**Content Types**: {', '.join(content_types)}")

                # Scope controls
                content_parts.append(f"**Max Files**: {context_config.scope_controls.max_files}")
                content_parts.append(f"**Detail Level**: {context_config.scope_controls.detail_level}")

                if context_config.scope_controls.focus_areas:
                    focus = ', '.join(f"`{a}`" for a in context_config.scope_controls.focus_areas)
                    content_parts.append(f"**Focus Areas**: {focus}")

                content_parts.extend(["", "---", ""])

            else:
                # Default separator if no context config
                content_parts.extend(["---", ""])

            # Add summary content
            content_parts.extend([
                summary_block,
                "",
                "---",
                "",
                "*Generated automatically by Obby*"
            ])

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
