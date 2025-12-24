"""
Agent Cancellation Service
Handles graceful-then-force cancellation of agent operations with user feedback.
"""

import asyncio
import psutil
import logging
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CancellationStatus:
    """Tracks the state of an ongoing cancellation."""
    session_id: str
    phase: str  # 'initiated', 'graceful', 'forcing', 'completed', 'failed'
    started_at: datetime
    subprocess_pid: Optional[int] = None
    message: str = ""


class AgentCancellationService:
    """Handles graceful-then-force cancellation of agent operations."""

    GRACEFUL_TIMEOUT = 5.0  # seconds to wait for graceful cancel
    FORCE_TIMEOUT = 3.0     # seconds for SIGTERM before SIGKILL

    def __init__(self):
        self.active_cancellations: Dict[str, CancellationStatus] = {}

    async def cancel_agent(
        self,
        session_id: str,
        task: asyncio.Task,
        subprocess_pid: Optional[int] = None,
        notify_callback: Optional[Callable[[str, str, str, Optional[Dict[str, Any]]], None]] = None
    ) -> bool:
        """
        Cancel an agent operation with graceful-then-force approach.

        Args:
            session_id: Chat session identifier
            task: The asyncio task to cancel
            subprocess_pid: Optional PID of Claude subprocess
            notify_callback: Callback to send SSE updates (session_id, event_type, message, data)

        Returns:
            True if cancellation succeeded
        """
        # Prevent duplicate cancellations
        if session_id in self.active_cancellations:
            logger.warning(f"Cancellation already in progress for session {session_id}")
            return False

        status = CancellationStatus(
            session_id=session_id,
            phase='initiated',
            started_at=datetime.now(),
            subprocess_pid=subprocess_pid
        )
        self.active_cancellations[session_id] = status

        try:
            # Phase 1: Graceful cancellation
            status.phase = 'graceful'
            status.message = 'Stopping agent gracefully...'
            logger.info(f"Phase 1: Graceful cancellation for session {session_id}")

            if notify_callback:
                notify_callback(session_id, 'cancelling', status.message, {'phase': 'graceful'})

            task.cancel()

            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=self.GRACEFUL_TIMEOUT)
                # Task completed (possibly raised CancelledError)
                status.phase = 'completed'
                status.message = 'Agent stopped'
                logger.info(f"Graceful cancellation succeeded for session {session_id}")
                if notify_callback:
                    notify_callback(session_id, 'cancelled', status.message, {'phase': 'graceful_success'})
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Graceful cancellation timed out for {session_id}")
            except asyncio.CancelledError:
                # Task was cancelled successfully
                status.phase = 'completed'
                status.message = 'Agent stopped'
                logger.info(f"Graceful cancellation succeeded (CancelledError) for session {session_id}")
                if notify_callback:
                    notify_callback(session_id, 'cancelled', status.message, {'phase': 'graceful_success'})
                return True

            # Phase 2: Force-kill subprocess if graceful failed
            if subprocess_pid:
                status.phase = 'forcing'
                status.message = "Agent didn't respond, forcing stop..."
                logger.info(f"Phase 2: Force-killing subprocess {subprocess_pid} for session {session_id}")

                if notify_callback:
                    notify_callback(session_id, 'cancelling', status.message, {'phase': 'force'})

                success = await self._force_kill_subprocess(subprocess_pid)

                if success:
                    status.phase = 'completed'
                    status.message = 'Agent force stopped'
                    logger.info(f"Force-kill succeeded for session {session_id}")
                    if notify_callback:
                        notify_callback(session_id, 'cancelled', status.message, {'phase': 'force_success'})
                    return True
                else:
                    logger.error(f"Force-kill failed for session {session_id}")
            else:
                logger.warning(f"No subprocess PID available for force-kill, session {session_id}")

            # Phase 3: Failed to stop
            status.phase = 'failed'
            status.message = 'Failed to stop agent'
            logger.error(f"Cancellation failed for session {session_id}")
            if notify_callback:
                notify_callback(session_id, 'error', status.message, {'phase': 'failed'})
            return False

        except Exception as e:
            logger.error(f"Error during cancellation for session {session_id}: {e}")
            status.phase = 'failed'
            status.message = f'Cancellation error: {str(e)}'
            if notify_callback:
                notify_callback(session_id, 'error', status.message, {'phase': 'error', 'error': str(e)})
            return False

        finally:
            # Always cleanup
            if session_id in self.active_cancellations:
                del self.active_cancellations[session_id]

    async def _force_kill_subprocess(self, pid: int) -> bool:
        """Force-kill a subprocess using psutil."""
        try:
            process = psutil.Process(pid)
            logger.info(f"Attempting to terminate process {pid} ({process.name()})")

            # First try SIGTERM (graceful)
            process.terminate()
            try:
                # Wait for process to die
                process.wait(timeout=self.FORCE_TIMEOUT)
                logger.info(f"Process {pid} terminated gracefully")
                return True
            except psutil.TimeoutExpired:
                pass

            # If SIGTERM didn't work, use SIGKILL
            logger.warning(f"SIGTERM failed for PID {pid}, using SIGKILL")
            process.kill()
            process.wait(timeout=2.0)
            logger.info(f"Process {pid} killed with SIGKILL")
            return True

        except psutil.NoSuchProcess:
            # Already dead - that's fine
            logger.info(f"Process {pid} already terminated")
            return True
        except psutil.AccessDenied:
            logger.error(f"Access denied when killing process {pid}")
            return False
        except Exception as e:
            logger.error(f"Failed to kill subprocess {pid}: {e}")
            return False

    def is_cancelling(self, session_id: str) -> bool:
        """Check if a cancellation is in progress for a session."""
        return session_id in self.active_cancellations

    def get_status(self, session_id: str) -> Optional[CancellationStatus]:
        """Get the current cancellation status for a session."""
        return self.active_cancellations.get(session_id)


def find_claude_subprocess() -> Optional[int]:
    """
    Find the Claude CLI subprocess PID.
    Searches for child processes that match Claude CLI patterns.
    """
    try:
        current_process = psutil.Process()
        for child in current_process.children(recursive=True):
            try:
                cmdline = ' '.join(child.cmdline()).lower()
                # Look for Claude CLI patterns
                if 'claude' in cmdline or 'anthropic' in cmdline or 'npx' in cmdline:
                    logger.debug(f"Found potential Claude subprocess: PID {child.pid}, cmd: {cmdline[:100]}")
                    return child.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    except Exception as e:
        logger.error(f"Error finding Claude subprocess: {e}")
        return None


def find_all_claude_subprocesses() -> list[int]:
    """
    Find all Claude CLI subprocess PIDs.
    Returns a list of PIDs that match Claude CLI patterns.
    """
    pids = []
    try:
        current_process = psutil.Process()
        for child in current_process.children(recursive=True):
            try:
                cmdline = ' '.join(child.cmdline()).lower()
                if 'claude' in cmdline or 'anthropic' in cmdline or 'npx' in cmdline:
                    pids.append(child.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error finding Claude subprocesses: {e}")
    return pids


# Singleton instance
_cancellation_service: Optional[AgentCancellationService] = None


def get_cancellation_service() -> AgentCancellationService:
    """Get the singleton cancellation service instance."""
    global _cancellation_service
    if _cancellation_service is None:
        _cancellation_service = AgentCancellationService()
    return _cancellation_service
