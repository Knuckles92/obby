# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from diffing.diff_tracker import DiffTracker
from ai.openai_client import OpenAIClient
import threading
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ObbyMonitor:
    """Main Obby monitoring class for API integration"""
    
    def __init__(self):
        self.diff_tracker = None
        self.ai_client = None
        self.file_watcher = None
        self.is_running = False
        self.watched_paths = [str(NOTES_FOLDER)]
        self.periodic_check_enabled = True  # Enable periodic checking by default
        self.periodic_check_thread = None
        self.check_interval = CHECK_INTERVAL
        self.last_check_times = {}  # Track last check time for each file
        
    def start(self):
        """Start the monitoring system"""
        if self.is_running:
            return
            
        # Setup
        ensure_directories(DIFF_PATH, NOTES_FOLDER)
        setup_test_file(NOTES_FOLDER / "test.md")
        
        # Initialize components
        self.diff_tracker = DiffTracker(NOTES_FOLDER / "test.md", DIFF_PATH)
        self.ai_client = OpenAIClient()
        
        # Initialize file watcher
        utils_folder = NOTES_FOLDER.parent / "utils"
        self.file_watcher = FileWatcher(
            NOTES_FOLDER, 
            self.diff_tracker, 
            self.ai_client, 
            LIVING_NOTE_PATH, 
            utils_folder
        )
        
        self.file_watcher.start()
        self.is_running = True
        
        # Start periodic checking thread if enabled
        if self.periodic_check_enabled:
            self.start_periodic_checking()
        
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
        """Perform a periodic check of all markdown files in watched directories"""
        logger.debug("Performing periodic check...")
        
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
                    logger.debug(f"Periodic check detected change in: {md_file}")
                    
                    # Update last check time
                    self.last_check_times[str(md_file)] = current_mtime
                    
                    # Process the change (this will trigger AI summary if needed)
                    if self.file_watcher and self.file_watcher.handler:
                        try:
                            self.file_watcher.handler._process_note_change(md_file)
                            checked_count += 1
                        except Exception as e:
                            logger.error(f"Error processing periodic change for {md_file}: {e}")
        
        if checked_count > 0:
            logger.info(f"Periodic check processed {checked_count} changed files")
    
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