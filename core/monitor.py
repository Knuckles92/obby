# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from core.file_tracker import file_tracker
from ai.openai_client import OpenAIClient
from ai.batch_processor import BatchAIProcessor
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
        self.batch_processor = None
        self.file_watcher = None
        self.is_running = False
        self.watched_paths = [str(NOTES_FOLDER)]
        self.periodic_check_enabled = True  # Enable periodic checking by default
        self.periodic_check_thread = None
        self.check_interval = CHECK_INTERVAL
        self.last_check_times = {}  # Track last check time for each file
        self.batch_processing_enabled = True  # Enable batch AI processing by default
        
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
            
            # Initialize batch AI processor
            if self.batch_processing_enabled:
                self.batch_processor = BatchAIProcessor(self.ai_client)
                self.batch_processor.start_scheduler()
                logger.info("Batch AI processor started")
            
            # Initialize file watcher with file tracking integration
            utils_folder = NOTES_FOLDER.parent
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
        
        # Stop batch AI processor
        if self.batch_processor:
            self.batch_processor.stop_scheduler()
        
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
    
    def trigger_batch_processing(self, force: bool = False):
        """Manually trigger batch AI processing."""
        if not self.batch_processor:
            logger.warning("Batch processor not initialized")
            return {'error': 'Batch processor not available'}
        
        try:
            result = self.batch_processor.process_batch(force=force)
            logger.info(f"Manual batch processing triggered: {result}")
            return result
        except Exception as e:
            logger.error(f"Error triggering batch processing: {e}")
            return {'error': str(e)}
    
    def get_batch_processing_status(self):
        """Get current batch processing status and configuration."""
        if not self.batch_processor:
            return {'error': 'Batch processor not available'}
        
        try:
            return self.batch_processor.get_batch_status()
        except Exception as e:
            logger.error(f"Error getting batch processing status: {e}")
            return {'error': str(e)}
    
    def update_batch_processing_config(self, **kwargs):
        """Update batch processing configuration."""
        if not self.batch_processor:
            logger.warning("Batch processor not initialized")
            return False
        
        try:
            result = self.batch_processor.update_config(**kwargs)
            if result:
                logger.info(f"Batch processing configuration updated: {kwargs}")
            return result
        except Exception as e:
            logger.error(f"Error updating batch processing config: {e}")
            return False
    
    def set_batch_processing_enabled(self, enabled: bool):
        """Enable or disable batch AI processing."""
        self.batch_processing_enabled = enabled
        
        if enabled and not self.batch_processor and self.ai_client:
            # Initialize and start batch processor
            try:
                self.batch_processor = BatchAIProcessor(self.ai_client)
                self.batch_processor.start_scheduler()
                logger.info("Batch AI processor enabled and started")
            except Exception as e:
                logger.error(f"Error starting batch AI processor: {e}")
        elif not enabled and self.batch_processor:
            # Stop batch processor
            try:
                self.batch_processor.stop_scheduler()
                logger.info("Batch AI processor disabled")
            except Exception as e:
                logger.error(f"Error stopping batch AI processor: {e}")
    
    def _process_with_ai(self, file_path: str, version_id: int):
        """
        Process file content with AI for semantic analysis.
        
        Modified to work with batch processing - individual AI calls are reduced
        and processing is deferred to batch operations when batch mode is enabled.
        """
        try:
            # If batch processing is enabled, skip individual AI processing
            # The batch processor will handle accumulated changes
            if self.batch_processing_enabled and self.batch_processor:
                logger.debug(f"Skipping individual AI processing for {file_path} - batch mode enabled")
                return
            
            # Fallback to individual processing if batch mode is disabled
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
                    entry_type='individual_analysis',
                    impact=response.get('impact', 'minor'),
                    topics=response.get('topics', []),
                    keywords=response.get('keywords', []),
                    file_path=file_path,
                    version_id=version_id
                )
                
                logger.debug(f"Individual AI analysis completed for {file_path}")
                
        except Exception as e:
            logger.error(f"Error in AI processing for {file_path}: {e}")

logger.info("File-based monitoring system initialized")