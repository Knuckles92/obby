"""
API-aware monitoring classes
Extended monitoring classes that integrate with the API's event system
"""

import logging
from pathlib import Path
from core.monitor import ObbyMonitor
from utils.file_watcher import NoteChangeHandler
from database.queries import EventQueries

logger = logging.getLogger(__name__)


class APIAwareNoteChangeHandler(NoteChangeHandler):
    """Extended handler that also updates the API's event list"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def _add_event(self, event_type, file_path, size=None):
        """Add an event to the database for API tracking (in addition to content diff generation)"""
        try:
            file_size = size if size is not None else (
                file_path.stat().st_size if file_path.exists() else 0
            )
        except:
            file_size = 0
            
        # Store basic event in database for API compatibility
        path_str = str(file_path.relative_to(self.notes_folder.parent) if file_path.is_relative_to(self.notes_folder.parent) else file_path)
        
        try:
            EventQueries.add_event(event_type, path_str, file_size)
            logger.debug(f"Added API event to database: {event_type} {path_str}")
        except Exception as e:
            logger.error(f"Failed to add API event to database: {e}")

    def on_modified(self, event):
        """Override to add API event tracking while preserving content diff generation"""
        # First call parent to generate content diffs via file_tracker
        super().on_modified(event)
        
        # Then add basic event for API tracking  
        if not event.is_directory:
            file_path = Path(event.src_path)
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('modified', file_path)
    
    def on_created(self, event):
        """Override to add API event tracking while preserving content diff generation"""
        # First call parent to generate content diffs via file_tracker
        super().on_created(event)
        
        # Then add basic event for API tracking
        file_path = Path(event.src_path)
        if not event.is_directory:
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('created', file_path)
    
    def on_deleted(self, event):
        """Override to add API event tracking while preserving content diff generation"""
        # First call parent to generate content diffs via file_tracker
        super().on_deleted(event)
        
        # Then add basic event for API tracking
        file_path = Path(event.src_path)
        if not event.is_directory:
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('deleted', file_path, size=0)
    
    def on_moved(self, event):
        """Override to add API event tracking while preserving content diff generation"""
        # First call parent to generate content diffs via file_tracker  
        super().on_moved(event)
        
        # Then add basic event for API tracking
        if not event.is_directory:
            src_path = Path(event.src_path)
            dest_path = Path(event.dest_path)
            
            # Check both paths
            src_ignored = self.ignore_handler.should_ignore(src_path)
            dest_ignored = self.ignore_handler.should_ignore(dest_path)
            src_watched = self.watch_handler.should_watch(src_path)
            dest_watched = self.watch_handler.should_watch(dest_path)
            
            if (not src_ignored and src_watched) or (not dest_ignored and dest_watched):
                if src_path.suffix.lower() == '.md' or dest_path.suffix.lower() == '.md':
                    self._add_event('moved', dest_path)


class APIObbyMonitor(ObbyMonitor):
    """Extended ObbyMonitor that uses API-aware event handler"""
    
    def __init__(self):
        super().__init__()
        # Initialize notes_folder from settings
        from config.settings import get_configured_notes_folder
        self.notes_folder = get_configured_notes_folder()
        # Load check interval from config if available
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.json"""
        try:
            from database.queries import ConfigQueries
            config = ConfigQueries.get_config()
            if config and 'check_interval' in config:
                self.check_interval = config['check_interval']
                logger.info(f"Loaded check interval from config: {self.check_interval}")
        except Exception as e:
            logger.warning(f"Could not load config from database: {e}")
            # Use default from settings
            from config.settings import CHECK_INTERVAL
            self.check_interval = CHECK_INTERVAL
    
    def start(self):
        """Start the monitoring system with API integration"""
        try:
            # Use our custom API-aware handler
            from utils.file_watcher import FileWatcher
            from ai.openai_client import OpenAIClient
            from utils.living_note_path import resolve_living_note_path
            
            # Initialize AI client
            ai_client = OpenAIClient()
            self.ai_client = ai_client
            
            # Create file watcher with correct parameters  
            utils_folder = self.notes_folder.parent  # Use root directory for config files
            self.file_watcher = FileWatcher(
                notes_folder=self.notes_folder,
                ai_client=ai_client,
                living_note_path=resolve_living_note_path(),
                utils_folder=utils_folder
            )
            
            # Replace the default handler with our API-aware handler
            self.file_watcher.handler = APIAwareNoteChangeHandler(
                notes_folder=self.notes_folder,
                ai_client=ai_client,
                living_note_path=resolve_living_note_path(),
                utils_folder=utils_folder,
                file_tracker=self.file_tracker  # Pass file_tracker for content diff generation
            )
            
            # Start watching (no batch AI scheduler here; Living Note updates are triggered explicitly)
            self.file_watcher.start()
            self.is_running = True
            
            logger.info(f"API-aware monitoring started for {self.notes_folder}")
            
        except Exception as e:
            logger.error(f"Failed to start API-aware monitoring: {e}")
            self.is_running = False
            raise
