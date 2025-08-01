from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import threading
import logging
import os
from pathlib import Path

# Import blueprint modules
from routes.monitoring import monitoring_bp
from routes.files import files_bp
from routes.living_note import living_note_bp
from routes.search import search_bp
from routes.config import config_bp
from routes.data import data_bp
from routes.admin import admin_bp

# Import API-aware monitoring classes
from routes.api_monitor import APIObbyMonitor

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

# Register blueprints
app.register_blueprint(monitoring_bp)
app.register_blueprint(files_bp)
app.register_blueprint(living_note_bp)
app.register_blueprint(search_bp)
app.register_blueprint(config_bp)
app.register_blueprint(data_bp)
app.register_blueprint(admin_bp)

# Initialize monitoring routes with shared state
from routes.monitoring import init_monitoring_routes
init_monitoring_routes(monitor_instance, monitor_thread, monitoring_active)

# Helper function for monitor thread
def run_monitor():
    """Run the monitor in a separate thread"""
    global monitor_instance
    try:
        if monitor_instance:
            monitor_instance.start()
    except Exception as e:
        logger.error(f"Monitor thread error: {e}")
        global monitoring_active
        monitoring_active = False


# Backwards compatibility routes that redirect to blueprint routes
@app.route('/api/diffs/<diff_id>', methods=['GET'])
def get_full_diff_content_compat(diff_id):
    """Backwards compatibility: redirect to files blueprint"""
    from flask import redirect, url_for
    return redirect(url_for('files.get_full_diff_content', diff_id=diff_id))


@app.route('/api/events/clear', methods=['POST'])
def clear_recent_events_compat():
    """Backwards compatibility: redirect to data blueprint"""
    from flask import redirect, url_for
    return redirect(url_for('data.clear_recent_events'), code=307)


@app.route('/api/diffs/clear', methods=['POST'])
def clear_recent_diffs_compat():
    """Backwards compatibility: redirect to data blueprint"""
    from flask import redirect, url_for
    return redirect(url_for('data.clear_recent_diffs'), code=307)


@app.route('/api/config', methods=['GET'])
def get_config_compat():
    """Backwards compatibility: redirect to config blueprint"""
    from flask import redirect, url_for
    return redirect(url_for('config.get_config_root'))


@app.route('/api/config', methods=['PUT'])
def update_config_compat():
    """Backwards compatibility: redirect to config blueprint"""
    from flask import redirect, url_for
    return redirect(url_for('config.update_config_root'), code=307)


@app.route('/api/models', methods=['GET'])
def get_models_compat():
    """Backwards compatibility: redirect to config blueprint"""
    from flask import redirect, url_for
    return redirect(url_for('config.get_models'))


@app.route('/api/search', methods=['GET'])
def search_compat():
    """Backwards compatibility: redirect to search blueprint"""
    from flask import redirect, url_for
    args = '&'.join([f'{k}={v}' for k, v in request.args.items()])
    redirect_url = url_for('search.search_semantic_index_get')
    if args:
        redirect_url += f'?{args}'
    return redirect(redirect_url)


# Static file serving for production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path=''):
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
            'monitoring': '/api/monitor/*',
            'files': '/api/files/*',
            'living-note': '/api/living-note/*',
            'search': '/api/search/*',
            'config': '/api/config/*',
            'data': '/api/data/*',
            'admin': '/api/admin/*'
        },
        'frontend': 'Build frontend with: cd frontend && npm run build'
    })


if __name__ == '__main__':
    logger.info("Starting Obby API server on http://localhost:8001")
    logger.info("Web interface will be available once the server starts")
    
    # Start the living note file watcher
    from routes.living_note import start_living_note_watcher, stop_living_note_watcher
    start_living_note_watcher()
    
    try:
        app.run(debug=True, port=8001, host='0.0.0.0', threaded=True)
    finally:
        # Clean up on shutdown
        stop_living_note_watcher()
