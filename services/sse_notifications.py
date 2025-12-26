"""
SSE Notifications Service

Centralized SSE client management and notification functions.
Extracted from routes to fix architectural layer violations.
"""

import asyncio
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# =============================================================================
# File Updates SSE Management
# =============================================================================

# SSE client management for file content updates
file_update_clients: Dict[str, asyncio.Queue] = {}
file_update_lock = asyncio.Lock()

# File tree cache with debounced invalidation
file_tree_cache = {
    'tree': None,
    'timestamp': None,
    'invalidation_timer': None
}
file_tree_cache_lock = threading.Lock()
FILE_TREE_CACHE_DEBOUNCE_SECONDS = 15


async def notify_file_update(file_path: str, event_type: str = 'modified', content: str = None):
    """Notify SSE clients of file content updates"""
    try:
        event = {
            'type': event_type,
            'filePath': file_path,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        if content is not None:
            event['content'] = content

        logger.info(f"[File Updates] Broadcasting update for: {file_path} to {len(file_update_clients)} clients")

        async with file_update_lock:
            disconnected_clients = []
            for client_id, client_queue in file_update_clients.items():
                try:
                    client_queue.put_nowait(event)
                    logger.debug(f"[File Updates] Sent to client {client_id}: {file_path}")
                except asyncio.QueueFull:
                    logger.warning(f"[File Updates] Queue full for client {client_id}")
                    disconnected_clients.append(client_id)
                except Exception as e:
                    logger.warning(f"[File Updates] Failed to notify client {client_id}: {e}")
                    disconnected_clients.append(client_id)

            # Remove disconnected clients
            for client_id in disconnected_clients:
                del file_update_clients[client_id]
                logger.info(f"[File Updates] Removed disconnected client {client_id}")

    except Exception as e:
        logger.error(f"[File Updates] Failed to notify: {e}")


def _invalidate_file_tree_cache():
    """Internal function to actually clear the file tree cache"""
    with file_tree_cache_lock:
        file_tree_cache['tree'] = None
        file_tree_cache['timestamp'] = None
        file_tree_cache['invalidation_timer'] = None
        logger.info("[File Tree Cache] Cache invalidated")

    # Notify SSE clients that file tree should be refreshed (async)
    async def send_notification():
        try:
            cache_event = {
                'type': 'file_tree_invalidated',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

            async with file_update_lock:
                for client_id, client_queue in file_update_clients.items():
                    try:
                        client_queue.put_nowait(cache_event)
                    except asyncio.QueueFull:
                        pass
                    except Exception:
                        pass

            logger.info(f"[File Tree Cache] Sent invalidation event to {len(file_update_clients)} clients")
        except Exception as e:
            logger.error(f"[File Tree Cache] Failed to send invalidation event: {e}")

    # Schedule the async notification without blocking
    try:
        asyncio.create_task(send_notification())
    except RuntimeError:
        # If no event loop is running, just skip the notification
        logger.debug("[File Tree Cache] Skipped notification - no event loop running")


def invalidate_file_tree_cache_debounced():
    """Invalidate file tree cache with debouncing (15 second delay)"""
    with file_tree_cache_lock:
        # Cancel existing timer if any
        if file_tree_cache['invalidation_timer'] is not None:
            file_tree_cache['invalidation_timer'].cancel()
            logger.debug("[File Tree Cache] Cancelled existing invalidation timer")

        # Schedule new invalidation
        timer = threading.Timer(FILE_TREE_CACHE_DEBOUNCE_SECONDS, _invalidate_file_tree_cache)
        timer.daemon = True
        timer.start()
        file_tree_cache['invalidation_timer'] = timer
        logger.debug(f"[File Tree Cache] Scheduled invalidation in {FILE_TREE_CACHE_DEBOUNCE_SECONDS}s")


# =============================================================================
# Summary Notes SSE Management
# =============================================================================

# SSE client management for summary notes
summary_sse_clients: List[asyncio.Queue] = []


def notify_summary_note_change(action: str, filename: str = None):
    """Notify all SSE clients of summary note changes

    Args:
        action: Type of change ('created', 'deleted', 'updated')
        filename: Name of the affected file
    """
    try:
        # Create notification event
        event = {
            'type': 'summary_note_changed',
            'action': action,
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }

        # Send to all connected SSE clients
        disconnected_clients = []
        for client_queue in summary_sse_clients:
            try:
                client_queue.put_nowait(event)
            except asyncio.QueueFull:
                # Mark client for removal if queue is full
                disconnected_clients.append(client_queue)
            except Exception as e:
                logger.warning(f"Failed to notify summary SSE client: {e}")
                disconnected_clients.append(client_queue)

        # Remove disconnected clients
        for client in disconnected_clients:
            if client in summary_sse_clients:
                summary_sse_clients.remove(client)

        logger.info(f"Notified {len(summary_sse_clients)} SSE clients of summary note {action}: {filename}")

    except Exception as e:
        logger.error(f"Failed to notify summary SSE clients: {e}")
