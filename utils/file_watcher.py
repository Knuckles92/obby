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
    
    def __init__(self, notes_folder, diff_tracker, ai_client, living_note_path, utils_folder=None):
        """
        Initialize the note change handler.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            diff_tracker: DiffTracker instance for processing changes
            ai_client: OpenAIClient instance for generating summaries
            living_note_path: Path to the living note file
            utils_folder: Path to the utils folder (defaults to notes_folder/utils)
        """
        self.notes_folder = Path(notes_folder)
        self.diff_tracker = diff_tracker
        self.ai_client = ai_client
        self.living_note_path = living_note_path
        self.last_event_times = {}  # Track debounce per file
        self.debounce_delay = 0.5  # 500ms debounce to prevent duplicate events
        
        # Set up utils folder path
        if utils_folder is None:
            self.utils_folder = self.notes_folder / "utils"
        else:
            self.utils_folder = Path(utils_folder)
        
        # Initialize handlers
        self.ignore_handler = IgnoreHandler(self.utils_folder, self.notes_folder)
        self.watch_handler = WatchHandler(self.utils_folder)
        
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
                return
                
            self.last_event_times[str(file_path)] = current_time
            self._process_note_change(file_path)
    
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
            self._process_note_change(file_path)
        
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
            # For deleted files, we can't process content but we should log the event
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
    
    def _process_note_change(self, file_path):
        """Process a detected note change."""
        try:
            # Update the diff tracker to work with the specific file
            self.diff_tracker.note_path = file_path
            changed, diff_content = self.diff_tracker.check_for_changes()
            
            if changed:
                logging.debug(f"Processing changes in: {file_path.name}")
                # Get recent tree changes for context
                recent_tree_changes = EventQueries.get_recent_tree_changes(limit=5, time_window_minutes=10)
                # Generate AI summary with tree change context and update living note
                summary = self.ai_client.summarize_diff(diff_content, recent_tree_changes=recent_tree_changes)
                # Store the file path in AI client for semantic indexing
                self.ai_client._current_file_path = str(file_path)
                self.ai_client.update_living_note(self.living_note_path, summary, "content")
            else:
                logging.debug(f"File event detected but no content change in: {file_path.name}")
                
        except Exception as e:
            logging.error(f"Error processing note change in {file_path.name}: {e}")
    
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
            
            # Generate AI summary for the tree change and update living note
            tree_summary = self.ai_client.summarize_tree_change(change_summary)
            self.ai_client.update_living_note(self.living_note_path, tree_summary, "tree")
                
        except Exception as e:
            logging.error(f"Error processing tree change: {e}")


class FileWatcher:
    """Main file watcher class for managing the observer."""
    
    def __init__(self, notes_folder, diff_tracker, ai_client, living_note_path, utils_folder=None):
        """
        Initialize the file watcher.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            diff_tracker: DiffTracker instance
            ai_client: OpenAIClient instance
            living_note_path: Path to the living note file
            utils_folder: Path to the utils folder (defaults to notes_folder/utils)
        """
        self.notes_folder = Path(notes_folder)
        
        # Set up utils folder path
        if utils_folder is None:
            self.utils_folder = self.notes_folder / "utils"
        else:
            self.utils_folder = Path(utils_folder)
        
        self.handler = NoteChangeHandler(notes_folder, diff_tracker, ai_client, living_note_path, self.utils_folder)
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
