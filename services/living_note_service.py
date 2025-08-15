import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from ai.openai_client import OpenAIClient


logger = logging.getLogger(__name__)


class LivingNoteService:
    """Service layer for all Living Note operations.

    Centralizes update, content, and settings logic so routes stay thin.
    """

    def __init__(self, living_note_path: str):
        # Base path provided by caller; final path may be dynamically resolved (daily mode)
        self.living_note_path = Path(living_note_path)
        self.settings_path = Path('config/living_note_settings.json')
        self.format_path = Path('config/format.md')
        self.openai_client = OpenAIClient()
        # Ensure format.md is in config if legacy file exists
        try:
            from utils.migrations import migrate_format_md
            migrate_format_md()
        except Exception:
            pass

        # Load dynamic living note configuration (daily vs single file)
        try:
            from config.settings import (
                LIVING_NOTE_MODE,
                LIVING_NOTE_DAILY_DIR,
                LIVING_NOTE_DAILY_FILENAME_TEMPLATE,
                LIVING_NOTE_PATH as LIVING_NOTE_SINGLE_PATH,
            )
            self._LIVING_NOTE_MODE = str(LIVING_NOTE_MODE).lower()
            self._LIVING_NOTE_DAILY_DIR = Path(LIVING_NOTE_DAILY_DIR)
            self._LIVING_NOTE_DAILY_FILENAME_TEMPLATE = LIVING_NOTE_DAILY_FILENAME_TEMPLATE
            self._LIVING_NOTE_SINGLE_PATH = Path(LIVING_NOTE_SINGLE_PATH)
        except Exception:
            # Fallback defaults
            self._LIVING_NOTE_MODE = "single"
            self._LIVING_NOTE_DAILY_DIR = Path('notes/daily')
            self._LIVING_NOTE_DAILY_FILENAME_TEMPLATE = "Living Note - {date}.md"
            self._LIVING_NOTE_SINGLE_PATH = Path('notes/living_note.md')

    def _resolve_living_note_path(self, now: datetime = None) -> Path:
        """Resolve current living note file path based on configured mode."""
        if now is None:
            now = datetime.now()
        if self._LIVING_NOTE_MODE == "daily":
            self._LIVING_NOTE_DAILY_DIR.mkdir(parents=True, exist_ok=True)
            date_str = now.strftime('%Y-%m-%d')
            filename = self._LIVING_NOTE_DAILY_FILENAME_TEMPLATE.format(date=date_str)
            resolved = self._LIVING_NOTE_DAILY_DIR / filename
        else:
            self._LIVING_NOTE_SINGLE_PATH.parent.mkdir(parents=True, exist_ok=True)
            resolved = self._LIVING_NOTE_SINGLE_PATH
        # Cache resolved path
        self.living_note_path = resolved
        return resolved

    # ---------- Content ----------
    def get_content(self):
        try:
            current_path = self._resolve_living_note_path()
            if current_path.exists():
                content = current_path.read_text(encoding='utf-8')
                stat = current_path.stat()
                last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
            else:
                content = "# Living Note\n\nNo content yet. Start monitoring to see automated summaries appear here."
                last_updated = datetime.now().isoformat()

            return {
                'content': content,
                'path': str(current_path),
                'exists': current_path.exists(),
                'lastUpdated': last_updated,
                'wordCount': len(content.split()) if content else 0,
            }
        except Exception as e:
            logger.error(f"Failed to read living note: {e}")
            raise

    def clear(self):
        try:
            current_path = self._resolve_living_note_path()
            current_path.parent.mkdir(parents=True, exist_ok=True)
            with open(current_path, 'w', encoding='utf-8') as f:
                f.write("# Living Note\n\nCleared at " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n")
            return {
                'success': True,
                'message': 'Living note cleared successfully'
            }
        except Exception as e:
            logger.error(f"Failed to clear living note: {e}")
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
            logger.error(f"Failed to get living note settings: {e}")
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
            logger.error(f"Failed to save living note settings: {e}")
            raise

    # ---------- Update ----------
    def update(self, force: bool = False):
        """Update the living note by summarizing diffs since last update.

        Returns dict with success, updated, message, and summary when applicable.
        """
        try:
            # Resolve target path (daily or single)
            target_path = self._resolve_living_note_path()

            # Cursor window
            from database.models import ConfigModel
            last_ts_str = ConfigModel.get('living_note_last_update', None)
            window_start = datetime.fromisoformat(last_ts_str) if last_ts_str else datetime.now() - timedelta(hours=4)

            # Optional file filtering
            watch_handler = None
            try:
                from utils.watch_handler import WatchHandler
                root_folder = Path(__file__).parent.parent
                watch_handler = WatchHandler(root_folder)
            except Exception as e:
                logger.debug(f"Watch patterns unavailable, proceeding without filter: {e}")

            # Fetch diffs
            from database.queries import FileQueries
            diffs = FileQueries.get_diffs_since(window_start, limit=200, watch_handler=watch_handler)

            # Fallback to recent diffs to avoid empty updates
            if not diffs:
                recent_diffs = FileQueries.get_recent_diffs(limit=10, watch_handler=watch_handler)
                if recent_diffs:
                    diffs = recent_diffs
                elif not force:
                    return {
                        'success': True,
                        'message': 'No diffs since last update',
                        'updated': False
                    }
                else:
                    # Proceed with an empty set of diffs when forced
                    diffs = []

            # Build AI context and metrics
            if diffs:
                combined_parts = []
                max_items = min(len(diffs), 12)
                for d in diffs[:max_items]:
                    file_path = d.get('filePath') or d.get('path') or 'unknown'
                    ts = d.get('timestamp') or ''
                    diff_text = d.get('diffContent') or ''
                    if isinstance(diff_text, str) and len(diff_text) > 800:
                        diff_text = diff_text[:800] + "\n..."
                    combined_parts.append(f"File: {file_path} ({ts})\n{diff_text}")
                context_text = "\n\n---\n\n".join(combined_parts)
            else:
                context_text = ""

            total_changes = len(diffs)
            files_affected = len({d.get('filePath') for d in diffs})
            # Filter out zero-change diffs to avoid counting meaningless +0/-0 entries
            meaningful_diffs = [d for d in diffs if int(d.get('linesAdded') or 0) > 0 or int(d.get('linesRemoved') or 0) > 0]
            lines_added = sum(int(d.get('linesAdded') or 0) for d in meaningful_diffs)
            lines_removed = sum(int(d.get('linesRemoved') or 0) for d in meaningful_diffs)
            notes_added_count = len({d.get('filePath') for d in diffs if (str(d.get('changeType')).lower() == 'created' and str(d.get('filePath') or '').lower().endswith('.md'))})

            # AI-generated summary bullets and proposed questions
            summary_bullets = self.openai_client.summarize_minimal(context_text) if context_text else "- no meaningful changes"
            questions_text = self.openai_client.generate_proposed_questions(context_text) if context_text else ""
            
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
                parts.append("### Questions")
                parts.append("")
                parts.append(questions_text.strip())
            summary_block = "\n".join(parts)

            # Update the living note file with structured append
            success = self.openai_client.update_living_note(
                str(target_path),
                summary_block,
                change_type="content",
                settings={"writingStyle": "bullet-points", "summaryLength": "brief", "includeMetrics": True},
                update_type=None,
            )
            if not success:
                return {'success': False, 'message': 'Failed to update living note'}

            # Advance cursor
            try:
                latest_ts = diffs[-1]['timestamp'] if diffs else datetime.now().isoformat()
                latest_ts_str = latest_ts if isinstance(latest_ts, str) else latest_ts.isoformat()
                ConfigModel.set('living_note_last_update', latest_ts_str, 'Living note last update')
            except Exception:
                ConfigModel.set('living_note_last_update', datetime.now().isoformat(), 'Living note last update')

            return {
                'success': True,
                'message': 'Living note updated from diffs since last check',
                'updated': True,
                'summary': summary_block
            }

        except Exception as e:
            logger.error(f"Failed to update living note: {e}")
            raise



