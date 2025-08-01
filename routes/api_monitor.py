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
        """Add an event to the database instead of memory"""
        try:
            file_size = size if size is not None else (
                file_path.stat().st_size if file_path.exists() else 0
            )
        except:
            file_size = 0
            
        # Store event in database instead of memory
        path_str = str(file_path.relative_to(self.notes_folder.parent) if file_path.is_relative_to(self.notes_folder.parent) else file_path)
        
        try:
            EventQueries.add_event(event_type, path_str, file_size)
            logger.debug(f"Added event to database: {event_type} {path_str}")
        except Exception as e:
            logger.error(f"Failed to add event to database: {e}")
            # Log fallback error but don't maintain in-memory storage
            logger.warning(f"Database event storage failed, event lost: {event_type} {path_str}")
    
    def on_modified(self, event):
        """Override to add API event tracking"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('modified', file_path)
        super().on_modified(event)
    
    def on_created(self, event):
        """Override to add API event tracking"""
        file_path = Path(event.src_path)
        if not event.is_directory:
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('created', file_path)
        super().on_created(event)
    
    def on_deleted(self, event):
        """Override to add API event tracking"""
        file_path = Path(event.src_path)
        if not event.is_directory:
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('deleted', file_path, size=0)
        super().on_deleted(event)
    
    def on_moved(self, event):
        """Override to add API event tracking"""
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
        super().on_moved(event)


class APIObbyMonitor(ObbyMonitor):
    """Extended ObbyMonitor that uses API-aware event handler"""
    
    def __init__(self):
        super().__init__()
        # Initialize notes_folder from settings
        from config.settings import NOTES_FOLDER
        self.notes_folder = NOTES_FOLDER
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
            
            # Create file watcher with our custom handler
            self.file_watcher = FileWatcher(
                handler_class=APIAwareNoteChangeHandler,
                notes_folder=self.notes_folder,
                check_interval=self.check_interval
            )
            
            # Start watching
            self.file_watcher.start()
            self.running = True
            
            logger.info(f"API-aware monitoring started for {self.notes_folder}")
            
            # Run the main monitoring loop
            self.run()
            
        except Exception as e:
            logger.error(f"Failed to start API-aware monitoring: {e}")
            self.running = False
            raise
