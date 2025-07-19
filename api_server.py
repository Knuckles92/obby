from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import os
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime

from main import ObbyMonitor
from config.settings import CHECK_INTERVAL, OPENAI_MODEL, NOTES_FOLDER
from ai.openai_client import OpenAIClient

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
                total_files += sum(1 for f in Path(path).rglob('*.md') if f.is_file())
    
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
        monitor_instance = ObbyMonitor()
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        monitoring_active = True
        
        return jsonify({'message': 'Monitoring started successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitoring():
    """Stop file monitoring"""
    global monitoring_active, monitor_instance
    
    monitoring_active = False
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
    return jsonify({
        'checkInterval': CHECK_INTERVAL,
        'openaiModel': OPENAI_MODEL,
        'notesFolder': NOTES_FOLDER
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
    """Update configuration"""
    data = request.json
    
    # Here you would update the configuration
    # For now, just return success
    return jsonify({'message': 'Configuration updated successfully'})

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
    """Build a file tree structure"""
    if current_depth > max_depth:
        return {}
    
    tree = {
        'name': path.name if path.name else str(path),
        'path': str(path),
        'type': 'directory' if path.is_dir() else 'file',
        'children': []
    }
    
    if path.is_dir():
        try:
            for child in sorted(path.iterdir()):
                if not child.name.startswith('.') and not child.name == '__pycache__':
                    if child.is_dir() or child.suffix == '.md':
                        tree['children'].append(build_file_tree(child, max_depth, current_depth + 1))
        except PermissionError:
            pass
    
    return tree

def run_monitor():
    """Run the monitor in a separate thread"""
    global monitor_instance, monitoring_active, recent_events
    
    while monitoring_active and monitor_instance:
        try:
            # This would integrate with your existing monitoring logic
            # For now, simulate some activity
            time.sleep(5)
            
            # Add mock event for demonstration
            recent_events.append({
                'id': f"event_{int(time.time())}",
                'type': 'modified',
                'path': 'notes/example.md',
                'timestamp': datetime.now().isoformat(),
                'size': 1024
            })
            
            # Keep only last 100 events
            if len(recent_events) > 100:
                recent_events = recent_events[-100:]
                
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