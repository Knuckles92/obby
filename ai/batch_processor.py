"""
Batch AI Processing System
==========================

Scheduled batch processing of accumulated file changes with AI analysis.
Replaces individual AI calls on every file change with efficient batch processing.
"""

import logging
import threading
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from database.models import (
    db, ContentDiffModel, FileChangeModel, SemanticModel, 
    ConfigModel, FileVersionModel
)
from ai.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

class BatchAIProcessor:
    """Handles batch AI processing of accumulated file changes on a schedule."""
    
    def __init__(self, ai_client: OpenAIClient = None):
        self.ai_client = ai_client or OpenAIClient()
        self.is_running = False
        self.scheduler_thread = None
        self.processing_lock = threading.Lock()
        
        # Configuration keys for database storage
        self.CONFIG_LAST_UPDATE = "batch_ai_last_update"
        self.CONFIG_UPDATE_INTERVAL = "ai_update_interval"
        self.CONFIG_BATCH_ENABLED = "batch_ai_enabled"
        self.CONFIG_MAX_BATCH_SIZE = "ai_max_batch_size"
        
        # Load default settings from config
        try:
            from config.settings import AI_UPDATE_INTERVAL, BATCH_AI_ENABLED, BATCH_AI_MAX_SIZE
            self.default_interval = AI_UPDATE_INTERVAL
            self.default_enabled = BATCH_AI_ENABLED
            self.default_max_batch_size = BATCH_AI_MAX_SIZE
        except ImportError:
            # Fallback defaults if settings not available
            self.default_interval = 300  # 5 minutes
            self.default_enabled = True
            self.default_max_batch_size = 50
        
        # Initialize default configurations if not set
        self._initialize_config()
    
    def _initialize_config(self):
        """Initialize default configuration values."""
        try:
            # Set defaults if not already configured
            if ConfigModel.get(self.CONFIG_UPDATE_INTERVAL) is None:
                ConfigModel.set(self.CONFIG_UPDATE_INTERVAL, self.default_interval, 
                               "AI batch processing interval in seconds")
            
            if ConfigModel.get(self.CONFIG_BATCH_ENABLED) is None:
                ConfigModel.set(self.CONFIG_BATCH_ENABLED, self.default_enabled, 
                               "Enable automatic batch AI processing")
            
            if ConfigModel.get(self.CONFIG_MAX_BATCH_SIZE) is None:
                ConfigModel.set(self.CONFIG_MAX_BATCH_SIZE, self.default_max_batch_size,
                               "Maximum number of changes to process in one batch")
            
            # Initialize last update timestamp if not set
            if ConfigModel.get(self.CONFIG_LAST_UPDATE) is None:
                ConfigModel.set(self.CONFIG_LAST_UPDATE, datetime.now().isoformat(),
                               "Last batch AI processing timestamp")
                
            logger.info("Batch AI processor configuration initialized")
            
        except Exception as e:
            logger.error(f"Error initializing batch AI processor config: {e}")
    
    def start_scheduler(self):
        """Start the batch processing scheduler."""
        if self.is_running:
            logger.warning("Batch AI scheduler is already running")
            return
        
        if not ConfigModel.get(self.CONFIG_BATCH_ENABLED, True):
            logger.info("Batch AI processing is disabled")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        interval = ConfigModel.get(self.CONFIG_UPDATE_INTERVAL, self.default_interval)
        logger.info(f"Batch AI scheduler started with {interval}s interval")
    
    def stop_scheduler(self):
        """Stop the batch processing scheduler."""
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        logger.info("Batch AI scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop for batch processing."""
        while self.is_running:
            try:
                interval = ConfigModel.get(self.CONFIG_UPDATE_INTERVAL, self.default_interval)
                time.sleep(interval)
                
                if not self.is_running:
                    break
                
                # Check if batch processing is still enabled
                if not ConfigModel.get(self.CONFIG_BATCH_ENABLED, True):
                    logger.debug("Batch AI processing disabled, skipping")
                    continue
                
                # Process accumulated changes
                self.process_batch()
                
            except Exception as e:
                logger.error(f"Error in batch AI scheduler loop: {e}")
                time.sleep(10)  # Brief pause before continuing
    
    def process_batch(self, force: bool = False) -> Dict[str, Any]:
        """
        Process accumulated file changes in a batch.
        
        Args:
            force: Force processing even if no changes since last update
            
        Returns:
            Dict containing processing results and statistics
        """
        with self.processing_lock:
            try:
                start_time = datetime.now()
                logger.info("Starting batch AI processing...")
                
                # Get last update timestamp
                last_update_str = ConfigModel.get(self.CONFIG_LAST_UPDATE)
                if last_update_str:
                    last_update = datetime.fromisoformat(last_update_str)
                else:
                    last_update = datetime.now() - timedelta(hours=1)  # Default to 1 hour ago
                
                # Query accumulated changes since last update
                changes = self._get_changes_since(last_update)
                
                if not changes and not force:
                    logger.debug("No new changes to process")
                    return {
                        'processed': False,
                        'reason': 'no_changes',
                        'changes_count': 0,
                        'processing_time': 0
                    }
                
                # Limit batch size for performance
                max_batch_size = ConfigModel.get(self.CONFIG_MAX_BATCH_SIZE, self.default_max_batch_size)
                if len(changes) > max_batch_size:
                    logger.warning(f"Batch size {len(changes)} exceeds limit {max_batch_size}, truncating")
                    changes = changes[:max_batch_size]
                
                # Process the batch with AI
                results = self._process_changes_batch(changes)
                
                # Update last processed timestamp
                ConfigModel.set(self.CONFIG_LAST_UPDATE, start_time.isoformat())
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"Batch AI processing completed: {len(changes)} changes in {processing_time:.2f}s")
                
                return {
                    'processed': True,
                    'changes_count': len(changes),
                    'results': results,
                    'processing_time': processing_time,
                    'last_update': start_time.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error in batch AI processing: {e}")
                return {
                    'processed': False,
                    'error': str(e),
                    'changes_count': 0,
                    'processing_time': 0
                }
    
    def _get_changes_since(self, since_timestamp: datetime) -> List[Dict[str, Any]]:
        """Query all file changes since the given timestamp."""
        try:
            # Get content diffs since timestamp
            query = """
                SELECT cd.*, fv_new.content, fv_new.file_path, fv_new.content_hash
                FROM content_diffs cd
                LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                WHERE cd.timestamp > ?
                ORDER BY cd.timestamp ASC
            """
            
            rows = db.execute_query(query, (since_timestamp,))
            changes = []
            
            for row in rows:
                change = {
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'change_type': row['change_type'],
                    'diff_content': row['diff_content'],
                    'lines_added': row['lines_added'],
                    'lines_removed': row['lines_removed'],
                    'timestamp': row['timestamp'],
                    'content': row['content'],
                    'content_hash': row['content_hash']
                }
                changes.append(change)
            
            logger.debug(f"Found {len(changes)} changes since {since_timestamp}")
            return changes
            
        except Exception as e:
            logger.error(f"Error querying changes since {since_timestamp}: {e}")
            return []
    
    def _process_changes_batch(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of changes with AI analysis."""
        try:
            if not changes:
                return {'summaries': [], 'total_impact': 'none'}
            
            # Group changes by file for better processing
            changes_by_file = {}
            for change in changes:
                file_path = change['file_path']
                if file_path not in changes_by_file:
                    changes_by_file[file_path] = []
                changes_by_file[file_path].append(change)
            
            # Process each file's accumulated changes
            summaries = []
            impact_levels = []
            
            for file_path, file_changes in changes_by_file.items():
                try:
                    summary = self._process_file_changes(file_path, file_changes)
                    if summary:
                        summaries.append(summary)
                        impact_levels.append(summary.get('impact', 'brief'))
                        
                except Exception as e:
                    logger.error(f"Error processing changes for {file_path}: {e}")
                    continue
            
            # Generate comprehensive batch summary
            batch_summary = self._generate_batch_summary(summaries, changes)
            
            # Determine overall impact
            overall_impact = self._calculate_overall_impact(impact_levels)
            
            return {
                'summaries': summaries,
                'batch_summary': batch_summary,
                'total_impact': overall_impact,
                'files_processed': len(changes_by_file),
                'total_changes': len(changes)
            }
            
        except Exception as e:
            logger.error(f"Error processing changes batch: {e}")
            return {'summaries': [], 'error': str(e)}
    
    def _process_file_changes(self, file_path: str, changes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Process accumulated changes for a single file."""
        try:
            if not changes:
                return None
            
            # Combine all diffs for this file
            combined_diff = self._combine_file_diffs(changes)
            
            # Get the latest content for context
            latest_change = max(changes, key=lambda x: x['timestamp'])
            file_content = latest_change.get('content', '')
            
            # Create context for AI processing
            context = {
                'file_path': file_path,
                'changes_count': len(changes),
                'total_lines_added': sum(c['lines_added'] for c in changes),
                'total_lines_removed': sum(c['lines_removed'] for c in changes),
                'time_span': self._calculate_time_span(changes),
                'combined_diff': combined_diff
            }
            
            # Use AI to summarize the accumulated changes
            summary = self._generate_ai_summary(context)
            
            if summary:
                # Store semantic analysis
                metadata = self.ai_client.extract_semantic_metadata(summary)
                
                semantic_id = SemanticModel.insert_entry(
                    summary=metadata.get('summary', 'Batch processed file changes'),
                    entry_type='batch_processing',
                    impact=metadata.get('impact', 'brief'),
                    topics=metadata.get('topics', []),
                    keywords=metadata.get('keywords', []),
                    file_path=file_path,
                    version_id=latest_change.get('new_version_id'),
                    source_type='session_summary_auto'
                )
                
                logger.debug(f"Created semantic entry {semantic_id} for batch processing of {file_path}")
                
                return {
                    'file_path': file_path,
                    'summary': summary,
                    'metadata': metadata,
                    'semantic_id': semantic_id,
                    'context': context
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing file changes for {file_path}: {e}")
            return None
    
    def _combine_file_diffs(self, changes: List[Dict[str, Any]]) -> str:
        """Combine multiple diffs for a file into a summary."""
        try:
            diff_parts = []
            for change in changes:
                if change.get('diff_content'):
                    timestamp = change.get('timestamp', 'unknown')
                    diff_parts.append(f"=== Change at {timestamp} ===")
                    diff_parts.append(change['diff_content'])
                    diff_parts.append("")
            
            return "\n".join(diff_parts)
            
        except Exception as e:
            logger.error(f"Error combining file diffs: {e}")
            return ""
    
    def _calculate_time_span(self, changes: List[Dict[str, Any]]) -> str:
        """Calculate the time span covered by the changes."""
        try:
            if not changes:
                return "unknown"
            
            timestamps = [datetime.fromisoformat(c['timestamp']) for c in changes if c.get('timestamp')]
            if not timestamps:
                return "unknown"
            
            earliest = min(timestamps)
            latest = max(timestamps)
            span = latest - earliest
            
            if span.total_seconds() < 60:
                return f"{int(span.total_seconds())} seconds"
            elif span.total_seconds() < 3600:
                return f"{int(span.total_seconds() / 60)} minutes"
            else:
                return f"{span.total_seconds() / 3600:.1f} hours"
                
        except Exception as e:
            logger.error(f"Error calculating time span: {e}")
            return "unknown"
    
    def _generate_ai_summary(self, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI summary for accumulated file changes."""
        try:
            # Build prompt for batch processing
            prompt = f"""Analyze the accumulated file changes for {context['file_path']}:

Changes Overview:
- Number of changes: {context['changes_count']}
- Lines added: {context['total_lines_added']}
- Lines removed: {context['total_lines_removed']}
- Time span: {context['time_span']}

Combined diff content:
{context['combined_diff'][:2000]}{'...' if len(context['combined_diff']) > 2000 else ''}

Please provide a summary following the standard format with semantic metadata."""
            
            # Use the existing AI client's summarize_diff method
            response = self.ai_client.summarize_diff(prompt)
            
            # If no response, try the batch-specific method
            if not response or "Error" in response:
                batch_data = {
                    'files_count': 1,
                    'total_changes': context['changes_count'],
                    'time_span': context['time_span'],
                    'combined_diff': context['combined_diff']
                }
                response = self.ai_client.summarize_batch_changes(batch_data)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return None
    
    def _generate_batch_summary(self, summaries: List[Dict[str, Any]], changes: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive summary for the entire batch."""
        try:
            if not summaries:
                return "No significant changes processed in this batch."
            
            # Collect all topics and keywords
            all_topics = set()
            all_keywords = set()
            files_affected = set()
            
            for summary in summaries:
                metadata = summary.get('metadata', {})
                all_topics.update(metadata.get('topics', []))
                all_keywords.update(metadata.get('keywords', []))
                files_affected.add(summary.get('file_path', ''))
            
            # Generate comprehensive summary
            summary_parts = [
                f"Batch processing completed for {len(files_affected)} files with {len(changes)} total changes.",
                f"Key topics: {', '.join(list(all_topics)[:5])}",
                f"Key keywords: {', '.join(list(all_keywords)[:8])}",
                f"Files affected: {', '.join([Path(f).name for f in files_affected])}"
            ]
            
            return " ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating batch summary: {e}")
            return "Error generating batch summary"
    
    def _calculate_overall_impact(self, impact_levels: List[str]) -> str:
        """Calculate overall impact from individual file impacts."""
        if not impact_levels:
            return 'none'
        
        # Count impact levels
        significant_count = impact_levels.count('significant')
        moderate_count = impact_levels.count('moderate')
        
        if significant_count > 0:
            return 'significant'
        elif moderate_count > len(impact_levels) / 2:
            return 'moderate'
        else:
            return 'brief'
    
    def get_batch_status(self) -> Dict[str, Any]:
        """Get current batch processing status and configuration."""
        try:
            last_update_str = ConfigModel.get(self.CONFIG_LAST_UPDATE)
            last_update = datetime.fromisoformat(last_update_str) if last_update_str else None
            
            # Calculate time until next batch
            interval = ConfigModel.get(self.CONFIG_UPDATE_INTERVAL, self.default_interval)
            next_batch = last_update + timedelta(seconds=interval) if last_update else datetime.now()
            time_until_next = max(0, (next_batch - datetime.now()).total_seconds())
            
            # Get pending changes count
            if last_update:
                pending_changes = self._get_changes_since(last_update)
                pending_count = len(pending_changes)
            else:
                pending_count = 0
            
            return {
                'enabled': ConfigModel.get(self.CONFIG_BATCH_ENABLED, True),
                'running': self.is_running,
                'interval_seconds': interval,
                'last_update': last_update.isoformat() if last_update else None,
                'next_batch_in_seconds': int(time_until_next),
                'pending_changes_count': pending_count,
                'max_batch_size': ConfigModel.get(self.CONFIG_MAX_BATCH_SIZE, self.default_max_batch_size)
            }
            
        except Exception as e:
            logger.error(f"Error getting batch status: {e}")
            return {'error': str(e)}
    
    def update_config(self, **kwargs) -> bool:
        """Update batch processing configuration."""
        try:
            updated = False
            
            if 'interval' in kwargs:
                ConfigModel.set(self.CONFIG_UPDATE_INTERVAL, int(kwargs['interval']))
                updated = True
            
            if 'enabled' in kwargs:
                ConfigModel.set(self.CONFIG_BATCH_ENABLED, bool(kwargs['enabled']))
                updated = True
            
            if 'max_batch_size' in kwargs:
                ConfigModel.set(self.CONFIG_MAX_BATCH_SIZE, int(kwargs['max_batch_size']))
                updated = True
            
            if updated:
                logger.info(f"Batch AI processor configuration updated: {kwargs}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Error updating batch AI processor config: {e}")
            return False

logger.info("Batch AI processor module initialized")
