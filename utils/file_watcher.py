"""
File system event handler for monitoring note changes.
Uses watchdog for instant, efficient file change detection.
"""

import time
import logging
import os
import sys
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from .ignore_handler import IgnoreHandler
from .watch_handler import WatchHandler
from database.queries import EventQueries


class NoteChangeHandler(FileSystemEventHandler):
    """Handles file system events for note changes."""
    
    def __init__(self, notes_folder, session_summary_path, utils_folder=None, file_tracker=None):
        """
        Initialize the note change handler.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            session_summary_path: Path to the session summary file
            utils_folder: Path to config folder containing .obbywatch/.obbyignore (defaults to project root)
            file_tracker: FileContentTracker instance for change tracking
        """
        self.notes_folder = Path(notes_folder)
        self.session_summary_path = session_summary_path
        self.file_tracker = file_tracker
        self.last_event_times = {}  # Track debounce per file
        self.debounce_delay = 0.5  # 500ms debounce to prevent duplicate events (increased to handle editor patterns)
        self.file_size_cache = {}  # Cache file sizes for quick change detection
        self.file_mtime_cache = {}  # Cache modification times
        
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
            
            # Enhanced validation and debouncing
            current_time = time.time()
            last_time = self.last_event_times.get(str(file_path), 0)
            
            # Debounce rapid-fire events per file (editors often save multiple times)
            if current_time - last_time < self.debounce_delay:
                logging.debug(f"[WATCHDOG] Debounced modification event for {file_path.name} (too recent: {current_time - last_time:.3f}s)")
                return
            
            # Quick pre-validation using file size and modification time
            if not self._has_file_changed_quick(file_path):
                logging.debug(f"[WATCHDOG] Skipped {file_path.name}: no size/mtime change detected")
                return
                
            self.last_event_times[str(file_path)] = current_time
            logging.info(f"[WATCHDOG] Processing file modification: {file_path.name}")
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
            logging.info(f"[WATCHDOG] Note file created: {file_path}")
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
            logging.info(f"[WATCHDOG] Note file deleted: {file_path}")
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
        
        # STRICT: Both source AND destination must be in watched paths for move tracking
        # This prevents files from being moved OUT of watched areas and still being tracked
        src_should_watch = self.watch_handler.should_watch(src_path)
        dest_should_watch = self.watch_handler.should_watch(dest_path)
        
        if not (src_should_watch and dest_should_watch):
            logging.debug(f"Ignoring move: src_watched={src_should_watch}, dest_watched={dest_should_watch}")
            return
        
        # Check if either source or destination is a markdown file
        src_is_md = src_path.suffix.lower() == '.md'
        dest_is_md = dest_path.suffix.lower() == '.md'
        
        if src_is_md or dest_is_md:
            logging.info(f"[WATCHDOG] Note file moved: {src_path} → {dest_path}")
            # If the destination is a markdown file in our folder, process it
            if dest_is_md:
                self._process_note_change(dest_path)
        
        # Log any file move for tree tracking
        self._process_tree_change("moved", event.src_path, dest_path=event.dest_path, is_directory=False)
    
    def _has_file_changed_quick(self, file_path: Path) -> bool:
        """Quick check if file has changed using size and modification time."""
        try:
            if not file_path.exists():
                return True  # File was deleted or moved
                
            stat = file_path.stat()
            current_size = stat.st_size
            current_mtime = stat.st_mtime
            
            file_str = str(file_path)
            cached_size = self.file_size_cache.get(file_str)
            cached_mtime = self.file_mtime_cache.get(file_str)
            
            # Update cache
            self.file_size_cache[file_str] = current_size
            self.file_mtime_cache[file_str] = current_mtime
            
            # Check if file has changed
            if cached_size is None or cached_mtime is None:
                return True  # First time seeing this file
                
            size_changed = current_size != cached_size if FILE_SIZE_CHANGE_VALIDATION else False
            mtime_changed = abs(current_mtime - cached_mtime) > 0.1 if FILE_MTIME_CHANGE_VALIDATION else False  # 100ms tolerance for filesystem precision
            
            if VERBOSE_MONITORING_LOGS:
                logging.debug(f"File change check for {file_path.name}: size_changed={size_changed}, mtime_changed={mtime_changed}")
            
            # Return True if either validation is disabled (to allow content hash validation) or if changes detected
            if not FILE_SIZE_CHANGE_VALIDATION and not FILE_MTIME_CHANGE_VALIDATION:
                return True  # Skip pre-validation, rely on content hash
            return size_changed or mtime_changed
            
        except Exception as e:
            logging.debug(f"Error in quick file change check for {file_path}: {e}")
            return True  # Assume changed if we can't check
    
    def _process_note_change(self, file_path, change_type='modified'):
        """Process a detected note change using file tracker with immediate AI processing."""
        try:
            logging.debug(f"[WATCHDOG] Processing {change_type} change in: {file_path.name}")

            # Use file tracker to process the change
            if self.file_tracker:
                version_id = self.file_tracker.track_file_change(str(file_path), change_type)

                # Enhanced logging for debugging
                if version_id:
                    logging.info(f"[WATCHDOG] Successfully processed {change_type} change in {file_path.name} (version_id: {version_id})")

                    # Broadcast file update to connected clients via SSE
                    self._broadcast_file_update(file_path, change_type)

                else:
                    logging.info(f"[WATCHDOG] File tracker returned None for {change_type} change in {file_path.name} - no content change detected")

            else:
                logging.warning("[WATCHDOG] File tracker not available - change not processed")

        except Exception as e:
            logging.error(f"[WATCHDOG] Error processing note change in {file_path.name}: {e}")

    def _broadcast_file_update(self, file_path, change_type='modified'):
        """Broadcast file update to SSE clients."""
        try:
            # Import here to avoid circular dependency
            from routes.files import notify_file_update, invalidate_file_tree_cache_debounced

            # Calculate relative path from root folder for consistency with frontend
            try:
                from pathlib import Path
                root_folder = Path(__file__).parent.parent
                relative_path = Path(file_path).relative_to(root_folder)
                path_str = str(relative_path).replace('\\', '/')
            except ValueError:
                # Fallback to full path if not within root
                path_str = str(file_path).replace('\\', '/')

            # Read file content if modified/created
            content = None
            if change_type in ['modified', 'created']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logging.warning(f"[WATCHDOG] Could not read file content for SSE broadcast: {e}")

            # Notify SSE clients
            notify_file_update(path_str, event_type=change_type, content=content)
            logging.info(f"[WATCHDOG] Broadcasted {change_type} update for: {path_str}")

            # Invalidate file tree cache with debounce
            invalidate_file_tree_cache_debounced()

        except Exception as e:
            logging.error(f"[WATCHDOG] Failed to broadcast file update: {e}")
    
    
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

            # Invalidate file tree cache when directory structure changes
            if is_directory:
                try:
                    from routes.files import invalidate_file_tree_cache_debounced
                    invalidate_file_tree_cache_debounced()
                    logging.debug(f"[WATCHDOG] Scheduled file tree cache invalidation for directory {event_type}")
                except Exception as e:
                    logging.error(f"[WATCHDOG] Failed to invalidate file tree cache: {e}")

            # Note: AI processing has been decoupled from file monitoring
            # Tree change logging is preserved but AI analysis will be handled separately

        except Exception as e:
            logging.error(f"Error processing tree change: {e}")


class FileWatcher:
    """Main file watcher class for managing the observer."""

    def __init__(self, notes_folder, session_summary_path, utils_folder=None, file_tracker=None):
        """
        Initialize the file watcher.

        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            session_summary_path: Path to the session summary file
            utils_folder: Path to the utils folder (defaults to notes_folder/utils)
            file_tracker: FileContentTracker instance for change tracking
        """
        self.notes_folder = Path(notes_folder)

        # Set up utils folder path
        if utils_folder is None:
            self.utils_folder = self.notes_folder / "utils"
        else:
            self.utils_folder = Path(utils_folder)

        self.handler = NoteChangeHandler(notes_folder, session_summary_path, self.utils_folder, file_tracker)

        # Detect WSL + DrvFS environment and use appropriate observer
        self.observer = self._create_observer()
        self.is_running = False

    def _create_observer(self):
        """
        Create appropriate observer based on environment.

        Uses PollingObserver for WSL+DrvFS (Windows filesystem) since inotify
        doesn't work with DrvFS mounts. Uses regular Observer for native filesystems.

        Returns:
            Observer or PollingObserver instance
        """
        # Check if running on WSL
        is_wsl = False
        try:
            if sys.platform == 'linux':
                with open('/proc/version', 'r') as f:
                    is_wsl = 'microsoft' in f.read().lower() or 'wsl' in f.read().lower()
        except:
            pass

        # Check if path is on DrvFS (Windows filesystem mount)
        is_drvfs = str(self.notes_folder.resolve()).startswith('/mnt/')

        if is_wsl and is_drvfs:
            logging.info("[WATCHDOG] Detected WSL + DrvFS environment - using PollingObserver for compatibility")
            logging.info("[WATCHDOG] PollingObserver will check for file changes every 1 second")
            return PollingObserver(timeout=1.0)  # Check every 1 second
        else:
            logging.info("[WATCHDOG] Using standard Observer with inotify for native filesystem")
            return Observer()
        
    def start(self):
        """Start watching for file changes."""
        if self.is_running:
            return
        
        # Get directories to watch from .obbywatch file
        watch_dirs = self.handler.watch_handler.get_watch_directories()
        
        if not watch_dirs:
            # STRICT MODE: If no watch directories specified, refuse to start
            # This prevents accidentally watching everything when .obbywatch is misconfigured
            logging.error("No watch directories specified in .obbywatch - file watching will not start!")
            logging.error("Please add watch patterns to .obbywatch to enable monitoring")
            return
        
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
