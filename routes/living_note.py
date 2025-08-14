"""
Living Notes API routes
Handles living note content, settings, updates, and SSE events
"""

from flask import Blueprint, jsonify, request, Response
import logging
import os
import json
from pathlib import Path
from config.settings import LIVING_NOTE_PATH, LIVING_NOTE_MODE, LIVING_NOTE_DAILY_DIR, LIVING_NOTE_DAILY_FILENAME_TEMPLATE
from utils.living_note_path import resolve_living_note_path
from ai.openai_client import OpenAIClient
from services.living_note_service import LivingNoteService
import queue
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

living_note_bp = Blueprint('living_note', __name__, url_prefix='/api/living-note')

# SSE client management
sse_clients = []
living_note_observer = None
living_note_service = LivingNoteService(str(LIVING_NOTE_PATH))


@living_note_bp.route('/', methods=['GET'])
def get_living_note_root():
    """Get the current living note content (root endpoint)"""
    try:
        data = living_note_service.get_content()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to read living note: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/content', methods=['GET'])
def get_living_note():
    """Get the current living note content"""
    try:
        data = living_note_service.get_content()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to read living note: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/clear', methods=['POST'])
def clear_living_note():
    """Clear the living note content"""
    try:
        result = living_note_service.clear()
        logger.info("Living note cleared")
        notify_living_note_change()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to clear living note: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/settings', methods=['GET', 'POST'])
def handle_living_note_settings():
    """Get or save living note customization settings"""
    if request.method == 'GET':
        return get_living_note_settings()
    else:
        return save_living_note_settings()


def get_living_note_settings():
    """Get living note customization settings"""
    try:
        data = living_note_service.get_settings()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to get living note settings: {e}")
        return jsonify({'error': str(e)}), 500


def save_living_note_settings():
    """Save living note customization settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No settings provided'}), 400
        result = living_note_service.save_settings(data)
        logger.info("Living note settings saved successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to save living note settings: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/update', methods=['POST'])
def trigger_living_note_update():
    """Update the living note by summarizing content diffs since the last update.

    This constrains the living note to summaries/insights strictly for the window
    between update calls (cursor-based), instead of an arbitrary set of recent events.
    """
    try:
        data = request.get_json() or {}
        force_update = data.get('force', False)
        result = living_note_service.update(force=force_update)
        # Notify SSE clients after a short delay to ensure the filesystem write is visible
        import time
        time.sleep(0.2)
        notify_living_note_change()
        status = 200 if result.get('success') else 500
        return jsonify(result), status

    except Exception as e:
        logger.error(f"Failed to trigger living note update: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/events')
def living_note_events():
    """SSE endpoint for living note updates"""
    def event_stream():
        client_queue = queue.Queue()
        sse_clients.append(client_queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to living note updates'})}\n\n"
            
            while True:
                try:
                    # Wait for events with timeout
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                except Exception as e:
                    logger.error(f"SSE stream error: {e}")
                    break
        finally:
            # Remove client from list when disconnected
            if client_queue in sse_clients:
                sse_clients.remove(client_queue)
    
    return Response(event_stream(), mimetype='text/event-stream', 
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*'})


def notify_living_note_change():
    """Notify all SSE clients of living note changes"""
    try:
        # Read current living note content
        content = ""
        last_updated = datetime.now().isoformat()

        current_path = _resolve_current_living_note_path()
        if current_path.exists():
            with open(current_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Get actual file modification time
            stat = os.stat(current_path)
            last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        # Calculate word count
        word_count = len(content.split()) if content else 0
        
        # Create notification event matching the LivingNote interface
        event = {
            'type': 'living_note_updated',
            'content': content,
            'lastUpdated': last_updated,
            'wordCount': word_count
        }
        
        # Send to all connected SSE clients
        disconnected_clients = []
        for client_queue in sse_clients:
            try:
                client_queue.put_nowait(event)
            except queue.Full:
                # Mark client for removal if queue is full
                disconnected_clients.append(client_queue)
            except Exception as e:
                logger.warning(f"Failed to notify SSE client: {e}")
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            if client in sse_clients:
                sse_clients.remove(client)
        
        logger.info(f"Notified {len(sse_clients)} SSE clients of living note change")
        logger.debug(f"Living note content length: {len(content)} characters, word count: {word_count}")
        
    except Exception as e:
        logger.error(f"Failed to notify SSE clients: {e}")


class LivingNoteFileHandler(FileSystemEventHandler):
    """File system event handler for living note changes"""
    
    def __init__(self, living_note_path):
        self.living_note_path = Path(living_note_path)
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if Path(event.src_path) == self.living_note_path:
            logger.info(f"Living note file changed: {event.src_path}")
            notify_living_note_change()


def _resolve_current_living_note_path() -> Path:
    """Resolve the current living note path according to mode (single/daily)."""
    return resolve_living_note_path()

def start_living_note_watcher():
    """Start watching the living note file for changes"""
    global living_note_observer
    
    if living_note_observer is not None:
        return  # Already watching
    
    try:
        living_note_path = _resolve_current_living_note_path()
        watch_dir = living_note_path.parent
        
        # Ensure the directory exists
        watch_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not living_note_path.exists():
            with open(living_note_path, 'w', encoding='utf-8') as f:
                f.write("# Living Note\n\nAutomated summaries will appear here.\n")
        
        # Set up file watcher
        event_handler = LivingNoteFileHandler(living_note_path)
        living_note_observer = Observer()
        living_note_observer.schedule(event_handler, str(watch_dir), recursive=False)
        living_note_observer.start()
        
        logger.info(f"Started watching living note file: {living_note_path}")
        
    except Exception as e:
        logger.error(f"Failed to start living note watcher: {e}")


def stop_living_note_watcher():
    """Stop watching the living note file"""
    global living_note_observer
    
    if living_note_observer is not None:
        living_note_observer.stop()
        living_note_observer.join()
        living_note_observer = None
        logger.info("Stopped living note file watcher")
