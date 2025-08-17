# Local imports
from config.settings import *
from config.settings import (
    PERIODIC_SCAN_ENABLED, WATCHDOG_COORDINATION_ENABLED, VERBOSE_MONITORING_LOGS
)
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
        self.periodic_check_enabled = PERIODIC_SCAN_ENABLED  # Enable periodic checking based on configuration
        self.periodic_check_thread = None
        self.check_interval = CHECK_INTERVAL
        self.last_check_times = {}  # Track last check time for each file
        self.watchdog_active = False  # Track if watchdog is running properly
        self.last_watchdog_event = 0  # Timestamp of last watchdog event
        
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
            utils_folder = NOTES_FOLDER.parent
            from utils.living_note_path import resolve_living_note_path
            self.file_watcher = FileWatcher(
                NOTES_FOLDER, 
                self.ai_client, 
                resolve_living_note_path(), 
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
        current_time = time.time()
        
        # Check if watchdog coordination is enabled and watchdog is active
        if WATCHDOG_COORDINATION_ENABLED:
            watchdog_recently_active = (current_time - self.last_watchdog_event) < 60
            
            if watchdog_recently_active:
                if VERBOSE_MONITORING_LOGS:
                    logger.debug("[PERIODIC] Skipping periodic check - watchdog is active")
                return
            
        if VERBOSE_MONITORING_LOGS:
            logger.debug("[PERIODIC] Performing periodic file check (watchdog inactive)...")
        
        try:
            # Check for file system changes
            self._check_filesystem_changes()
            
        except Exception as e:
            logger.error(f"[PERIODIC] Error in periodic file check: {e}")
    
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
                logger.info(f"[PERIODIC] Scan detected {files_changed} changed files in {watch_dir}")
                checked_count += files_changed
        
        if checked_count > 0:
            logger.debug(f"[PERIODIC] Filesystem check processed {checked_count} changed files")
        else:
            logger.debug(f"[PERIODIC] Filesystem check complete - no changes detected")
    
    def process_file_change(self, file_path: str, change_type: str = 'modified'):
        """Process a file change through the tracking system"""
        try:
            # Update watchdog activity timestamp
            self.last_watchdog_event = time.time()
            
            version_id = self.file_tracker.track_file_change(file_path, change_type)
            
            if version_id and self.ai_client:
                # Process with AI for semantic analysis
                self._process_with_ai(file_path, version_id)
                
            return version_id
            
        except Exception as e:
            logger.error(f"Error processing file change for {file_path}: {e}")
            return None
    
    
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
    
    
    
    
    def process_with_ai_immediate(self, file_path: str, version_id: int):
        """
        Process file content immediately with AI for semantic analysis.
        This replaces the batch processing system with immediate processing.
        """
        try:
            if not self.ai_client:
                logger.warning(f"AI client not available for processing {file_path}")
                return
                
            # Get file content from version
            from database.models import FileVersionModel
            version = FileVersionModel.get_by_id(version_id)
            
            if not version or not version.get('content'):
                logger.debug(f"No content found for version {version_id} of {file_path}")
                return
                
            content = version['content']
            if len(content.strip()) < 50:  # Skip very short content
                logger.debug(f"Skipping AI processing for {file_path} - content too short")
                return
                
            logger.info(f"Processing {file_path} with AI immediately...")
            
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
                
                logger.info(f"✅ Created semantic entry {semantic_id} for {file_path}")
                return semantic_id
            else:
                logger.warning(f"AI client returned no summary for {file_path}")
                
        except Exception as e:
            logger.error(f"Error in immediate AI processing for {file_path}: {e}")

logger.info("File-based monitoring system initialized")