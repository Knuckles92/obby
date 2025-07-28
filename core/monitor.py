# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from git_integration.git_change_tracker import GitChangeTracker
from git_integration.git_client import get_git_client
from ai.openai_client import OpenAIClient
import threading
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ObbyMonitor:
    """Main Obby monitoring class with git-native change tracking"""
    
    def __init__(self):
        self.git_tracker = None
        self.git_client = None
        self.ai_client = None
        self.file_watcher = None
        self.is_running = False
        self.watched_paths = [str(NOTES_FOLDER)]
        self.periodic_check_enabled = True  # Enable periodic checking by default
        self.periodic_check_thread = None
        self.check_interval = CHECK_INTERVAL
        self.last_check_times = {}  # Track last check time for each file
        
    def start(self):
        """Start the git-native monitoring system"""
        if self.is_running:
            return
            
        try:
            # Setup directories (no longer need DIFF_PATH)
            ensure_directories(NOTES_FOLDER)
            setup_test_file(NOTES_FOLDER / "test.md")
            
            # Initialize git components
            self.git_client = get_git_client()
            self.ai_client = OpenAIClient()
            self.git_tracker = GitChangeTracker(ai_client=self.ai_client)
            
            # Initialize file watcher with git integration
            utils_folder = NOTES_FOLDER.parent / "utils"
            self.file_watcher = FileWatcher(
                NOTES_FOLDER, 
                self.git_tracker,  # Pass git tracker instead of diff tracker
                self.ai_client, 
                LIVING_NOTE_PATH, 
                utils_folder
            )
            
            self.file_watcher.start()
            self.is_running = True
            
            # Start periodic checking thread if enabled
            if self.periodic_check_enabled:
                self.start_periodic_checking()
                
            logger.info("Git-native monitoring system started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring system: {e}")
            raise
        
    def stop(self):
        """Stop the monitoring system"""
        self.is_running = False
        
        # Stop periodic checking
        if self.periodic_check_thread and self.periodic_check_thread.is_alive():
            self.periodic_check_thread.join(timeout=2)
        
        if self.file_watcher:
            self.file_watcher.stop()
    
    def start_periodic_checking(self):
        """Start the periodic checking thread"""
        self.periodic_check_thread = threading.Thread(target=self._periodic_check_loop, daemon=True)
        self.periodic_check_thread.start()
        logger.info(f"Started periodic checking with {self.check_interval}s interval")
    
    def _periodic_check_loop(self):
        """Run periodic checks for all watched files"""
        while self.is_running:
            try:
                # Wait for the configured interval
                time.sleep(self.check_interval)
                
                if not self.is_running:
                    break
                
                # Perform periodic check
                self._perform_periodic_check()
                
            except Exception as e:
                logger.error(f"Error in periodic check loop: {e}")
    
    def _perform_periodic_check(self):
        """Perform a periodic git-based check for changes"""
        logger.debug("Performing periodic git check...")
        
        try:
            # Check for git changes
            has_changes, change_summary = self.git_tracker.check_for_changes()
            
            if has_changes and change_summary:
                logger.info(f"Periodic git check detected changes: {change_summary}")
                
                # Process the changes through the file watcher if needed
                if self.file_watcher and self.file_watcher.handler:
                    try:
                        # Process any working directory changes
                        working_changes = change_summary.get('details', {}).get('working', [])
                        for change in working_changes:
                            file_path = Path(change['path'])
                            if file_path.suffix == '.md':  # Only process markdown files
                                self.file_watcher.handler._process_note_change(file_path)
                    except Exception as e:
                        logger.error(f"Error processing periodic git changes: {e}")
            
            # Also check for file system changes that git might not catch
            self._check_filesystem_changes()
            
        except Exception as e:
            logger.error(f"Error in periodic git check: {e}")
    
    def _check_filesystem_changes(self):
        """Check for filesystem changes in watched directories"""
        # Get all directories to check from watch handler
        if self.file_watcher and self.file_watcher.handler:
            watch_dirs = self.file_watcher.handler.watch_handler.get_watch_directories()
        else:
            watch_dirs = [NOTES_FOLDER]
        
        checked_count = 0
        for watch_dir in watch_dirs:
            if not watch_dir.exists():
                continue
                
            # Find all markdown files in this directory
            for md_file in watch_dir.rglob('*.md'):
                if not md_file.is_file():
                    continue
                
                # Skip if file should be ignored
                if (self.file_watcher and
                    self.file_watcher.handler.ignore_handler.should_ignore(md_file)):
                    continue
                
                # Check if file was modified since last check
                current_mtime = md_file.stat().st_mtime
                last_check = self.last_check_times.get(str(md_file), 0)
                
                if current_mtime > last_check:
                    logger.debug(f"Filesystem check detected change in: {md_file}")
                    
                    # Update last check time
                    self.last_check_times[str(md_file)] = current_mtime
                    
                    # Update git file state
                    self.git_tracker.update_file_state(md_file)
                    
                    # Process the change
                    if self.file_watcher and self.file_watcher.handler:
                        try:
                            self.file_watcher.handler._process_note_change(md_file)
                            checked_count += 1
                        except Exception as e:
                            logger.error(f"Error processing filesystem change for {md_file}: {e}")
        
        if checked_count > 0:
            logger.debug(f"Filesystem check processed {checked_count} changed files")
    
    def set_check_interval(self, interval_seconds):
        """Update the check interval"""
        self.check_interval = max(1, interval_seconds)
        logger.info(f"Check interval updated to {self.check_interval}s")
    
    def set_periodic_check_enabled(self, enabled):
        """Enable or disable periodic checking"""
        self.periodic_check_enabled = enabled
        
        if enabled and self.is_running and not (self.periodic_check_thread and self.periodic_check_thread.is_alive()):
            self.start_periodic_checking()
        elif not enabled and self.periodic_check_thread and self.periodic_check_thread.is_alive():
            logger.info("Stopping periodic checking")