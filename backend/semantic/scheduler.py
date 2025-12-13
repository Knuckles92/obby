"""
Semantic Insight Scheduler
==========================

Manages when and how often semantic insights run.
Implements a resource budget system to avoid overwhelming the system.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from database.models import db
from .processor import SemanticProcessor

logger = logging.getLogger(__name__)


class SemanticInsightScheduler:
    """
    Manages the execution budget for semantic insights.

    Runs processing in time-boxed windows to avoid resource exhaustion.
    Supports both scheduled runs and manual triggers.
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the scheduler.

        Args:
            working_dir: Base directory for file operations
            config: Optional configuration overrides
        """
        self.working_dir = working_dir or Path.cwd()
        self.processor = SemanticProcessor(working_dir=self.working_dir)

        # Default configuration
        self.config = {
            'run_interval_minutes': 60,      # How often to run
            'max_runtime_minutes': 5,        # Max time per run
            'max_notes_per_run': 50,         # Limit notes processed
            'max_ai_calls_per_run': 20,      # Limit API calls
            'enabled': True,                  # Whether scheduler is enabled
        }

        # Apply config overrides
        if config:
            self.config.update(config)

        # Scheduler state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._next_run: Optional[datetime] = None

        # Progress callback for UI updates
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._running

    def should_run(self) -> bool:
        """
        Check if enough time has passed since last run.

        Returns:
            True if a new run should be triggered
        """
        if not self.config.get('enabled', True):
            return False

        if self._last_run is None:
            return True

        interval = timedelta(minutes=self.config['run_interval_minutes'])
        return datetime.now() - self._last_run >= interval

    def get_last_run_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the last scheduler run."""
        try:
            result = db.execute_query("""
                SELECT * FROM insight_scheduler_runs
                ORDER BY started_at DESC
                LIMIT 1
            """)
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Error getting last run info: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        last_run = self.get_last_run_info()

        # Calculate queue size (notes needing processing)
        try:
            queue_result = db.execute_query("""
                SELECT COUNT(*) as count
                FROM file_states fs
                LEFT JOIN semantic_processing_state sps ON fs.file_path = sps.note_path
                WHERE fs.file_path LIKE '%.md'
                  AND (sps.content_hash IS NULL OR sps.content_hash != fs.content_hash)
            """)
            queue_size = queue_result[0]['count'] if queue_result else 0
        except Exception:
            queue_size = 0

        return {
            'enabled': self.config.get('enabled', True),
            'is_running': self._running,
            'last_run': last_run,
            'next_run': self._next_run.isoformat() if self._next_run else None,
            'queue_size': queue_size,
            'config': {
                'run_interval_minutes': self.config['run_interval_minutes'],
                'max_runtime_minutes': self.config['max_runtime_minutes'],
                'max_notes_per_run': self.config['max_notes_per_run'],
            }
        }

    async def run_scheduled_processing(self) -> Dict[str, Any]:
        """
        Main entry point - run a single processing cycle.

        Returns:
            Processing summary
        """
        if self._running:
            logger.warning("Processing already in progress")
            return {'error': 'Processing already in progress'}

        self._running = True
        self._last_run = datetime.now()

        try:
            logger.info("Starting scheduled semantic processing")

            # Emit progress event
            if self.progress_callback:
                self.progress_callback({
                    'phase': 'starting',
                    'message': 'Starting semantic processing...'
                })

            # Run the processing pipeline
            summary = await self.processor.run_processing_pipeline(
                max_notes=self.config['max_notes_per_run'],
                max_runtime_seconds=self.config['max_runtime_minutes'] * 60
            )

            # Emit completion event
            if self.progress_callback:
                self.progress_callback({
                    'phase': 'complete',
                    'message': f'Processed {summary["notes_processed"]} notes',
                    'summary': summary
                })

            # Calculate next run time
            self._next_run = datetime.now() + timedelta(
                minutes=self.config['run_interval_minutes']
            )

            logger.info(f"Scheduled processing complete: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Error in scheduled processing: {e}")
            return {'error': str(e)}

        finally:
            self._running = False

    async def trigger_manual_run(self) -> Dict[str, Any]:
        """
        Trigger a manual processing run (ignores schedule).

        Returns:
            Processing summary
        """
        logger.info("Manual processing triggered")
        return await self.run_scheduled_processing()

    async def start_background_scheduler(self):
        """Start the background scheduler loop."""
        if self._task is not None:
            logger.warning("Scheduler already started")
            return

        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Background scheduler started")

    async def stop_background_scheduler(self):
        """Stop the background scheduler loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Background scheduler stopped")

    async def _scheduler_loop(self):
        """Background loop that checks if processing should run."""
        while True:
            try:
                if self.should_run():
                    await self.run_scheduled_processing()

                # Wait before checking again (check every minute)
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    def update_config(self, config: Dict[str, Any]):
        """Update scheduler configuration."""
        self.config.update(config)
        logger.info(f"Scheduler config updated: {config}")

    def enable(self):
        """Enable the scheduler."""
        self.config['enabled'] = True
        logger.info("Scheduler enabled")

    def disable(self):
        """Disable the scheduler."""
        self.config['enabled'] = False
        logger.info("Scheduler disabled")


# Singleton instance
_scheduler_instance: Optional[SemanticInsightScheduler] = None


def get_semantic_scheduler(
    working_dir: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None
) -> SemanticInsightScheduler:
    """
    Get or create the singleton scheduler instance.

    Args:
        working_dir: Base directory for file operations
        config: Optional configuration overrides

    Returns:
        SemanticInsightScheduler instance
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = SemanticInsightScheduler(
            working_dir=working_dir,
            config=config
        )

    return _scheduler_instance
