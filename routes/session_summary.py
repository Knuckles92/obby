
"""
Session Summary API routes (FastAPI)
Handles session summary content, settings, updates, and SSE events
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import os
import json
from pathlib import Path
from config.settings import (
    SESSION_SUMMARY_PATH,
    SESSION_SUMMARY_MODE,
    SESSION_SUMMARY_DAILY_DIR,
    SESSION_SUMMARY_DAILY_FILENAME_TEMPLATE,
)
from utils.session_summary_path import resolve_session_summary_path
from services.session_summary_service import SessionSummaryService
import queue
import asyncio
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

# Import SSE client tracking from backend
import sys
if 'backend' in sys.modules:
    from backend import register_sse_client, unregister_sse_client
else:
    # Fallback if backend module not available (e.g., during testing)
    def register_sse_client(client_id: str): pass
    def unregister_sse_client(client_id: str): pass

logger = logging.getLogger(__name__)

session_summary_bp = APIRouter(prefix='/api/session-summary', tags=['session-summary'])

# SSE client management
sse_clients = []
session_summary_observer = None
session_summary_service = SessionSummaryService(str(SESSION_SUMMARY_PATH))
session_summary_update_lock = threading.Lock()


@session_summary_bp.get('/')
async def get_session_summary_root():
    """Get the current session summary content (root endpoint)"""
    try:
        data = session_summary_service.get_content()
        return data
    except Exception as e:
        logger.error(f"Failed to read session summary: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@session_summary_bp.get('/content')
async def get_session_summary():
    """Get the current session summary content"""
    try:
        data = session_summary_service.get_content()
        return data
    except Exception as e:
        logger.error(f"Failed to read session summary: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@session_summary_bp.post('/clear')
async def clear_session_summary():
    """Clear the session summary content"""
    try:
        result = session_summary_service.clear()
        logger.info("Session summary cleared")
        notify_session_summary_change()
        return result
    except Exception as e:
        logger.error(f"Failed to clear session summary: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@session_summary_bp.api_route('/settings', methods=['GET', 'POST'])
async def handle_session_summary_settings(request: Request):
    """Get or save session summary customization settings"""
    if request.method == 'GET':
        return await get_session_summary_settings()
    else:
        return await save_session_summary_settings(request)


async def get_session_summary_settings():
    """Get session summary customization settings"""
    try:
        data = session_summary_service.get_settings()
        return data
    except Exception as e:
        logger.error(f"Failed to get session summary settings: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


async def save_session_summary_settings(request: Request):
    """Save session summary customization settings"""
    try:
        data = await request.json()
        if not data:
            return JSONResponse({'error': 'No settings provided'}, status_code=400)
        result = session_summary_service.save_settings(data)
        logger.info("Session summary settings saved successfully")
        return result
    except Exception as e:
        logger.error(f"Failed to save session summary settings: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


def _run_update_worker(force: bool, lock_timeout: float, result_box: dict, context_config=None):
    """Background worker to perform the session summary update with locking.

    Writes the result dict into result_box['result'] when done.
    """
    acquired = session_summary_update_lock.acquire(timeout=max(lock_timeout, 0.0))
    if not acquired:
        logger.info("Session summary update: another run is in progress; skipping new execution")
        result_box['result'] = {
            'success': True,
            'updated': False,
            'message': 'Update already in progress'
        }
        return
    try:
        logger.info(f"Session summary update: starting (force={force})")
        res = session_summary_service.update(force=force, context_config=context_config)
        result_box['result'] = res
        # Small delay to ensure FS timestamps are visible
        time.sleep(0.2)
        notify_session_summary_change()
        logger.info("Session summary update: completed and SSE notified")
    except Exception as e:
        logger.error(f"Session summary update failed in worker: {e}")
        result_box['result'] = {
            'success': False,
            'updated': False,
            'message': f'Session summary update failed: {str(e)}'
        }
    finally:
        try:
            session_summary_update_lock.release()
        except Exception:
            pass


@session_summary_bp.post('/update')
async def trigger_session_summary_update(request: Request):
    """Update the session summary with optional async execution and overall timeout ceiling.

    Request body supports:
      - force (bool): force update even with no diffs
      - async (bool): when true, start in background and return 202 immediately
      - lock_timeout (float): seconds to wait for acquiring update lock (default 1.0)
      - max_duration_secs (float): ceiling for synchronous wait before returning 202 (default 15.0)
      - context (dict): Optional context configuration for custom time/file filtering
    """
    try:
        data = await request.json() if request.headers.get('content-type','').startswith('application/json') else {}
        force_update = bool(data.get('force', False))
        run_async = bool(data.get('async', False))
        lock_timeout = float(data.get('lock_timeout', 1.0))
        max_duration = float(data.get('max_duration_secs', 15.0))
        
        # Parse context config if provided
        context_config = None
        if 'context' in data and data['context']:
            from utils.summary_context import SummaryContextConfig
            try:
                context_config = SummaryContextConfig.from_dict(data['context'])
                logger.info("Session summary update: using provided context configuration")
            except Exception as e:
                logger.warning(f"Failed to parse context config: {e}, proceeding without it")

        # Always run the update in a worker thread to allow early return if needed
        result_box = {'result': None}
        worker = threading.Thread(target=_run_update_worker, args=(force_update, lock_timeout, result_box, context_config), daemon=True)
        worker.start()

        if run_async:
            logger.info("Session summary update: triggered asynchronously; returning 202")
            return JSONResponse({
                'accepted': True,
                'success': True,
                'message': 'Session summary update started in background',
            }, status_code=202)

        # Synchronous path with protective ceiling
        worker.join(timeout=max(0.0, max_duration))
        if result_box['result'] is not None:
            return result_box['result']
        else:
            logger.info(f"Session summary update: still running after {max_duration:.1f}s; returning 202 to avoid blocking")
            return JSONResponse({
                'accepted': True,
                'success': True,
                'message': 'Session summary update continuing in background',
            }, status_code=202)

    except Exception as e:
        logger.error(f"Failed to trigger session summary update: {e}", exc_info=True)
        # Provide more detailed error message
        error_message = str(e)
        if "API" in error_message:
            error_message = f"AI service error: {error_message}. The service may need a moment to warm up. Please try again."
        elif "timeout" in error_message.lower():
            error_message = "Request timed out. The AI service may be experiencing delays. Please try again."
        else:
            error_message = f"Unexpected error: {error_message}"
        
        return JSONResponse({
            'success': False,
            'message': error_message,
            'updated': False,
            'error_type': type(e).__name__
        }, status_code=500)


@session_summary_bp.get('/events')
async def session_summary_events(request: Request):
    """SSE endpoint for session summary updates"""
    async def event_stream():
        client_id = f"session-{datetime.now().timestamp()}"
        client_queue = asyncio.Queue(maxsize=100)

        # Register client for global tracking
        register_sse_client(client_id)
        sse_clients.append(client_queue)

        logger.info(f"[Session Summary] New client connected: {client_id}")

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'clientId': client_id, 'message': 'Connected to session summary updates'})}\n\n"

            while True:
                # Check if client disconnected BEFORE blocking operation
                if await request.is_disconnected():
                    logger.info(f"[Session Summary] Client {client_id} disconnected (detected)")
                    break

                try:
                    # Wait for events with shorter timeout for faster shutdown (5s instead of 30s)
                    event = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    # Client disconnected - this is normal, just log and exit
                    logger.debug(f"[Session Summary] Client {client_id} disconnected: {e}")
                    break
                except Exception as e:
                    logger.error(f"[Session Summary] SSE stream error for {client_id}: {e}")
                    break
        finally:
            # Remove client from local list
            if client_queue in sse_clients:
                sse_clients.remove(client_queue)
                logger.info(f"[Session Summary] Client {client_id} cleaned up from local list")

            # Unregister from global tracking
            unregister_sse_client(client_id)

    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'X-Accel-Buffering': 'no'  # Disable buffering for nginx/proxy compatibility
    })


def notify_session_summary_change():
    """Notify all SSE clients of session summary changes"""
    try:
        # Read current session summary content
        content = ""
        last_updated = datetime.now().isoformat()

        current_path = _resolve_current_session_summary_path()
        if current_path.exists():
            with open(current_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Get actual file modification time
            stat = os.stat(current_path)
            last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        # Calculate word count
        word_count = len(content.split()) if content else 0
        
        # Create notification event matching the SessionSummary interface
        event = {
            'type': 'session_summary_updated',
            'content': content,
            'lastUpdated': last_updated,
            'wordCount': word_count
        }
        
        # Send to all connected SSE clients
        disconnected_clients = []
        for client_queue in sse_clients:
            try:
                client_queue.put_nowait(event)
            except asyncio.QueueFull:
                # Mark client for removal if queue is full
                disconnected_clients.append(client_queue)
            except Exception as e:
                logger.warning(f"Failed to notify SSE client: {e}")
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            if client in sse_clients:
                sse_clients.remove(client)
        
        logger.info(f"Notified {len(sse_clients)} SSE clients of session summary change")
        logger.debug(f"Session summary content length: {len(content)} characters, word count: {word_count}")
        
    except Exception as e:
        logger.error(f"Failed to notify SSE clients: {e}")


class SessionSummaryFileHandler(FileSystemEventHandler):
    """File system event handler for session summary changes"""
    
    def __init__(self, session_summary_path):
        self.session_summary_path = Path(session_summary_path)
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if Path(event.src_path) == self.session_summary_path:
            logger.info(f"Session summary file changed: {event.src_path}")
            notify_session_summary_change()


def _resolve_current_session_summary_path() -> Path:
    """Resolve the current session summary path according to mode (single/daily)."""
    return resolve_session_summary_path()

def start_session_summary_watcher():
    """Start watching the session summary file for changes"""
    global session_summary_observer
    
    if session_summary_observer is not None:
        return  # Already watching
    
    try:
        session_summary_path = _resolve_current_session_summary_path()
        watch_dir = session_summary_path.parent
        
        # Ensure the directory exists
        watch_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not session_summary_path.exists():
            with open(session_summary_path, 'w', encoding='utf-8') as f:
                f.write("# Session Summary\n\nAutomated summaries will appear here.\n")
        
        # Set up file watcher
        event_handler = SessionSummaryFileHandler(session_summary_path)
        session_summary_observer = Observer()
        session_summary_observer.schedule(event_handler, str(watch_dir), recursive=False)
        session_summary_observer.start()
        
        logger.info(f"Started watching session summary file: {session_summary_path}")
        
    except Exception as e:
        logger.error(f"Failed to start session summary watcher: {e}")


def stop_session_summary_watcher():
    """Stop watching the session summary file"""
    global session_summary_observer
    
    if session_summary_observer is not None:
        session_summary_observer.stop()
        session_summary_observer.join()
        session_summary_observer = None
        logger.info("Stopped session summary file watcher")
