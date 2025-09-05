# Local imports
from config.settings import *
from config.settings import (
    PERIODIC_SCAN_ENABLED, WATCHDOG_COORDINATION_ENABLED, VERBOSE_MONITORING_LOGS,
    get_configured_notes_folder
)
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from core.file_tracker import FileContentTracker
from ai.openai_client import OpenAIClient
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

class ObbyMonitor:
    """Main Obby monitoring class with pure file system tracking"""
    
    def __init__(self, watch_dirs: List[str] = None, check_interval: int = 60):
        """
        Initialize the Obby monitoring system
        
        Args:
            watch_dirs: List of directories to monitor (defaults to notes folder)
            check_interval: Seconds between periodic checks (default: 60)
        """
        # Get watch directories from config or defaults
        self.watch_dirs = watch_dirs or [str(get_configured_notes_folder())]
        self.watched_paths = self.watch_dirs  # Keep for compatibility
        
        # Initialize file tracker with watch paths
        self.file_tracker = FileContentTracker(watch_paths=self.watch_dirs)
        
        # Initialize AI client (optional)
        self.ai_client = None
        try:
            self.ai_client = OpenAIClient()
            logger.info("[MONITOR] AI client initialized successfully")
        except Exception as e:
            logger.warning(f"[MONITOR] AI client initialization failed: {e}")
            logger.info("[MONITOR] Monitor will run without AI processing")
        
        # Initialize batch AI processor
        self.batch_processor = BatchAIProcessor()
        
        # Monitoring state
        self.file_watcher = None
        self.is_running = False
        self.periodic_check_enabled = PERIODIC_SCAN_ENABLED  # Enable periodic checking based on configuration
        self.periodic_check_thread = None
        self.check_interval = check_interval
        self.last_check_times = {}  # Track last check time for each file
        self.watchdog_active = False  # Track if watchdog is running properly
        self.last_watchdog_event = 0  # Timestamp of last watchdog event
        
        logger.info(f"[MONITOR] ObbyMonitor initialized with check interval: {check_interval}s")
        
    def start(self):
        """Start the file-based monitoring system"""
        if self.is_running:
            return
            
        try:
            # Setup directories
            notes_folder = get_configured_notes_folder()
            ensure_directories(notes_folder)
            setup_test_file(notes_folder / "test.md")
            
            # Initialize file watcher with file tracking integration
            notes_folder = get_configured_notes_folder()
            utils_folder = notes_folder.parent
            from utils.living_note_path import resolve_living_note_path
            self.file_watcher = FileWatcher(
                notes_folder, 
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

        logger.debug("[MONITOR] Starting periodic file check")
        
        # Use the file tracker's scan_directory which now respects ignore/watch patterns
        changes = self.file_tracker.scan_directory()
        
        # Process any detected changes
        total_changes = len(changes.get('new', [])) + len(changes.get('modified', [])) + len(changes.get('deleted', []))
        
        if total_changes > 0:
            logger.info(f"[MONITOR] Periodic check found {total_changes} changes")
            
            # Process new files
            for file_info in changes.get('new', []):
                self.file_tracker.track_file_change(file_info['path'], 'created')
                
            # Process modified files  
            for file_info in changes.get('modified', []):
                self.file_tracker.track_file_change(file_info['path'], 'modified')
                
            # Process deleted files
            for file_info in changes.get('deleted', []):
                self.file_tracker.track_file_change(file_info['path'], 'deleted')
        else:
            logger.debug("[MONITOR] Periodic check found no changes")
            
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