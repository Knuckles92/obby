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








@monitoring_bp.post('/batch-ai/trigger')
async def trigger_manual_ai_processing(request: Request):
    """Manually trigger AI processing for recent file changes"""
    try:
        from database.queries import FileQueries
        from database.models import SemanticModel
        from ai.openai_client import OpenAIClient
        import time
        
        start_time = time.time()
        
        # Get request data
        data = await request.json() if request.headers.get('content-type','').startswith('application/json') else {}
        force = data.get('force', True)
        
        logger.info(f"Manual AI processing triggered (force={force})")
        
        # Get or create singleton AI client and ensure it's warmed up
        ai_client = OpenAIClient.get_instance()
        # Warm-up is handled automatically in the summarize_diff method if needed
        
        # Get ALL file changes that don't have AI summaries yet (no limit for comprehensive processing)
        recent_changes = FileQueries.get_recent_changes_without_ai_summary(limit=None)
        
        if not recent_changes:
            return {
                'success': True,
                'message': 'No new changes found to process',
                'result': {
                    'processed': True,
                    'changes_count': 0,
                    'processing_time': time.time() - start_time,
                    'reason': 'All recent changes already have AI summaries'
                }
            }
        
        changes_processed = 0
        
        # Process each change
        for change in recent_changes:
            try:
                # Get the content diff for this change
                diff_content = change.get('diff_content', '')
                file_path = change.get('file_path', '')
                
                if not diff_content:
                    logger.warning(f"No diff content for change: {file_path}")
                    continue
                
                # Generate AI summary (warm-up and retry logic are handled internally)
                ai_summary = ai_client.summarize_diff(diff_content)
                
                if ai_summary:
                    # Extract semantic metadata from the AI summary
                    metadata = ai_client.extract_semantic_metadata(ai_summary)
                    
                    # Map AI impact values to database schema values
                    impact_mapping = {
                        'brief': 'minor',
                        'medium': 'moderate', 
                        'major': 'significant',
                        'minor': 'minor',
                        'moderate': 'moderate',
                        'significant': 'significant'
                    }
                    ai_impact = metadata.get('impact', 'moderate')
                    db_impact = impact_mapping.get(ai_impact, 'moderate')
                    
                    # Store semantic entry with extracted metadata
                    semantic_id = SemanticModel.insert_entry(
                        summary=metadata.get('summary', ai_summary),
                        entry_type='diff',
                        impact=db_impact,
                        topics=metadata.get('topics', []),
                        keywords=metadata.get('keywords', []),
                        file_path=file_path
                    )
                    
                    if semantic_id:
                        changes_processed += 1
                        logger.info(f"Generated AI summary for {file_path} (ID: {semantic_id})")
                    
            except Exception as e:
                logger.error(f"Failed to process change for {change.get('file_path', 'unknown')}: {e}")
                continue
        
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'message': f'Successfully processed {changes_processed} changes',
            'result': {
                'processed': True,
                'changes_count': changes_processed,
                'processing_time': processing_time,
                'last_update': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Manual AI processing failed: {e}")
        return JSONResponse({
            'success': False,
            'message': f'Manual AI processing failed: {str(e)}',
            'result': {
                'processed': False,
                'changes_count': 0,
                'processing_time': 0,
                'error': str(e)
            }
        }, status_code=500)


@monitoring_bp.post('/comprehensive-summary/generate')
async def generate_comprehensive_summary(request: Request):
    """Generate a comprehensive summary with async worker pattern"""
    try:
        import threading
        from routes.monitoring_comp_helper import run_comprehensive_worker
        
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
        from routes.monitoring_comp_helper import get_comprehensive_status as get_status_data
        return get_status_data()
    except Exception as e:
        logger.error(f"Failed to get comprehensive status: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@monitoring_bp.get('/comprehensive-summary/{summary_id}')
async def get_comprehensive_summary(summary_id: int):
    """Get details of a specific comprehensive summary"""
    try:
        from database.models import ComprehensiveSummaryModel, db

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
