from flask import Flask, jsonify, request, send_from_directory, send_file, Response
from flask_cors import CORS
import threading
import time
import os
from pathlib import Path
from typing import Dict, List, Any
from config.settings import DIFF_PATH, LIVING_NOTE_PATH
import json
from datetime import datetime
import uuid
import logging
from functools import lru_cache
import queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.monitor import ObbyMonitor
from config.settings import CHECK_INTERVAL, OPENAI_MODEL, NOTES_FOLDER
from ai.openai_client import OpenAIClient
from utils.file_watcher import FileWatcher, NoteChangeHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('obby.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Disable Flask development server logging in production
if not app.debug:
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

# Global variables for monitoring state
monitor_instance = None
monitor_thread = None
monitoring_active = False
recent_events = []
recent_diffs = []

# SSE clients for real-time updates
sse_clients = []
living_note_observer = None

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current monitoring status"""
    global monitoring_active, monitor_instance
    
    watched_paths = []
    total_files = 0
    events_today = len([e for e in recent_events if is_today(e.get('timestamp', ''))])
    
    if monitor_instance and monitoring_active:
        watched_paths = getattr(monitor_instance, 'watched_paths', [])
        # Count files in watched directories
        for path in watched_paths:
            if os.path.exists(path):
                # Count only .md files that aren't ignored
                path_obj = Path(path)
                for f in path_obj.rglob('*.md'):
                    if f.is_file():
                        # Check if file would be watched (simplified check)
                        rel_path = f.relative_to(path_obj) if f.is_relative_to(path_obj) else f
                        if not any(part.startswith('.') for part in rel_path.parts):
                            total_files += 1
    
    return jsonify({
        'isActive': monitoring_active,
        'watchedPaths': watched_paths,
        'totalFiles': total_files,
        'eventsToday': events_today
    })

@app.route('/api/monitor/start', methods=['POST'])
def start_monitoring():
    """Start file monitoring"""
    global monitor_instance, monitor_thread, monitoring_active
    
    if monitoring_active:
        return jsonify({'message': 'Monitoring already active'}), 400
    
    try:
        monitor_instance = APIObbyMonitor()
        monitor_instance.start()
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        monitoring_active = True
        
        # Get initial watched paths
        if monitor_instance.file_watcher:
            watched_paths = []
            watch_dirs = monitor_instance.file_watcher.handler.watch_handler.get_watch_directories()
            if watch_dirs:
                watched_paths = [str(d) for d in watch_dirs if d.exists()]
            else:
                watched_paths = [str(NOTES_FOLDER)]
            monitor_instance.watched_paths = watched_paths
        
        return jsonify({'message': 'Monitoring started successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitoring():
    """Stop file monitoring"""
    global monitoring_active, monitor_instance
    
    monitoring_active = False
    if monitor_instance:
        monitor_instance.stop()
        monitor_instance = None
    
    return jsonify({'message': 'Monitoring stopped'})

@app.route('/api/events', methods=['GET'])
def get_recent_events():
    """Get recent file events"""
    try:
        limit = max(1, min(request.args.get('limit', 50, type=int), 200))  # Limit between 1-200
        return jsonify(recent_events[-limit:] if recent_events else [])
    except Exception as e:
        logger.error(f"Error retrieving recent events: {e}")
        return jsonify({'error': 'Failed to retrieve events'}), 500

@app.route('/api/diffs', methods=['GET'])
def get_recent_diffs():
    """Get recent diff files"""
    try:
        limit = max(1, min(request.args.get('limit', 20, type=int), 100))  # Limit between 1-100
        
        # Use absolute path to ensure we're looking in the right place
        diffs_dir = Path(__file__).parent / 'diffs'
        diff_files = []
        
        print(f"DIFFS API CALLED - Looking in: {diffs_dir.resolve()}")
        print(f"DIFFS API CALLED - Dir exists: {diffs_dir.exists()}")
        logger.info(f"DIFFS API CALLED - Looking in: {diffs_dir.resolve()}")
        logger.info(f"DIFFS API CALLED - Dir exists: {diffs_dir.exists()}")
        
        if diffs_dir.exists():
            try:
                diff_file_list = list(diffs_dir.glob('*.txt'))
                print(f"Found {len(diff_file_list)} diff files: {[f.name for f in diff_file_list]}")
                logger.info(f"Found {len(diff_file_list)} diff files")
                sorted_files = sorted(diff_file_list, key=lambda f: f.stat().st_mtime, reverse=True)[:limit]
                
                for diff_file in sorted_files:
                    try:
                        content = diff_file.read_text(encoding='utf-8')
                        file_parts = diff_file.stem.split('.')
                        base_name = file_parts[0] if file_parts else diff_file.stem
                        
                        diff_files.append({
                            'id': diff_file.stem,
                            'filePath': base_name,
                            'timestamp': datetime.fromtimestamp(diff_file.stat().st_mtime).isoformat(),
                            'content': content[:500] + '...' if len(content) > 500 else content,
                            'size': len(content),
                            'fullPath': str(diff_file)
                        })
                        print(f"Processed diff file: {diff_file.name}")
                    except (UnicodeDecodeError, PermissionError) as e:
                        logger.warning(f"Could not read diff file {diff_file}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing diff file {diff_file}: {e}")
                        continue
                        
            except PermissionError:
                logger.error(f"Permission denied accessing diffs directory: {diffs_dir}")
                return jsonify({'error': 'Permission denied accessing diffs directory'}), 403
        else:
            print(f"Diffs directory does not exist: {diffs_dir}")
            logger.info(f"Diffs directory does not exist: {diffs_dir}")
        
        print(f"Returning {len(diff_files)} diff files")
        logger.info(f"Returning {len(diff_files)} diff files")
        return jsonify(diff_files)
        
    except Exception as e:
        print(f"Error retrieving diff files: {e}")
        logger.error(f"Error retrieving diff files: {e}")
        return jsonify({'error': 'Failed to retrieve diff files'}), 500

@app.route('/api/living-note', methods=['GET'])
def get_living_note():
    """Get the current living note content"""
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

@app.route('/api/living-note/clear', methods=['POST'])
def clear_living_note():
    """Clear the living note content"""
    try:
        living_note_path = Path('notes/living_note.md')
        
        if living_note_path.exists():
            # Clear the file
            living_note_path.write_text('', encoding='utf-8')
            logger.info("Living note cleared successfully")
            
            # Notify SSE clients of the change
            notify_living_note_change()
            
            return jsonify({
                'message': 'Living note cleared successfully'
            })
        else:
            return jsonify({'message': 'Living note file does not exist'}), 404
            
    except PermissionError:
        logger.error(f"Permission denied clearing living note: {living_note_path}")
        return jsonify({'error': 'Permission denied accessing living note file'}), 403
    except Exception as e:
        logger.error(f"Error clearing living note: {e}")
        return jsonify({'error': f'Failed to clear living note: {str(e)}'}), 500

@app.route('/api/living-note/events')
def living_note_events():
    """SSE endpoint for living note updates"""
    def event_stream():
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        
        # Create a queue for this client
        client_queue = queue.Queue()
        sse_clients.append(client_queue)
        
        try:
            while True:
                try:
                    # Wait for events with timeout to send keepalive
                    message = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        except GeneratorExit:
            # Client disconnected
            if client_queue in sse_clients:
                sse_clients.remove(client_queue)
    
    return Response(event_stream(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    })

def notify_living_note_change():
    """Notify all SSE clients of living note changes"""
    if not sse_clients:
        return
    
    try:
        # Get the updated living note data
        living_note_path = Path('notes/living_note.md')
        
        if living_note_path.exists():
            content = living_note_path.read_text(encoding='utf-8')
            stat = living_note_path.stat()
            
            data = {
                'type': 'living_note_updated',
                'content': content,
                'lastUpdated': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'wordCount': len(content.split())
            }
        else:
            data = {
                'type': 'living_note_updated',
                'content': '',
                'lastUpdated': datetime.now().isoformat(),
                'wordCount': 0
            }
        
        # Send to all connected clients
        for client_queue in sse_clients[:]:  # Copy list to avoid modification during iteration
            try:
                client_queue.put_nowait(data)
            except:
                # Remove dead clients
                sse_clients.remove(client_queue)
                
    except Exception as e:
        logger.error(f"Error notifying living note change: {e}")

class LivingNoteFileHandler(FileSystemEventHandler):
    """File system event handler for living note changes"""
    
    def __init__(self, living_note_path):
        self.living_note_path = Path(living_note_path)
        
    def on_modified(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.resolve() == self.living_note_path.resolve():
                logger.info("Living note file modified, notifying clients")
                notify_living_note_change()

def start_living_note_watcher():
    """Start watching the living note file for changes"""
    global living_note_observer
    
    if living_note_observer is not None:
        return
    
    living_note_path = Path('notes/living_note.md')
    
    # Ensure the notes directory exists
    living_note_path.parent.mkdir(exist_ok=True)
    
    # Create the file if it doesn't exist
    if not living_note_path.exists():
        living_note_path.write_text('')
    
    # Set up file watcher
    event_handler = LivingNoteFileHandler(living_note_path)
    living_note_observer = Observer()
    living_note_observer.schedule(event_handler, str(living_note_path.parent), recursive=False)
    living_note_observer.start()
    
    logger.info(f"Started watching living note file: {living_note_path}")

def stop_living_note_watcher():
    """Stop watching the living note file"""
    global living_note_observer
    
    if living_note_observer is not None:
        living_note_observer.stop()
        living_note_observer.join()
        living_note_observer = None
        logger.info("Stopped living note file watcher")

@app.route('/api/events/clear', methods=['POST'])
def clear_recent_events():
    """Clear the recent events list"""
    global recent_events
    
    try:
        events_count = len(recent_events)
        recent_events.clear()
        
        logger.info(f"Cleared {events_count} recent events")
        return jsonify({
            'message': f'Cleared {events_count} recent events successfully',
            'clearedCount': events_count
        })
        
    except Exception as e:
        logger.error(f"Error clearing recent events: {e}")
        return jsonify({'error': f'Failed to clear recent events: {str(e)}'}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    # Load current configuration from settings and any saved config file
    config_file = Path('config.json')
    config_data = {
        'checkInterval': CHECK_INTERVAL,
        'openaiApiKey': os.getenv('OPENAI_API_KEY', ''),
        'aiModel': OPENAI_MODEL,
        'watchPaths': [str(NOTES_FOLDER)],  # Default to notes folder
        'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
        'periodicCheckEnabled': True  # Default to enabled
    }
    
    # Load from config file if it exists
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
                config_data.update(saved_config)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    return jsonify(config_data)

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available OpenAI models"""
    try:
        models = OpenAIClient.MODELS
        return jsonify({
            'models': models,
            'defaultModel': 'gpt-4o',
            'currentModel': OPENAI_MODEL
        })
    except Exception as e:
        return jsonify({
            'error': f'Failed to get models: {str(e)}',
            'models': {},
            'defaultModel': 'gpt-4o',
            'currentModel': OPENAI_MODEL
        }), 500

@app.route('/api/config', methods=['PUT'])
def update_config():
    """Update configuration"""
    data = request.json
    
    try:
        # Validate the configuration data
        valid_fields = ['checkInterval', 'openaiApiKey', 'aiModel', 'ignorePatterns', 'periodicCheckEnabled']
        config_data = {}
        
        for field in valid_fields:
            if field in data:
                config_data[field] = data[field]
        
        # Validate specific fields
        if 'checkInterval' in config_data:
            try:
                config_data['checkInterval'] = int(config_data['checkInterval'])
                if config_data['checkInterval'] < 1:
                    return jsonify({'error': 'Check interval must be at least 1 second'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid check interval value'}), 400
        
        if 'ignorePatterns' in config_data:
            if not isinstance(config_data['ignorePatterns'], list):
                return jsonify({'error': 'Ignore patterns must be a list'}), 400
        
        if 'periodicCheckEnabled' in config_data:
            if not isinstance(config_data['periodicCheckEnabled'], bool):
                return jsonify({'error': 'periodicCheckEnabled must be a boolean'}), 400
        
        # Save configuration to file
        config_file = Path('config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Update environment variable if API key is provided
        if 'openaiApiKey' in config_data and config_data['openaiApiKey']:
            os.environ['OPENAI_API_KEY'] = config_data['openaiApiKey']
        
        # Update running monitor if applicable
        global monitor_instance
        if monitor_instance and monitoring_active:
            if 'checkInterval' in config_data:
                monitor_instance.set_check_interval(config_data['checkInterval'])
            if 'periodicCheckEnabled' in config_data:
                monitor_instance.set_periodic_check_enabled(config_data['periodicCheckEnabled'])
        
        return jsonify({'message': 'Configuration updated successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to update configuration: {str(e)}'}), 500

@app.route('/api/files/tree', methods=['GET'])
def get_file_tree():
    """Get file tree structure"""
    path = request.args.get('path', '.')
    
    try:
        tree = build_file_tree(Path(path))
        return jsonify(tree)
    except PermissionError:
        logger.warning(f"Permission denied accessing path: {path}")
        return jsonify({'error': 'Permission denied'}), 403
    except FileNotFoundError:
        logger.warning(f"Path not found: {path}")
        return jsonify({'error': 'Path not found'}), 404
    except Exception as e:
        logger.error(f"Error building file tree for {path}: {e}")
        return jsonify({'error': 'Failed to build file tree'}), 500

def build_file_tree(path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
    """Build a file tree structure focusing on relevant directories and markdown files"""
    if current_depth > max_depth:
        return {}
    
    tree = {
        'name': path.name if path.name else str(path),
        'path': str(path),
        'type': 'directory' if path.is_dir() else 'file',
        'children': []
    }
    
    # Define directories to ignore
    ignore_dirs = {'node_modules', '__pycache__', '.git', '.vscode', 'dist', 'build', 'venv', 'env'}
    
    if path.is_dir():
        try:
            for child in sorted(path.iterdir()):
                # Skip hidden files and ignored directories
                if (child.name.startswith('.') or 
                    child.name in ignore_dirs or
                    child.name.endswith('.pyc')):
                    continue
                
                # Include directories and markdown files
                if child.is_dir():
                    # Only include directories that might contain relevant content
                    subtree = build_file_tree(child, max_depth, current_depth + 1)
                    if subtree and (subtree.get('children') or current_depth < 2):
                        tree['children'].append(subtree)
                elif child.suffix.lower() == '.md':
                    tree['children'].append(build_file_tree(child, max_depth, current_depth + 1))
        except PermissionError:
            pass
    
    return tree

# Custom event handler that integrates with the API
class APIAwareNoteChangeHandler(NoteChangeHandler):
    """Extended handler that also updates the API's event list"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def _add_event(self, event_type, file_path, size=None):
        """Add an event to the API's recent events list"""
        global recent_events
        
        try:
            file_size = size if size is not None else (
                file_path.stat().st_size if file_path.exists() else 0
            )
        except:
            file_size = 0
            
        event = {
            'id': f"event_{str(uuid.uuid4())[:8]}",
            'type': event_type,
            'path': str(file_path.relative_to(self.notes_folder.parent) if file_path.is_relative_to(self.notes_folder.parent) else file_path),
            'timestamp': datetime.now().isoformat(),
            'size': file_size
        }
        
        recent_events.append(event)
        
        # Keep only last 100 events
        if len(recent_events) > 100:
            recent_events = recent_events[-100:]
    
    def on_modified(self, event):
        """Override to add API event tracking"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('modified', file_path)
        super().on_modified(event)
    
    def on_created(self, event):
        """Override to add API event tracking"""
        file_path = Path(event.src_path)
        if not event.is_directory:
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('created', file_path)
        super().on_created(event)
    
    def on_deleted(self, event):
        """Override to add API event tracking"""
        file_path = Path(event.src_path)
        if not event.is_directory:
            if not self.ignore_handler.should_ignore(file_path) and self.watch_handler.should_watch(file_path):
                if file_path.suffix.lower() == '.md':
                    self._add_event('deleted', file_path, size=0)
        super().on_deleted(event)
    
    def on_moved(self, event):
        """Override to add API event tracking"""
        if not event.is_directory:
            src_path = Path(event.src_path)
            dest_path = Path(event.dest_path)
            
            # Check both paths
            src_ignored = self.ignore_handler.should_ignore(src_path)
            dest_ignored = self.ignore_handler.should_ignore(dest_path)
            src_watched = self.watch_handler.should_watch(src_path)
            dest_watched = self.watch_handler.should_watch(dest_path)
            
            if (not src_ignored and src_watched) or (not dest_ignored and dest_watched):
                if src_path.suffix.lower() == '.md' or dest_path.suffix.lower() == '.md':
                    self._add_event('moved', dest_path)
        super().on_moved(event)

# Modified ObbyMonitor to use our custom handler
class APIObbyMonitor(ObbyMonitor):
    """Extended ObbyMonitor that uses API-aware event handler"""
    
    def __init__(self):
        super().__init__()
        # Load check interval from config if available
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.json"""
        config_file = Path('config.json')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.check_interval = config.get('checkInterval', CHECK_INTERVAL)
                    logger.info(f"Loaded check interval from config: {self.check_interval}s")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
    
    def start(self):
        """Start the monitoring system with API integration"""
        if self.is_running:
            return
            
        # Setup
        from utils.file_helpers import ensure_directories, setup_test_file
        from diffing.diff_tracker import DiffTracker
        
        ensure_directories(DIFF_PATH, NOTES_FOLDER)
        setup_test_file(NOTES_FOLDER / "test.md")
        
        # Initialize components
        self.diff_tracker = DiffTracker(NOTES_FOLDER / "test.md", DIFF_PATH)
        self.ai_client = OpenAIClient()
        
        # Create custom file watcher with API-aware handler
        utils_folder = NOTES_FOLDER.parent / "utils"
        
        # Create the handler manually
        handler = APIAwareNoteChangeHandler(
            NOTES_FOLDER,
            self.diff_tracker,
            self.ai_client,
            LIVING_NOTE_PATH,
            utils_folder
        )
        
        # Create file watcher and inject our custom handler
        self.file_watcher = FileWatcher(
            NOTES_FOLDER,
            self.diff_tracker,
            self.ai_client,
            LIVING_NOTE_PATH,
            utils_folder
        )
        self.file_watcher.handler = handler  # Replace with our custom handler
        
        self.file_watcher.start()
        self.is_running = True
        
        # Start periodic checking thread if enabled
        if self.periodic_check_enabled:
            self.start_periodic_checking()

def run_monitor():
    """Run the monitor in a separate thread"""
    global monitor_instance, monitoring_active
    
    # The monitor now runs its own event loop via watchdog
    # This thread just keeps the monitor alive
    while monitoring_active and monitor_instance and monitor_instance.is_running:
        try:
            time.sleep(1)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            break

def is_today(timestamp_str: str) -> bool:
    """Check if timestamp is from today"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return timestamp.date() == datetime.now().date()
    except:
        return False

# Static file serving for production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the React frontend"""
    frontend_dir = Path('frontend/dist')
    
    # If frontend build exists, serve it
    if frontend_dir.exists():
        if path and (frontend_dir / path).exists():
            return send_from_directory(frontend_dir, path)
        # For React Router, serve index.html for any non-API routes
        elif not path.startswith('api/'):
            return send_from_directory(frontend_dir, 'index.html')
    
    # Fallback for development or missing frontend
    return jsonify({
        'message': 'Obby API Server',
        'version': '1.0.0',
        'endpoints': {
            'status': '/api/status',
            'monitor': '/api/monitor/start|stop',
            'events': '/api/events',
            'diffs': '/api/diffs',
            'living-note': '/api/living-note',
            'config': '/api/config',
            'files': '/api/files/tree'
        },
        'frontend': 'Build frontend with: cd frontend && npm run build'
    })

if __name__ == '__main__':
    logger.info("Starting Obby API server on http://localhost:8001")
    logger.info("Web interface will be available once the server starts")
    
    # Start the living note file watcher
    start_living_note_watcher()
    
    try:
        app.run(debug=True, port=8001, host='0.0.0.0', threaded=True)
    finally:
        # Clean up on shutdown
        stop_living_note_watcher()