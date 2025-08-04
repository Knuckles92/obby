"""
File system event handler for monitoring note changes.
Uses watchdog for instant, efficient file change detection.
"""

import time
import logging
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from .ignore_handler import IgnoreHandler
from .watch_handler import WatchHandler
from database.queries import EventQueries


class NoteChangeHandler(FileSystemEventHandler):
    """Handles file system events for note changes."""
    
    def __init__(self, notes_folder, ai_client, living_note_path, utils_folder=None, file_tracker=None):
        """
        Initialize the note change handler.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            ai_client: OpenAIClient instance for generating summaries
            living_note_path: Path to the living note file
            utils_folder: Path to config folder containing .obbywatch/.obbyignore (defaults to project root)
            file_tracker: FileContentTracker instance for change tracking
        """
        self.notes_folder = Path(notes_folder)
        self.ai_client = ai_client
        self.living_note_path = living_note_path
        self.file_tracker = file_tracker
        self.last_event_times = {}  # Track debounce per file
        self.debounce_delay = 0.1  # 100ms debounce to prevent duplicate events (reduced for responsiveness)
        
        # Set up config folder path (root directory for .obbywatch/.obbyignore files)
        if utils_folder is None:
            # Default to parent of notes folder (project root)
            self.config_folder = self.notes_folder.parent
        else:
            self.config_folder = Path(utils_folder)
        
        # Initialize handlers
        self.ignore_handler = IgnoreHandler(self.config_folder, self.notes_folder)
        self.watch_handler = WatchHandler(self.config_folder)
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        # Check if the modified file should be watched and is not ignored
        file_path = Path(event.src_path)
        
        # Check if this file should be ignored based on .obbyignore patterns
        if self.ignore_handler.should_ignore(file_path):
            return
        
        # Check if this file should be watched based on .obbywatch patterns
        if not self.watch_handler.should_watch(file_path):
            return
            
        if file_path.suffix.lower() == '.md':
            
            # Debounce rapid-fire events per file (editors often save multiple times)
            current_time = time.time()
            last_time = self.last_event_times.get(str(file_path), 0)
            if current_time - last_time < self.debounce_delay:
                logging.debug(f"Debounced modification event for {file_path.name} (too recent: {current_time - last_time:.3f}s)")
                return
                
            self.last_event_times[str(file_path)] = current_time
            logging.info(f"Processing file modification: {file_path.name}")
            self._process_note_change(file_path, 'modified')
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            logging.info(f"Directory created: {event.src_path}")
            self._process_tree_change("created", event.src_path, is_directory=True)
            return
            
        # If a markdown file is created and should be watched, process it
        file_path = Path(event.src_path)
        
        # Check if this file should be ignored based on .obbyignore patterns
        if self.ignore_handler.should_ignore(file_path):
            return
        
        # Check if this file should be watched based on .obbywatch patterns
        if not self.watch_handler.should_watch(file_path):
            return
            
        if file_path.suffix.lower() == '.md':
            logging.info(f"Note file created: {file_path}")
            self._process_note_change(file_path, 'created')
        
        # Also log any file creation for tree tracking
        self._process_tree_change("created", event.src_path, is_directory=False)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            logging.info(f"Directory deleted: {event.src_path}")
            self._process_tree_change("deleted", event.src_path, is_directory=True)
            return
            
        # If a markdown file is deleted and should be watched, log it
        file_path = Path(event.src_path)
        
        # Check if this file should be ignored based on .obbyignore patterns
        if self.ignore_handler.should_ignore(file_path):
            return
        
        # Check if this file should be watched based on .obbywatch patterns
        if not self.watch_handler.should_watch(file_path):
            return
            
        if file_path.suffix.lower() == '.md':
            logging.info(f"Note file deleted: {file_path}")
            # For deleted files, track the deletion event
            self._process_note_change(file_path, 'deleted')
            self._process_tree_change("deleted", event.src_path, is_directory=False)
        else:
            # Log any file deletion for tree tracking
            self._process_tree_change("deleted", event.src_path, is_directory=False)
    
    def on_moved(self, event):
        """Handle file move/rename events."""
        if event.is_directory:
            logging.info(f"Directory moved: {event.src_path} → {event.dest_path}")
            self._process_tree_change("moved", event.src_path, dest_path=event.dest_path, is_directory=True)
            return
            
        # Handle markdown file moves/renames
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        
        # Check if either source or destination should be ignored based on .obbyignore patterns
        if (self.ignore_handler.should_ignore(src_path) or 
            self.ignore_handler.should_ignore(dest_path)):
            return
        
        # Check if either source or destination should be watched based on .obbywatch patterns
        src_should_watch = self.watch_handler.should_watch(src_path)
        dest_should_watch = self.watch_handler.should_watch(dest_path)
        
        if not (src_should_watch or dest_should_watch):
            return
        
        # Check if either source or destination is a markdown file
        src_is_md = src_path.suffix.lower() == '.md'
        dest_is_md = dest_path.suffix.lower() == '.md'
        
        if src_is_md or dest_is_md:
            logging.info(f"Note file moved: {src_path} → {dest_path}")
            # If the destination is a markdown file in our folder, process it
            if dest_is_md:
                self._process_note_change(dest_path)
        
        # Log any file move for tree tracking
        self._process_tree_change("moved", event.src_path, dest_path=event.dest_path, is_directory=False)
    
    def _process_note_change(self, file_path, change_type='modified'):
        """Process a detected note change using file tracker."""
        try:
            logging.debug(f"Processing {change_type} change in: {file_path.name}")
            
            # Use file tracker to process the change
            if self.file_tracker:
                version_id = self.file_tracker.track_file_change(str(file_path), change_type)
                
                # Log successful diff creation
                if version_id:
                    logging.info(f"✅ Successfully processed {change_type} change in {file_path.name} (version_id: {version_id})")
                else:
                    logging.warning(f"⚠️ File tracker returned None for {change_type} change in {file_path.name} - change may not have been processed")
                
                # Note: AI processing has been decoupled from file monitoring
                # All file tracking, diff generation, and database storage is preserved
                # AI analysis will be handled separately to reduce API usage
            else:
                logging.warning("File tracker not available, using legacy processing")
                # Fallback to legacy processing if no file tracker
                self._legacy_process_note_change(file_path)
                
        except Exception as e:
            logging.error(f"Error processing note change in {file_path.name}: {e}")
    
    def _legacy_process_note_change(self, file_path):
        """Legacy processing method for when file tracker is not available."""
        # Note: AI processing has been decoupled from file monitoring
        # Legacy method preserved for compatibility but without AI calls
        logging.info(f"Legacy processing for {file_path.name} - AI analysis will be handled separately")
    
    def _process_tree_change(self, event_type, src_path, dest_path=None, is_directory=False):
        """Process a detected file tree change."""
        try:
            # Create a summary of the tree change
            path_type = "directory" if is_directory else "file"
            
            if event_type == "moved":
                change_summary = f"File tree change: {path_type} moved from {src_path} to {dest_path}"
            else:
                change_summary = f"File tree change: {path_type} {event_type} at {src_path}"
            
            logging.info(f"{change_summary}")
            
            # Note: AI processing has been decoupled from file monitoring
            # Tree change logging is preserved but AI analysis will be handled separately
                
        except Exception as e:
            logging.error(f"Error processing tree change: {e}")


class FileWatcher:
    """Main file watcher class for managing the observer."""
    
    def __init__(self, notes_folder, ai_client, living_note_path, utils_folder=None, file_tracker=None):
        """
        Initialize the file watcher.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            ai_client: OpenAIClient instance
            living_note_path: Path to the living note file
            utils_folder: Path to the utils folder (defaults to notes_folder/utils)
            file_tracker: FileContentTracker instance for change tracking
        """
        self.notes_folder = Path(notes_folder)
        
        # Set up utils folder path
        if utils_folder is None:
            self.utils_folder = self.notes_folder / "utils"
        else:
            self.utils_folder = Path(utils_folder)
        
        self.handler = NoteChangeHandler(notes_folder, ai_client, living_note_path, self.utils_folder, file_tracker)
        self.observer = Observer()
        self.is_running = False
        
    def start(self):
        """Start watching for file changes."""
        if self.is_running:
            return
        
        # Get directories to watch from .obbywatch file
        watch_dirs = self.handler.watch_handler.get_watch_directories()
        
        if not watch_dirs:
            # If no watch directories specified, fall back to notes folder
            watch_dirs = [self.notes_folder]
            logging.warning(f"No watch directories specified in .obbywatch, watching default: {self.notes_folder}")
        
        # Schedule watching for each directory
        for watch_dir in watch_dirs:
            if watch_dir.exists():
                logging.info(f"Watching directory: {watch_dir}")
                self.observer.schedule(self.handler, str(watch_dir), recursive=True)
            else:
                logging.warning(f"Watch directory does not exist: {watch_dir}")
        
        self.observer.start()
        self.is_running = True
        
        # Count existing markdown files
        md_files = list(self.notes_folder.glob('*.md'))
        logging.info(f"File watcher started - monitoring {len(md_files)} markdown files in {self.notes_folder}")
        logging.info("Real-time change detection active for all .md files!")
        
    def stop(self):
        """Stop watching for file changes."""
        if not self.is_running:
            return
            
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        logging.info("File watcher stopped")
        
    def wait(self):
        """Wait for the observer to finish (blocking)."""
        if self.is_running:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
