# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from core.file_tracker import file_tracker
from ai.openai_client import OpenAIClient
import threading
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ObbyMonitor:
    """Main Obby monitoring class with pure file system tracking"""
    
    def __init__(self):
        self.file_tracker = file_tracker
        self.ai_client = None
        self.file_watcher = None
        self.is_running = False
        self.watched_paths = [str(NOTES_FOLDER)]
        self.periodic_check_enabled = True  # Enable periodic checking by default
        self.periodic_check_thread = None
        self.check_interval = CHECK_INTERVAL
        self.last_check_times = {}  # Track last check time for each file
        
    def start(self):
        """Start the file-based monitoring system"""
        if self.is_running:
            return
            
        try:
            # Setup directories
            ensure_directories(NOTES_FOLDER)
            setup_test_file(NOTES_FOLDER / "test.md")
            
            # Initialize AI client for content analysis
            self.ai_client = OpenAIClient()
            
            # Initialize file watcher with file tracking integration
            utils_folder = NOTES_FOLDER.parent / "utils"
            self.file_watcher = FileWatcher(
                NOTES_FOLDER, 
                self.ai_client, 
                LIVING_NOTE_PATH, 
                utils_folder,
                file_tracker=self.file_tracker  # Pass file tracker to watcher
            )
            
            self.file_watcher.start()
            self.is_running = True
            
            # Start periodic checking thread if enabled
            if self.periodic_check_enabled:
                self.start_periodic_checking()
                
            logger.info("File-based monitoring system started successfully")
            
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
        """Perform a periodic file-based check for changes"""
        logger.debug("Performing periodic file check...")
        
        try:
            # Check for file system changes
            self._check_filesystem_changes()
            
        except Exception as e:
            logger.error(f"Error in periodic file check: {e}")
    
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
                
            # Scan directory for changes using file tracker
            files_changed = self.file_tracker.scan_directory(str(watch_dir), recursive=True)
            
            if files_changed > 0:
                logger.info(f"Periodic scan detected {files_changed} changed files in {watch_dir}")
                checked_count += files_changed
        
        if checked_count > 0:
            logger.debug(f"Filesystem check processed {checked_count} changed files")
    
    def process_file_change(self, file_path: str, change_type: str = 'modified'):
        """Process a file change through the tracking system"""
        try:
            version_id = self.file_tracker.track_file_change(file_path, change_type)
            
            if version_id and self.ai_client:
                # Process with AI for semantic analysis
                self._process_with_ai(file_path, version_id)
                
            return version_id
            
        except Exception as e:
            logger.error(f"Error processing file change for {file_path}: {e}")
            return None
    
    def _process_with_ai(self, file_path: str, version_id: int):
        """Process file content with AI for semantic analysis"""
        try:
            # Get file content from version
            from database.models import FileVersionModel
            version = FileVersionModel.get_by_hash("", file_path)  # Get latest version
            
            if not version or not version.get('content'):
                return
                
            # Use AI to analyze content
            content = version['content']
            if len(content.strip()) < 50:  # Skip very short content
                return
                
            # Generate AI analysis
            response = self.ai_client.summarize_changes(content, file_path)
            
            if response and isinstance(response, dict):
                # Store semantic analysis
                from database.models import SemanticModel
                SemanticModel.insert_entry(
                    summary=response.get('summary', 'File content analyzed'),
                    entry_type='file_analysis',
                    impact=response.get('impact', 'minor'),
                    topics=response.get('topics', []),
                    keywords=response.get('keywords', []),
                    file_path=file_path,
                    version_id=version_id
                )
                
                logger.debug(f"AI analysis completed for {file_path}")
                
        except Exception as e:
            logger.error(f"Error in AI processing for {file_path}: {e}")
    
    def get_file_history(self, file_path: str, limit: int = 50):
        """Get change history for a file"""
        return self.file_tracker.get_file_history(file_path, limit)
    
    def get_file_diff(self, file_path: str, old_version_id: int = None, new_version_id: int = None):
        """Get diff between file versions"""
        return self.file_tracker.get_file_diff(file_path, old_version_id, new_version_id)
    
    def get_current_file_state(self, file_path: str):
        """Get current state of a file"""
        return self.file_tracker.get_current_file_state(file_path)
    
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
    
    def get_stats(self):
        """Get monitoring statistics"""
        from database.models import PerformanceModel, FileVersionModel, FileChangeModel
        
        stats = PerformanceModel.get_stats()
        
        # Add file tracking specific stats
        recent_versions = FileVersionModel.get_recent(limit=10)
        recent_changes = FileChangeModel.get_recent(limit=10)
        
        stats.update({
            'recent_versions_count': len(recent_versions),
            'recent_changes_count': len(recent_changes),
            'is_running': self.is_running,
            'periodic_check_enabled': self.periodic_check_enabled,
            'check_interval': self.check_interval
        })
        
        return stats

logger.info("File-based monitoring system initialized")