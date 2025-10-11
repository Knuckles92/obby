"""
File system event handler for monitoring note changes.
Uses watchdog for instant, efficient file change detection.
"""

import time
import logging
import os
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
                    
                    # Trigger immediate AI processing if AI client is available
                    if self.ai_client and change_type in ['created', 'modified']:
                        self._process_with_ai_immediate(str(file_path), version_id)
                    
                else:
                    logging.info(f"[WATCHDOG] File tracker returned None for {change_type} change in {file_path.name} - no content change detected")
                
            else:
                logging.warning("[WATCHDOG] File tracker not available, using legacy processing")
                # Fallback to legacy processing if no file tracker
                self._legacy_process_note_change(file_path)
                
        except Exception as e:
            logging.error(f"[WATCHDOG] Error processing note change in {file_path.name}: {e}")
    
    def _process_with_ai_immediate(self, file_path: str, version_id: int):
        """Process file content immediately with AI for semantic analysis."""
        try:
            if not self.ai_client:
                logging.debug(f"AI client not available for processing {file_path}")
                return
                
            # Get file content from version
            from database.models import FileVersionModel
            version = FileVersionModel.get_by_id(version_id)
            
            if not version or not version.get('content'):
                logging.debug(f"No content found for version {version_id} of {file_path}")
                return
                
            content = version['content']
            if len(content.strip()) < 50:  # Skip very short content
                logging.debug(f"Skipping AI processing for {file_path} - content too short")
                return
                
            logging.info(f"[AI] Processing {Path(file_path).name} with AI immediately...")
            
            # Generate AI summary
            summary = self.ai_client.generate_summary(content)
            if summary:
                # Extract semantic metadata
                metadata = self.ai_client.extract_semantic_metadata(summary)
                
                # Store in database immediately
                from database.models import SemanticModel
                semantic_id = SemanticModel.insert_entry(
                    summary=metadata.get('summary', 'AI-generated summary'),
                    entry_type='immediate_processing',
                    impact=metadata.get('impact', 'minor'),
                    topics=metadata.get('topics', []),
                    keywords=metadata.get('keywords', []),
                    file_path=file_path,
                    version_id=version_id
                )
                
                logging.info(f"[AI] Created semantic entry {semantic_id} for {Path(file_path).name}")
                
                # Notify summary note service about new summary
                self._notify_summary_created(file_path, semantic_id)
                
                return semantic_id
            else:
                logging.warning(f"[AI] No summary generated for {file_path}")
                
        except Exception as e:
            logging.error(f"[AI] Error in immediate AI processing for {file_path}: {e}")
    
    def _notify_summary_created(self, file_path: str, semantic_id: int):
        """Notify the summary note service about a newly created summary."""
        try:
            # Import here to avoid circular imports
            from routes.summary_note import notify_summary_note_change
            
            # Create a filename based on the semantic entry
            filename = f"Summary-{semantic_id}-{Path(file_path).stem}.md"
            notify_summary_note_change('created', filename)
            
            logging.debug(f"[AI] Notified summary service about new summary: {filename}")
            
        except Exception as e:
            logging.warning(f"[AI] Failed to notify summary service: {e}")
    
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
