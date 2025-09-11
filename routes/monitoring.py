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
    """Generate a comprehensive summary of all changes since the last comprehensive summary"""
    try:
        from database.models import ComprehensiveSummaryModel
        from database.queries import FileQueries
        from ai.openai_client import OpenAIClient
        import time
        from datetime import datetime
        
        start_time = time.time()
        
        # Get request data
        data = await request.json() if request.headers.get('content-type','').startswith('application/json') else {}
        force = data.get('force', False)
        
        logger.info("Comprehensive summary generation triggered")
        
        # Get last comprehensive summary timestamp
        last_summary_timestamp = ComprehensiveSummaryModel.get_last_summary_timestamp()
        
        if not last_summary_timestamp:
            # If no previous comprehensive summary, use a week ago as fallback
            from datetime import timedelta
            last_summary_timestamp = datetime.now() - timedelta(days=7)
            logger.info("No previous comprehensive summary found, using 7 days ago as start time")
        
        # Get ALL changes since last comprehensive summary (no limit!)
        changes_query = """
            SELECT cd.*, fv_new.content, fv_new.file_path, fv_new.content_hash
            FROM content_diffs cd
            LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
            WHERE cd.timestamp > ?
            ORDER BY cd.timestamp ASC
        """
        
        from database.models import db
        changes = db.execute_query(changes_query, (last_summary_timestamp,))
        
        if not changes and not force:
            return {
                'success': True,
                'message': 'No changes found since last comprehensive summary',
                'result': {
                    'processed': False,
                    'changes_count': 0,
                    'time_range_start': last_summary_timestamp.isoformat(),
                    'time_range_end': datetime.now().isoformat(),
                    'reason': 'No changes to summarize'
                }
            }
        
        # Group changes by file for better processing
        changes_by_file = {}
        for change in changes:
            change_dict = dict(change)
            file_path = change_dict['file_path']
            # Exclude internal semantic index artifact to prevent polluting summaries
            try:
                if str(file_path).lower().endswith('semantic_index.json'):
                    continue
            except Exception:
                pass
            if file_path not in changes_by_file:
                changes_by_file[file_path] = []
            changes_by_file[file_path].append(change_dict)
        
        # Get or create singleton AI client and ensure it's warmed up
        logger.info("Initializing OpenAI client with warm-up...")
        ai_client = OpenAIClient.get_instance()
        
        # Perform warm-up to avoid cold start issues
        warm_up_success = ai_client.warm_up()
        if warm_up_success:
            logger.info("OpenAI client warmed up successfully")
        else:
            logger.warning("OpenAI client warm-up failed, but continuing anyway")
        
        # Prepare batch data for comprehensive processing
        batch_data = {
            'files_count': len(changes_by_file),
            'total_changes': len(changes),
            'time_span': _calculate_time_span(last_summary_timestamp, datetime.now()),
            'combined_diff': _prepare_combined_diff(changes_by_file),
            'file_summaries': _prepare_file_summaries(changes_by_file)
        }
        
        # Generate comprehensive summary using the batch method
        ai_summary = ai_client.summarize_batch_changes(batch_data)
        
        if not ai_summary or "Error" in ai_summary:
            return JSONResponse({
                'success': False,
                'message': 'Failed to generate comprehensive summary',
                'result': {
                    'processed': False,
                    'changes_count': len(changes),
                    'error': ai_summary or 'Unknown AI error'
                }
            }, status_code=500)
        
        # Parse the AI summary to extract structured data
        summary_data = _parse_ai_summary(ai_summary)
        
        # Create comprehensive summary record
        current_time = datetime.now()
        summary_id = ComprehensiveSummaryModel.create_summary(
            time_range_start=last_summary_timestamp,
            time_range_end=current_time,
            summary_content=summary_data.get('summary', ai_summary),
            key_topics=summary_data.get('topics', []),
            key_keywords=summary_data.get('keywords', []),
            overall_impact=summary_data.get('impact', 'moderate'),
            files_affected_count=len(changes_by_file),
            changes_count=len(changes),
            time_span=batch_data['time_span']
        )
        
        processing_time = time.time() - start_time
        
        if summary_id:
            logger.info(f"Comprehensive summary created with ID {summary_id}")
            return {
                'success': True,
                'message': f'Comprehensive summary generated successfully for {len(changes)} changes across {len(changes_by_file)} files',
                'result': {
                    'processed': True,
                    'summary_id': summary_id,
                    'changes_count': len(changes),
                    'files_count': len(changes_by_file),
                    'time_range_start': last_summary_timestamp.isoformat(),
                    'time_range_end': current_time.isoformat(),
                    'processing_time': processing_time,
                    'time_span': batch_data['time_span'],
                    'summary_preview': summary_data.get('summary', ai_summary)[:200] + '...'
                }
            }
        else:
            return JSONResponse({
                'success': False,
                'message': 'Failed to save comprehensive summary',
                'result': {
                    'processed': False,
                    'changes_count': len(changes),
                    'error': 'Database save failed'
                }
            }, status_code=500)
        
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


def _calculate_time_span(start_time: datetime, end_time: datetime) -> str:
    """Calculate human-readable time span between two timestamps."""
    span = end_time - start_time
    
    if span.days > 0:
        return f"{span.days} day{'s' if span.days != 1 else ''}"
    elif span.seconds >= 3600:
        hours = span.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif span.seconds >= 60:
        minutes = span.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{span.seconds} second{'s' if span.seconds != 1 else ''}"


def _prepare_combined_diff(changes_by_file: dict) -> str:
    """Prepare a combined diff string for all file changes."""
    diff_parts = []
    
    for file_path, file_changes in changes_by_file.items():
        diff_parts.append(f"\n=== Changes in {file_path} ===")
        
        for change in file_changes:
            if change.get('diff_content'):
                timestamp = change.get('timestamp', 'unknown')
                diff_parts.append(f"--- Change at {timestamp} ---")
                diff_parts.append(change['diff_content'])
        
        diff_parts.append("")  # Add spacing between files
    
    combined = "\n".join(diff_parts)
    
    # Truncate if too long to avoid API limits
    if len(combined) > 8000:
        return combined[:8000] + "\n... (truncated for API limits)"
    
    return combined


def _prepare_file_summaries(changes_by_file: dict) -> list:
    """Prepare individual file summary data."""
    file_summaries = []
    
    for file_path, file_changes in changes_by_file.items():
        changes_count = len(file_changes)
        lines_added = sum(c.get('lines_added', 0) for c in file_changes)
        lines_removed = sum(c.get('lines_removed', 0) for c in file_changes)
        
        summary = f"{changes_count} change{'s' if changes_count != 1 else ''}"
        if lines_added > 0 or lines_removed > 0:
            summary += f" (+{lines_added}/-{lines_removed} lines)"
        
        file_summaries.append({
            'file_path': file_path,
            'summary': summary,
            'changes_count': changes_count,
            'lines_added': lines_added,
            'lines_removed': lines_removed
        })
    
    return file_summaries


def _parse_ai_summary(ai_summary: str) -> dict:
    """Parse structured AI summary response into components."""
    import re
    
    parsed = {
        'summary': ai_summary,
        'topics': [],
        'keywords': [],
        'impact': 'moderate'
    }
    
    # Try to extract structured sections
    lines = ai_summary.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Extract topics
        if line.startswith('**Key Topics**:'):
            topics_text = line.replace('**Key Topics**:', '').strip()
            parsed['topics'] = [t.strip() for t in topics_text.split(',') if t.strip()]
        
        # Extract keywords  
        elif line.startswith('**Key Keywords**:'):
            keywords_text = line.replace('**Key Keywords**:', '').strip()
            parsed['keywords'] = [k.strip() for k in keywords_text.split(',') if k.strip()]
        
        # Extract impact
        elif line.startswith('**Overall Impact**:'):
            impact_text = line.replace('**Overall Impact**:', '').strip().lower()
            if impact_text in ['brief', 'moderate', 'significant']:
                parsed['impact'] = impact_text
        
        # Extract main summary
        elif line.startswith('**Batch Summary**:'):
            parsed['summary'] = line.replace('**Batch Summary**:', '').strip()
    
    return parsed


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
