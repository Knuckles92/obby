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

# Import database layer
from database.queries import DiffQueries, EventQueries, SemanticQueries, ConfigQueries, AnalyticsQueries

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
# Note: recent_events and recent_diffs now stored in database

# SSE client management
sse_clients = []

# SSE clients for real-time updates
living_note_observer = None

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current monitoring status"""
    global monitoring_active, monitor_instance
    
    watched_paths = []
    total_files = 0
    
    # Get events today from database instead of memory
    try:
        events_today = EventQueries.get_events_today_count()
    except Exception as e:
        logger.error(f"Failed to get events count from database: {e}")
        events_today = 0
    
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
    """Get recent file events from database"""
    try:
        limit = max(1, min(request.args.get('limit', 50, type=int), 200))  # Limit between 1-200
        events = EventQueries.get_recent_events(limit=limit)
        logger.info(f"Retrieved {len(events)} events from database")
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error retrieving recent events: {e}")
        return jsonify({'error': 'Failed to retrieve events'}), 500

@app.route('/api/diffs', methods=['GET'])
def get_recent_diffs():
    """Get recent diff files from database"""
    try:
        limit = max(1, min(request.args.get('limit', 20, type=int), 100))  # Limit between 1-100
        
        logger.info(f"DATABASE DIFFS API CALLED - Limit: {limit}")
        
        # Use database queries instead of file operations
        diff_files = DiffQueries.get_recent_diffs(limit=limit)
        
        logger.info(f"Retrieved {len(diff_files)} diffs from database")
        return jsonify(diff_files)
        
    except Exception as e:
        logger.error(f"Error retrieving diffs from database: {e}")
        return jsonify({'error': 'Failed to retrieve diff files'}), 500

@app.route('/api/diffs/<diff_id>', methods=['GET'])
def get_full_diff_content(diff_id):
    """Get full diff content by ID"""
    try:
        logger.info(f"FULL DIFF CONTENT API CALLED - ID: {diff_id}")
        
        # Get full diff content from database
        diff_data = DiffQueries.get_diff_content(diff_id)
        
        if diff_data is None:
            logger.warning(f"Diff not found: {diff_id}")
            return jsonify({'error': 'Diff not found'}), 404
        
        logger.info(f"Retrieved full diff content for ID: {diff_id}")
        return jsonify({
            'id': diff_id,
            'content': diff_data['content']  # Extract just the content string
        })
        
    except Exception as e:
        logger.error(f"Error retrieving full diff content: {e}")
        return jsonify({'error': 'Failed to retrieve diff content'}), 500

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

@app.route('/api/living-note/settings', methods=['GET'])
def get_living_note_settings():
    """Get living note customization settings"""
    try:
        settings_file = Path('config/living_note_settings.json')
        
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            # Return default settings
            settings = {
                'updateFrequency': 'realtime',
                'summaryLength': 'moderate', 
                'writingStyle': 'technical',
                'includeMetrics': True,
                'autoUpdate': True,
                'maxSections': 10,
                'focusAreas': []
            }
            
        return jsonify(settings)
        
    except Exception as e:
        logger.error(f"Error getting living note settings: {e}")
        return jsonify({'error': f'Failed to get settings: {str(e)}'}), 500

@app.route('/api/living-note/settings', methods=['POST'])
def save_living_note_settings():
    """Save living note customization settings"""
    try:
        settings_data = request.get_json()
        
        if not settings_data:
            return jsonify({'error': 'No settings data provided'}), 400
            
        # Validate settings
        valid_frequencies = ['realtime', 'hourly', 'daily', 'weekly', 'manual']
        valid_lengths = ['brief', 'moderate', 'detailed']
        valid_styles = ['technical', 'casual', 'formal', 'bullet-points']
        
        if settings_data.get('updateFrequency') not in valid_frequencies:
            return jsonify({'error': 'Invalid update frequency'}), 400
            
        if settings_data.get('summaryLength') not in valid_lengths:
            return jsonify({'error': 'Invalid summary length'}), 400
            
        if settings_data.get('writingStyle') not in valid_styles:
            return jsonify({'error': 'Invalid writing style'}), 400
            
        if not isinstance(settings_data.get('maxSections', 10), int) or settings_data.get('maxSections', 10) < 1:
            return jsonify({'error': 'Max sections must be a positive integer'}), 400
            
        if not isinstance(settings_data.get('focusAreas', []), list):
            return jsonify({'error': 'Focus areas must be a list'}), 400
        
        # Ensure config directory exists
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)
        
        # Save settings
        settings_file = config_dir / 'living_note_settings.json'
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)
            
        logger.info(f"Living note settings saved: {settings_data}")
        return jsonify({
            'message': 'Settings saved successfully',
            'settings': settings_data
        })
        
    except Exception as e:
        logger.error(f"Error saving living note settings: {e}")
        return jsonify({'error': f'Failed to save settings: {str(e)}'}), 500

@app.route('/api/living-note/update', methods=['POST'])
def trigger_living_note_update():
    """Simple update button - trigger a living note update"""
    try:
        # Get current settings (but don't enforce restrictions)
        settings_file = Path('config/living_note_settings.json')
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {'updateFrequency': 'manual', 'summaryLength': 'moderate', 'writingStyle': 'technical'}
            
        # Always allow updates - no frequency restrictions
        from ai.openai_client import OpenAIClient
        
        ai_client = OpenAIClient()
        living_note_path = Path('notes/living_note.md')
        
        # Create a simple summary
        summary = "Update triggered - summarizing recent activity"
        ai_client.update_living_note(living_note_path, summary, "manual", settings)
        
        logger.info("Living note update triggered")
        return jsonify({
            'message': 'Living note update completed successfully'
        })
                
    except Exception as e:
        logger.error(f"Error during update: {e}")
        return jsonify({'error': f'Failed to trigger update: {str(e)}'}), 500


@app.route('/api/living-note/events', methods=['GET'])
def living_note_events():
    """SSE endpoint for living note updates"""
    try:
        logger.info("SSE endpoint called, starting event stream")
        
        def event_stream():
            client_queue = None
            try:
                logger.info("Creating event stream generator")
                # Send initial connection message
                yield f"data: {json.dumps({'type': 'connected'})}\n\n"
                
                # Create a queue for this client
                client_queue = queue.Queue()
                sse_clients.append(client_queue)
                logger.info(f"Added client to SSE clients list. Total clients: {len(sse_clients)}")
                
                while True:
                    try:
                        # Wait for events with timeout to send keepalive
                        message = client_queue.get(timeout=30)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send keepalive
                        yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
            except GeneratorExit:
                logger.info("Client disconnected from SSE stream")
                # Client disconnected
                if client_queue and client_queue in sse_clients:
                    sse_clients.remove(client_queue)
                    logger.info(f"Removed client from SSE clients list. Total clients: {len(sse_clients)}")
            except Exception as e:
                logger.error(f"Error in SSE event stream: {e}", exc_info=True)
                if client_queue and client_queue in sse_clients:
                    sse_clients.remove(client_queue)
                raise
        
        return Response(event_stream(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        })
    except Exception as e:
        logger.error(f"Error setting up SSE endpoint: {e}", exc_info=True)
        return jsonify({'error': f'SSE endpoint error: {str(e)}'}), 500

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
    """Clear all events from database"""
    try:
        result = EventQueries.clear_all_events()
        logger.info(f"Cleared events via database: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error clearing recent events: {e}")
        return jsonify({'error': f'Failed to clear recent events: {str(e)}'}), 500

@app.route('/api/diffs/clear', methods=['POST'])
def clear_recent_diffs():
    """Clear all diffs from database"""
    try:
        result = DiffQueries.clear_all_diffs()
        logger.info(f"Cleared diffs via database: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error clearing recent diffs: {e}")
        return jsonify({'error': f'Failed to clear recent diffs: {str(e)}'}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration from database"""
    try:
        config_data = ConfigQueries.get_config()
        logger.info("Retrieved configuration from database")
        return jsonify(config_data)
    except Exception as e:
        logger.error(f"Error loading config from database: {e}")
        # Fallback to defaults
        return jsonify({
            'checkInterval': CHECK_INTERVAL,
            'openaiApiKey': os.getenv('OPENAI_API_KEY', ''),
            'aiModel': OPENAI_MODEL,
            'watchPaths': [str(NOTES_FOLDER)],
            'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
            'periodicCheckEnabled': True
        })

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
    """Update configuration in database"""
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
        
        # Update configuration in database
        result = ConfigQueries.update_config(config_data)
        
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
        
        return jsonify(result)
    
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

@app.route('/api/search', methods=['GET'])
def search_semantic_index():
    """Search the semantic index from database"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    change_type = request.args.get('type', '').strip()  # content, tree, or empty for all
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    try:
        # Use database search instead of file operations
        result = SemanticQueries.search_semantic(query, limit, change_type)
        logger.info(f"Semantic search returned {len(result.get('results', []))} results")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error searching semantic index: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/api/search/topics', methods=['GET'])
def get_semantic_topics():
    """Get all available topics from database"""
    logger.info("get_semantic_topics route called")
    try:
        result = SemanticQueries.get_all_topics()
        logger.info(f"Retrieved {result.get('total', 0)} topics from database")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting semantic topics: {e}")
        return jsonify({'error': f'Failed to get topics: {str(e)}'}), 500

@app.route('/api/search/keywords', methods=['GET'])
def get_semantic_keywords():
    """Get all available keywords from database"""
    try:
        result = SemanticQueries.get_all_keywords()
        logger.info(f"Retrieved {result.get('total', 0)} keywords from database")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting semantic keywords: {e}")
        return jsonify({'error': f'Failed to get keywords: {str(e)}'}), 500

# Custom event handler that integrates with the API
class APIAwareNoteChangeHandler(NoteChangeHandler):
    """Extended handler that also updates the API's event list"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def _add_event(self, event_type, file_path, size=None):
        """Add an event to the database instead of memory"""
        try:
            file_size = size if size is not None else (
                file_path.stat().st_size if file_path.exists() else 0
            )
        except:
            file_size = 0
            
        # Store event in database instead of memory
        path_str = str(file_path.relative_to(self.notes_folder.parent) if file_path.is_relative_to(self.notes_folder.parent) else file_path)
        
        try:
            EventQueries.add_event(event_type, path_str, file_size)
            logger.debug(f"Added event to database: {event_type} {path_str}")
        except Exception as e:
            logger.error(f"Failed to add event to database: {e}")
            # Log fallback error but don't maintain in-memory storage
            logger.warning(f"Database event storage failed, event lost: {event_type} {path_str}")
    
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

# Legacy function removed - date filtering now handled in database queries

# Static file serving for production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the React frontend"""
    logger.info(f"serve_frontend called with path: '{path}'")
    
    # Don't handle API routes here - let them be handled by specific routes
    if path.startswith('/api/'):
        # This should not happen if routes are registered properly
        logger.warning(f"API path {path} reached catch-all route - this indicates a routing issue")
        return jsonify({'error': 'API endpoint not found'}), 404
    
    frontend_dir = Path('frontend/dist')
    
    # If frontend build exists, serve it
    if frontend_dir.exists():
        if path and (frontend_dir / path).exists():
            return send_from_directory(frontend_dir, path)
        # For React Router, serve index.html for any non-API routes
        else:
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