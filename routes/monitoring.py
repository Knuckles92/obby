"""
Monitoring and Control API routes
Handles file monitoring start/stop, status, and scanning operations
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime
from pathlib import Path
from database.queries import EventQueries

logger = logging.getLogger(__name__)

monitoring_bp = APIRouter(prefix='/api/monitor', tags=['monitor'])

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


@monitoring_bp.get('/status')
async def get_status():
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

        # Initialize watch and ignore handlers for STRICT filtering (matches /api/files/watched)
        try:
            from utils.watch_handler import WatchHandler
            from utils.ignore_handler import IgnoreHandler
            from config.settings import get_configured_notes_folder

            root_folder = Path(__file__).parent.parent
            watch_handler = WatchHandler(root_folder)
            notes_folder = get_configured_notes_folder()
            ignore_handler = IgnoreHandler(root_folder, notes_folder)

            # Count files in watched directories with strict filtering
            for path in watched_paths:
                if os.path.exists(path):
                    path_obj = Path(path).resolve()  # Convert to absolute path
                    for f in path_obj.rglob('*.md'):
                        if f.is_file():
                            # Skip hidden files and directories
                            if any(part.startswith('.') for part in f.parts):
                                continue

                            # STRICT: Apply ignore patterns
                            if ignore_handler.should_ignore(f):
                                continue

                            # STRICT: Apply watch patterns (pass resolved absolute path)
                            if not watch_handler.should_watch(f.resolve()):
                                continue

                            total_files += 1
        except Exception as e:
            logger.warning(f"Could not apply watch/ignore filters, using simple count: {e}")
            # Fallback to simple counting if handlers fail
            for path in watched_paths:
                if os.path.exists(path):
                    path_obj = Path(path)
                    for f in path_obj.rglob('*.md'):
                        if f.is_file():
                            rel_path = f.relative_to(path_obj) if f.is_relative_to(path_obj) else f
                            if not any(part.startswith('.') for part in rel_path.parts):
                                total_files += 1

    return {
        'isActive': monitoring_active,
        'watchedPaths': watched_paths,
        'totalFiles': total_files,
        'eventsToday': events_today
    }


@monitoring_bp.post('/start')
async def start_monitoring():
    """Start file monitoring"""
    global monitor_instance, monitor_thread, monitoring_active
    
    if monitoring_active:
        return {'success': True, 'message': 'Monitoring is already active', 'status': 'already_running'}
    
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
        return {'success': True, 'message': 'Monitoring started successfully'}
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        return JSONResponse({'success': False, 'message': f'Failed to start monitoring: {str(e)}', 'error': str(e)}, status_code=500)


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

        # Initialize watch and ignore handlers for STRICT filtering (matches /api/files/watched)
        try:
            from utils.watch_handler import WatchHandler
            from utils.ignore_handler import IgnoreHandler
            from config.settings import get_configured_notes_folder

            root_folder = Path(__file__).parent.parent
            watch_handler = WatchHandler(root_folder)
            notes_folder = get_configured_notes_folder()
            ignore_handler = IgnoreHandler(root_folder, notes_folder)

            # Count total files being watched with strict filtering
            total_files = 0
            for path in watched_paths:
                if os.path.exists(path):
                    path_obj = Path(path).resolve()  # Convert to absolute path
                    for f in path_obj.rglob('*.md'):
                        if f.is_file():
                            # Skip hidden files and directories
                            if any(part.startswith('.') for part in f.parts):
                                continue

                            # STRICT: Apply ignore patterns
                            if ignore_handler.should_ignore(f):
                                continue

                            # STRICT: Apply watch patterns (pass resolved absolute path)
                            if not watch_handler.should_watch(f.resolve()):
                                continue

                            total_files += 1
        except Exception as e:
            logger.warning(f"Could not apply watch/ignore filters in status, using simple count: {e}")
            # Fallback to simple counting if handlers fail
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

    return status


@monitoring_bp.post('/stop')
async def stop_monitoring():
    """Stop file monitoring"""
    global monitor_instance, monitor_thread, monitoring_active
    
    if not monitoring_active:
        return {'success': True, 'message': 'Monitoring was not active'}
    
    try:
        logger.info("Stopping monitoring system...")
        
        if monitor_instance:
            monitor_instance.stop()
        
        monitoring_active = False
        monitor_instance = None
        monitor_thread = None
        
        logger.info("Monitoring stopped successfully")
        return {'success': True, 'message': 'Monitoring stopped successfully'}
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        return JSONResponse({'success': False, 'message': f'Failed to stop monitoring: {str(e)}', 'error': str(e)}, status_code=500)


@monitoring_bp.post('/scan')
async def scan_files():
    """Manually scan files for changes"""
    global monitor_instance
    
    if not monitor_instance:
        return JSONResponse({'success': False, 'message': 'Monitoring is not active'}, status_code=400)
    
    try:
        # Trigger a manual scan
        logger.info("Starting manual file scan...")
        
        # Force a check for changes
        if hasattr(monitor_instance, 'force_check'):
            monitor_instance.force_check()
        
        return {'success': True, 'message': 'Manual scan completed'}
    except Exception as e:
        logger.error(f"Manual scan failed: {e}")
        return JSONResponse({'success': False, 'message': f'Manual scan failed: {str(e)}', 'error': str(e)}, status_code=500)



@monitoring_bp.post('/comprehensive-summary/generate')
async def generate_comprehensive_summary(request: Request):
    """Generate a comprehensive summary with async worker pattern"""
    try:
        import threading
        from services.comprehensive_summary_worker import run_comprehensive_worker
        
        # Get request data
        data = await request.json() if request.headers.get('content-type','').startswith('application/json') else {}
        force = bool(data.get('force', False))
        run_async = bool(data.get('async', True))
        max_duration = float(data.get('max_duration_secs', 2.0))
        
        logger.info("Comprehensive summary generation triggered (async mode)")
        
        # Always launch worker
        result_box = {'result': None}
        worker = threading.Thread(target=run_comprehensive_worker, args=(force, result_box), daemon=True)
        worker.start()
        
        if run_async:
            return JSONResponse({
                'accepted': True,
                'success': True,
                'message': 'Comprehensive summary generation started in background'
            }, status_code=202)
        
        # Synchronous path with protective ceiling
        worker.join(timeout=max(0.0, max_duration))
        if result_box['result'] is not None:
            return result_box['result']
        
        return JSONResponse({
            'accepted': True,
            'success': True,
            'message': 'Comprehensive summary generation continuing in background'
        }, status_code=202)
        
    except Exception as e:
        logger.error(f"Comprehensive summary generation failed: {e}")
        return JSONResponse({
            'success': False,
            'message': f'Comprehensive summary generation failed: {str(e)}',
            'result': {
                'processed': False,
                'changes_count': 0,
                'processing_time': 0,
                'error': str(e)
            }
        }, status_code=500)




@monitoring_bp.get('/comprehensive-summary/list')
async def get_comprehensive_summaries(request: Request):
    """Get paginated list of comprehensive summaries"""
    try:
        from database.models import ComprehensiveSummaryModel
        
        # Get pagination parameters from query string
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Validate parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50:
            page_size = 10
        
        data = ComprehensiveSummaryModel.get_summaries_paginated(page=page, page_size=page_size)
        return data
        
    except Exception as e:
        logger.error(f"Failed to get comprehensive summaries: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@monitoring_bp.get('/comprehensive-summary/status')
async def get_comprehensive_status():
    """Get comprehensive summary generation status (for polling)"""
    try:
        from services.comprehensive_summary_worker import get_comprehensive_status as get_status_data
        return get_status_data()
    except Exception as e:
        logger.error(f"Failed to get comprehensive status: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@monitoring_bp.get('/comprehensive-summary/{summary_id}')
async def get_comprehensive_summary(summary_id: int):
    """Get details of a specific comprehensive summary"""
    try:
        from database.models import ComprehensiveSummaryModel, db
        
        # Ensure migration is applied before querying
        migration_success = False
        try:
            from database.migration_comprehensive_summaries import apply_migration
            migration_success = apply_migration()
        except Exception as migration_error:
            logger.error(f"Failed to ensure comprehensive_summaries migration: {migration_error}", exc_info=True)
        
        # Check if table exists
        table_check_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='comprehensive_summaries'
        """
        table_exists = db.execute_query(table_check_query)
        
        if not table_exists:
            return JSONResponse({'error': 'Comprehensive summaries table not available'}, status_code=503)

        query = """
            SELECT * FROM comprehensive_summaries WHERE id = ?
        """
        rows = db.execute_query(query, (summary_id,))

        if not rows:
            return JSONResponse({'error': 'Comprehensive summary not found'}, status_code=404)

        summary = dict(rows[0])
        # Parse JSON fields
        import json
        summary['key_topics'] = json.loads(summary['key_topics']) if summary['key_topics'] else []
        summary['key_keywords'] = json.loads(summary['key_keywords']) if summary['key_keywords'] else []

        return summary

    except Exception as e:
        logger.error(f"Failed to get comprehensive summary {summary_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@monitoring_bp.delete('/comprehensive-summary/{summary_id}')
async def delete_comprehensive_summary(summary_id: int):
    """Delete a specific comprehensive summary"""
    try:
        from database.models import ComprehensiveSummaryModel

        success = ComprehensiveSummaryModel.delete_summary(summary_id)

        if success:
            return {'success': True, 'message': f'Comprehensive summary {summary_id} deleted successfully'}
        else:
            return JSONResponse({'error': 'Comprehensive summary not found'}, status_code=404)

    except Exception as e:
        logger.error(f"Failed to delete comprehensive summary {summary_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


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
