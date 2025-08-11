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

    # ---------- Content ----------
    def get_content(self):
        try:
            if self.living_note_path.exists():
                content = self.living_note_path.read_text(encoding='utf-8')
                stat = self.living_note_path.stat()
                last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
            else:
                content = "# Living Note\n\nNo content yet. Start monitoring to see automated summaries appear here."
                last_updated = datetime.now().isoformat()

            return {
                'content': content,
                'path': str(self.living_note_path),
                'exists': self.living_note_path.exists(),
                'lastUpdated': last_updated,
                'wordCount': len(content.split()) if content else 0,
            }
        except Exception as e:
            logger.error(f"Failed to read living note: {e}")
            raise

    def clear(self):
        try:
            self.living_note_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.living_note_path, 'w', encoding='utf-8') as f:
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

            if diffs:
                combined = []
                for d in diffs:
                    combined.append(f"File: {d['filePath']} ({d['timestamp']})\n{d.get('diffContent') or ''}")
                full_diff_content = "\n\n---\n\n".join(combined)
                summary = self.openai_client.summarize_diff(full_diff_content)
            else:
                summary = f"No changes detected since {window_start.isoformat()}"

            # Update the living note file
            success = self.openai_client.update_living_note(str(self.living_note_path), summary)
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
                'summary': summary
            }

        except Exception as e:
            logger.error(f"Failed to update living note: {e}")
            raise



