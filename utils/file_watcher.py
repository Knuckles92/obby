"""
File system event handler for monitoring note changes.
Uses watchdog for instant, efficient file change detection.
"""

import time
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from .ignore_handler import IgnoreHandler


class NoteChangeHandler(FileSystemEventHandler):
    """Handles file system events for note changes."""
    
    def __init__(self, notes_folder, diff_tracker, ai_client, living_note_path):
        """
        Initialize the note change handler.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            diff_tracker: DiffTracker instance for processing changes
            ai_client: OpenAIClient instance for generating summaries
            living_note_path: Path to the living note file
        """
        self.notes_folder = Path(notes_folder)
        self.diff_tracker = diff_tracker
        self.ai_client = ai_client
        self.living_note_path = living_note_path
        self.last_event_times = {}  # Track debounce per file
        self.debounce_delay = 0.5  # 500ms debounce to prevent duplicate events
        self.ignore_handler = IgnoreHandler(self.notes_folder)
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        # Check if the modified file is a markdown file in our target folder
        file_path = Path(event.src_path)
        
        # Check if this file should be ignored based on .obbyignore patterns
        if self.ignore_handler.should_ignore(file_path):
            return
            
        if (file_path.suffix.lower() == '.md' and 
            file_path.parent.resolve() == self.notes_folder.resolve()):
            
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
            print(f"[!] Directory created: {event.src_path}")
            self._process_tree_change("created", event.src_path, is_directory=True)
            return
            
        # If a markdown file is created in our folder, process it
        file_path = Path(event.src_path)
        
        # Check if this file should be ignored based on .obbyignore patterns
        if self.ignore_handler.should_ignore(file_path):
            return
            
        if (file_path.suffix.lower() == '.md' and 
            file_path.parent.resolve() == self.notes_folder.resolve()):
            print(f"[!] Note file created: {file_path}")
            self._process_note_change(file_path)
        
        # Also log any file creation for tree tracking
        self._process_tree_change("created", event.src_path, is_directory=False)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            print(f"[!] Directory deleted: {event.src_path}")
            self._process_tree_change("deleted", event.src_path, is_directory=True)
            return
            
        # If a markdown file is deleted from our folder, log it
        file_path = Path(event.src_path)
        
        # Check if this file should be ignored based on .obbyignore patterns
        if self.ignore_handler.should_ignore(file_path):
            return
            
        if (file_path.suffix.lower() == '.md' and 
            file_path.parent.resolve() == self.notes_folder.resolve()):
            print(f"[!] Note file deleted: {file_path}")
            # For deleted files, we can't process content but we should log the event
            self._process_tree_change("deleted", event.src_path, is_directory=False)
        else:
            # Log any file deletion for tree tracking
            self._process_tree_change("deleted", event.src_path, is_directory=False)
    
    def on_moved(self, event):
        """Handle file move/rename events."""
        if event.is_directory:
            print(f"[!] Directory moved: {event.src_path} → {event.dest_path}")
            self._process_tree_change("moved", event.src_path, dest_path=event.dest_path, is_directory=True)
            return
            
        # Handle markdown file moves/renames
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        
        # Check if either source or destination should be ignored based on .obbyignore patterns
        if (self.ignore_handler.should_ignore(src_path) or 
            self.ignore_handler.should_ignore(dest_path)):
            return
        
        # Check if either source or destination is a markdown file in our folder
        src_is_md = (src_path.suffix.lower() == '.md' and 
                     src_path.parent.resolve() == self.notes_folder.resolve())
        dest_is_md = (dest_path.suffix.lower() == '.md' and 
                      dest_path.parent.resolve() == self.notes_folder.resolve())
        
        if src_is_md or dest_is_md:
            print(f"[!] Note file moved: {src_path} → {dest_path}")
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
                print(f"[✓] Processing changes in: {file_path.name}")
                # Generate AI summary and update living note
                summary = self.ai_client.summarize_diff(diff_content)
                self.ai_client.update_living_note(self.living_note_path, summary)
            else:
                print(f"[✓] File event detected but no content change in: {file_path.name}")
                
        except Exception as e:
            print(f"[!] Error processing note change in {file_path.name}: {e}")
    
    def _process_tree_change(self, event_type, src_path, dest_path=None, is_directory=False):
        """Process a detected file tree change."""
        try:
            # Create a summary of the tree change
            path_type = "directory" if is_directory else "file"
            
            if event_type == "moved":
                change_summary = f"File tree change: {path_type} moved from {src_path} to {dest_path}"
            else:
                change_summary = f"File tree change: {path_type} {event_type} at {src_path}"
            
            print(f"[✓] {change_summary}")
            
            # Generate AI summary for the tree change and update living note
            tree_summary = self.ai_client.summarize_tree_change(change_summary)
            self.ai_client.update_living_note(self.living_note_path, tree_summary)
                
        except Exception as e:
            print(f"[!] Error processing tree change: {e}")


class FileWatcher:
    """Main file watcher class for managing the observer."""
    
    def __init__(self, notes_folder, diff_tracker, ai_client, living_note_path):
        """
        Initialize the file watcher.
        
        Args:
            notes_folder: Path to the folder containing markdown files to monitor
            diff_tracker: DiffTracker instance
            ai_client: OpenAIClient instance
            living_note_path: Path to the living note file
        """
        self.notes_folder = Path(notes_folder)
        self.handler = NoteChangeHandler(notes_folder, diff_tracker, ai_client, living_note_path)
        self.observer = Observer()
        self.is_running = False
        
    def start(self):
        """Start watching for file changes."""
        if self.is_running:
            return
            
        # Watch the notes folder
        watch_dir = str(self.notes_folder)
        self.observer.schedule(self.handler, watch_dir, recursive=False)
        self.observer.start()
        self.is_running = True
        
        # Count existing markdown files
        md_files = list(self.notes_folder.glob('*.md'))
        print(f"[✓] File watcher started - monitoring {len(md_files)} markdown files in {self.notes_folder}")
        print("    Real-time change detection active for all .md files!")
        
    def stop(self):
        """Stop watching for file changes."""
        if not self.is_running:
            return
            
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        print("[✓] File watcher stopped")
        
    def wait(self):
        """Wait for the observer to finish (blocking)."""
        if self.is_running:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
