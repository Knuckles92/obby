from flask import Flask, jsonify, request
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

from core.monitor import ObbyMonitor
from config.settings import CHECK_INTERVAL, OPENAI_MODEL, NOTES_FOLDER
from ai.openai_client import OpenAIClient
from utils.file_watcher import FileWatcher, NoteChangeHandler

app = Flask(__name__)
CORS(app)

# Global variables for monitoring state
monitor_instance = None
monitor_thread = None
monitoring_active = False
recent_events = []
recent_diffs = []

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
    limit = request.args.get('limit', 50, type=int)
    return jsonify(recent_events[-limit:])

@app.route('/api/diffs', methods=['GET'])
def get_recent_diffs():
    """Get recent diff files"""
    limit = request.args.get('limit', 20, type=int)
    
    diffs_dir = Path('diffs')
    diff_files = []
    
    if diffs_dir.exists():
        for diff_file in sorted(diffs_dir.glob('*.diff'), key=os.path.getmtime, reverse=True)[:limit]:
            try:
                content = diff_file.read_text(encoding='utf-8')
                diff_files.append({
                    'id': diff_file.stem,
                    'filePath': diff_file.stem.split('_')[0] if '_' in diff_file.stem else diff_file.stem,
                    'timestamp': datetime.fromtimestamp(diff_file.stat().st_mtime).isoformat(),
                    'content': content[:500] + '...' if len(content) > 500 else content,
                    'size': len(content)
                })
            except Exception as e:
                print(f"Error reading diff file {diff_file}: {e}")
    
    return jsonify(diff_files)

@app.route('/api/living-note', methods=['GET'])
def get_living_note():
    """Get the current living note content"""
    living_note_path = Path('living_note.md')
    
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
        'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store']
    }
    
    # Load from config file if it exists
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
                config_data.update(saved_config)
        except Exception as e:
            print(f"Error loading config file: {e}")
    
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
        valid_fields = ['checkInterval', 'openaiApiKey', 'aiModel', 'watchPaths', 'ignorePatterns']
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
        
        if 'watchPaths' in config_data:
            if not isinstance(config_data['watchPaths'], list):
                return jsonify({'error': 'Watch paths must be a list'}), 400
        
        if 'ignorePatterns' in config_data:
            if not isinstance(config_data['ignorePatterns'], list):
                return jsonify({'error': 'Ignore patterns must be a list'}), 400
        
        # Save configuration to file
        config_file = Path('config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Update environment variable if API key is provided
        if 'openaiApiKey' in config_data and config_data['openaiApiKey']:
            os.environ['OPENAI_API_KEY'] = config_data['openaiApiKey']
        
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

def run_monitor():
    """Run the monitor in a separate thread"""
    global monitor_instance, monitoring_active
    
    # The monitor now runs its own event loop via watchdog
    # This thread just keeps the monitor alive
    while monitoring_active and monitor_instance and monitor_instance.is_running:
        try:
            time.sleep(1)
        except Exception as e:
            print(f"Monitor error: {e}")
            break

def is_today(timestamp_str: str) -> bool:
    """Check if timestamp is from today"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return timestamp.date() == datetime.now().date()
    except:
        return False

if __name__ == '__main__':
    print("Starting Obby API server...")
    app.run(debug=True, port=8000, host='0.0.0.0')