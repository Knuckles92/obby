"""
Living Notes API routes
Handles living note content, settings, updates, and SSE events
"""

from flask import Blueprint, jsonify, request, Response
import logging
import os
import json
from pathlib import Path
from config.settings import LIVING_NOTE_PATH
from ai.openai_client import OpenAIClient
import queue
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

living_note_bp = Blueprint('living_note', __name__, url_prefix='/api/living-note')

# SSE client management
sse_clients = []
living_note_observer = None


@living_note_bp.route('/', methods=['GET'])
def get_living_note_root():
    """Get the current living note content (root endpoint)"""
    living_note_path = Path('notes/living_note.md')
    
    if living_note_path.exists():
        content = living_note_path.read_text(encoding='utf-8')
        stat = living_note_path.stat()
        
        return jsonify({
            'content': content,
            'lastUpdated': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'wordCount': len(content.split())
        })
    else:
        return jsonify({
            'content': '',
            'lastUpdated': datetime.now().isoformat(),
            'wordCount': 0
        })


@living_note_bp.route('/content', methods=['GET'])
def get_living_note():
    """Get the current living note content"""
    try:
        if os.path.exists(LIVING_NOTE_PATH):
            with open(LIVING_NOTE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# Living Note\n\nNo content yet. Start monitoring to see automated summaries appear here."
        
        return jsonify({
            'content': content,
            'path': LIVING_NOTE_PATH,
            'exists': os.path.exists(LIVING_NOTE_PATH)
        })
    except Exception as e:
        logger.error(f"Failed to read living note: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/clear', methods=['POST'])
def clear_living_note():
    """Clear the living note content"""
    try:
        if os.path.exists(LIVING_NOTE_PATH):
            # Create backup before clearing
            backup_path = f"{LIVING_NOTE_PATH}.backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            # Copy current content to backup
            import shutil
            shutil.copy2(LIVING_NOTE_PATH, backup_path)
            
            # Clear the living note
            with open(LIVING_NOTE_PATH, 'w', encoding='utf-8') as f:
                f.write("# Living Note\n\nCleared at " + 
                       str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + "\n")
            
            logger.info(f"Living note cleared, backup saved to {backup_path}")
            
            # Notify SSE clients
            notify_living_note_change()
            
            return jsonify({
                'success': True,
                'message': 'Living note cleared successfully',
                'backup_path': backup_path
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Living note file does not exist'
            })
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
        settings_path = "living_note_settings.json"
        format_path = "format.md"
        
        # Default settings
        default_settings = {
            "enabled": True,
            "update_frequency": "immediate",
            "include_metadata": True,
            "max_summary_length": 500,
            "format_template": "## Summary\n\n{summary}\n\n## Key Changes\n\n{changes}\n\n---\n\n"
        }
        
        # Load settings
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = default_settings
        
        # Load format template
        if os.path.exists(format_path):
            with open(format_path, 'r', encoding='utf-8') as f:
                settings['format_template'] = f.read()
        
        return jsonify({
            'settings': settings,
            'settings_path': settings_path,
            'format_path': format_path
        })
    except Exception as e:
        logger.error(f"Failed to get living note settings: {e}")
        return jsonify({'error': str(e)}), 500


def save_living_note_settings():
    """Save living note customization settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No settings provided'}), 400
        
        settings_path = "living_note_settings.json"
        format_path = "format.md"
        
        # Extract format template separately
        format_template = data.get('format_template', '')
        if 'format_template' in data:
            del data['format_template']
        
        # Save settings (without format_template)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Save format template
        if format_template:
            with open(format_path, 'w', encoding='utf-8') as f:
                f.write(format_template)
        
        logger.info("Living note settings saved successfully")
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully',
            'settings_path': settings_path,
            'format_path': format_path
        })
    except Exception as e:
        logger.error(f"Failed to save living note settings: {e}")
        return jsonify({'error': str(e)}), 500


@living_note_bp.route('/update', methods=['POST'])
def trigger_living_note_update():
    """Simple update button - trigger a living note update"""
    try:
        data = request.get_json() or {}
        force_update = data.get('force', False)
        
        # Get recent events from database to generate summary
        from database.queries import EventQueries
        recent_events = EventQueries.get_recent_events(limit=10)
        
        if not recent_events and not force_update:
            return jsonify({
                'success': True,
                'message': 'No recent events to summarize',
                'updated': False
            })
        
        # Initialize OpenAI client
        openai_client = OpenAIClient()
        
        # Create a summary of recent events
        if recent_events:
            event_summaries = []
            for event in recent_events:
                summary = f"- {event['type']} in {event['path']}"
                if event.get('summary'):
                    summary += f": {event['summary']}"
                event_summaries.append(summary)
            
            events_text = "\n".join(event_summaries)
            
            # Generate AI summary
            summary = openai_client.summarize_events(events_text)
            
            # Update living note
            success = openai_client.update_living_note(LIVING_NOTE_PATH, summary)
            
            if success:
                # Small delay to ensure file is fully written before notification
                import time
                time.sleep(0.2)
                
                # Notify SSE clients
                notify_living_note_change()
                
                return jsonify({
                    'success': True,
                    'message': 'Living note updated successfully',
                    'updated': True,
                    'summary': summary
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update living note'
                }), 500
        else:
            # Force update with placeholder content
            placeholder_summary = f"Living note manually updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            success = openai_client.update_living_note(LIVING_NOTE_PATH, placeholder_summary)
            
            if success:
                # Small delay to ensure file is fully written before notification
                import time
                time.sleep(0.2)
                
                notify_living_note_change()
                return jsonify({
                    'success': True,
                    'message': 'Living note updated with placeholder content',
                    'updated': True
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update living note'
                }), 500
                
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
        
        if os.path.exists(LIVING_NOTE_PATH):
            with open(LIVING_NOTE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            # Get actual file modification time
            stat = os.stat(LIVING_NOTE_PATH)
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


def start_living_note_watcher():
    """Start watching the living note file for changes"""
    global living_note_observer
    
    if living_note_observer is not None:
        return  # Already watching
    
    try:
        living_note_path = Path(LIVING_NOTE_PATH)
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
