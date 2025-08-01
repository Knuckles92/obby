"""
Monitoring and Control API routes
Handles file monitoring start/stop, status, and scanning operations
"""

from flask import Blueprint, jsonify, request
import logging
import os
from pathlib import Path
from database.queries import EventQueries

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitor')

# Global variables for monitoring state (will be injected by main app)
monitor_instance = None
monitor_thread = None
monitoring_active = False


def init_monitoring_routes(app_monitor_instance, app_monitor_thread, app_monitoring_active):
    """Initialize monitoring routes with shared state from main app"""
    global monitor_instance, monitor_thread, monitoring_active
    monitor_instance = app_monitor_instance
    monitor_thread = app_monitor_thread
    monitoring_active = app_monitoring_active


@monitoring_bp.route('/status', methods=['GET'])
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


@monitoring_bp.route('/start', methods=['POST'])
def start_monitoring():
    """Start file monitoring"""
    global monitor_instance, monitor_thread, monitoring_active
    
    if monitoring_active:
        return jsonify({
            'success': True,
            'message': 'Monitoring is already active',
            'status': 'already_running'
        })
    
    try:
        from core.monitor import ObbyMonitor
        from routes.api_monitor import APIObbyMonitor
        import threading
        
        logger.info("Starting monitoring system...")
        
        # Create monitor instance
        monitor_instance = APIObbyMonitor()
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        
        monitoring_active = True
        
        logger.info("Monitoring started successfully")
        return jsonify({
            'success': True,
            'message': 'Monitoring started successfully'
        })
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to start monitoring: {str(e)}'
        }), 500


def get_monitoring_status():
    """Get monitoring system status"""
    global monitoring_active, monitor_instance
    
    status = {
        'is_active': monitoring_active,
        'watched_paths': [],
        'total_watched_files': 0,
        'last_scan_time': None,
        'errors': []
    }
    
    if monitor_instance and monitoring_active:
        # Get watched paths from monitor
        watched_paths = getattr(monitor_instance, 'watched_paths', [])
        status['watched_paths'] = watched_paths
        
        # Count total files being watched
        total_files = 0
        for path in watched_paths:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for file in files:
                        if file.endswith('.md'):
                            total_files += 1
        
        status['total_watched_files'] = total_files
        status['last_scan_time'] = getattr(monitor_instance, 'last_scan_time', None)
    
    return jsonify(status)


@monitoring_bp.route('/stop', methods=['POST'])
def stop_monitoring():
    """Stop file monitoring"""
    global monitor_instance, monitor_thread, monitoring_active
    
    if not monitoring_active:
        return jsonify({
            'success': True,
            'message': 'Monitoring was not active'
        })
    
    try:
        logger.info("Stopping monitoring system...")
        
        if monitor_instance:
            monitor_instance.stop()
        
        monitoring_active = False
        monitor_instance = None
        monitor_thread = None
        
        logger.info("Monitoring stopped successfully")
        return jsonify({
            'success': True,
            'message': 'Monitoring stopped successfully'
        })
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to stop monitoring: {str(e)}'
        }), 500


@monitoring_bp.route('/scan', methods=['POST'])
def scan_files():
    """Manually scan files for changes"""
    global monitor_instance
    
    if not monitor_instance:
        return jsonify({
            'success': False,
            'message': 'Monitoring is not active'
        }), 400
    
    try:
        # Trigger a manual scan
        logger.info("Starting manual file scan...")
        
        # Force a check for changes
        if hasattr(monitor_instance, 'force_check'):
            monitor_instance.force_check()
        
        return jsonify({
            'success': True,
            'message': 'Manual scan completed'
        })
    except Exception as e:
        logger.error(f"Manual scan failed: {e}")
        return jsonify({
            'success': False,
            'message': f'Manual scan failed: {str(e)}'
        }), 500


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
