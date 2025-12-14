"""
Admin & System API routes
Handles system statistics, database optimization, and health monitoring
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import os
import psutil
import shutil
from database.queries import AnalyticsQueries

logger = logging.getLogger(__name__)

admin_bp = APIRouter(prefix='/api/admin', tags=['admin'])


@admin_bp.get('/system/stats')
async def get_system_stats():
    """Get system statistics for admin panel"""
    try:
        # System memory info
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Process info
        process = psutil.Process()
        process_memory = process.memory_info()
        
        stats = {
            'system': {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_percent': memory.percent,
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'disk_percent': (disk.used / disk.total) * 100
            },
            'process': {
                'memory_rss': process_memory.rss,
                'memory_vms': process_memory.vms,
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent(),
                'pid': process.pid,
                'num_threads': process.num_threads()
            }
        }
        
        return {'stats': stats, 'timestamp': psutil.boot_time()}
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.get('/database/stats')
async def get_database_stats():
    """Get database-specific statistics"""
    try:
        stats = AnalyticsQueries.get_database_stats()
        
        return {'database_stats': stats, 'success': True}
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.post('/database/optimize')
async def optimize_database():
    """Optimize the database"""
    try:
        optimization_results = AnalyticsQueries.optimize_database()
        
        logger.info("Database optimization completed")
        
        return {'success': True, 'message': 'Database optimization completed', 'results': optimization_results}
    except Exception as e:
        logger.error(f"Failed to optimize database: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.post('/system/clear-logs')
async def clear_system_logs():
    """Clear system logs"""
    try:
        logs_cleared = 0
        log_files = ['obby.log', 'error.log', 'debug.log']
        
        for log_file in log_files:
            if os.path.exists(log_file):
                # Backup before clearing
                backup_file = f"{log_file}.backup"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                
                shutil.copy2(log_file, backup_file)
                
                # Clear the log file
                open(log_file, 'w').close()
                logs_cleared += 1
        
        logger.info(f"Cleared {logs_cleared} log files")
        
        return {'success': True, 'message': f'Cleared {logs_cleared} log files', 'logs_cleared': logs_cleared}
    except Exception as e:
        logger.error(f"Failed to clear system logs: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.get('/system/health')
async def get_system_health():
    """Get overall system health status"""
    try:
        health_status = {
            'overall_status': 'healthy',
            'issues': [],
            'warnings': []
        }
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            health_status['issues'].append('High memory usage')
            health_status['overall_status'] = 'warning'
        elif memory.percent > 80:
            health_status['warnings'].append('Elevated memory usage')
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > 95:
            health_status['issues'].append('Very low disk space')
            health_status['overall_status'] = 'critical'
        elif disk_percent > 85:
            health_status['warnings'].append('Low disk space')
            if health_status['overall_status'] == 'healthy':
                health_status['overall_status'] = 'warning'
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 95:
            health_status['issues'].append('Very high CPU usage')
            health_status['overall_status'] = 'critical'
        elif cpu_percent > 80:
            health_status['warnings'].append('High CPU usage')
            if health_status['overall_status'] == 'healthy':
                health_status['overall_status'] = 'warning'
        
        # Check database connectivity
        try:
            db_stats = AnalyticsQueries.get_database_stats()
            if not db_stats:
                health_status['issues'].append('Database connectivity issues')
                health_status['overall_status'] = 'critical'
        except Exception:
            health_status['issues'].append('Database not accessible')
            health_status['overall_status'] = 'critical'
        
        return {'health': health_status, 'timestamp': psutil.boot_time()}
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.post('/database/reset')
async def reset_database(request: Request):
    """Reset the entire database with safety confirmations"""
    try:
        # Parse request data
        data = await request.json() if request.headers.get('content-type','').startswith('application/json') else {}
        
        # Extract safety confirmation parameters
        confirmation_phrase = data.get('confirmationPhrase', '')
        slider_confirmed = data.get('sliderConfirmed', False)
        backup_enabled = data.get('enableBackup', True)
        
        # Validate that both safety measures are confirmed
        if not slider_confirmed:
            return JSONResponse({'success': False, 'error': 'Slider confirmation required. Reset aborted.', 'required_confirmations': {'slider': False, 'phrase': len(confirmation_phrase.strip()) > 0}}, status_code=400)
        
        # Validate confirmation phrase (case-insensitive)
        expected_phrase = "if i ruin my database it is my fault"
        if confirmation_phrase.strip().lower() != expected_phrase.lower():
            return JSONResponse({'success': False, 'error': 'Invalid confirmation phrase. Reset aborted.', 'expected_phrase': expected_phrase, 'required_confirmations': {'slider': True, 'phrase': False}}, status_code=400)
        
        # Both safety measures confirmed, proceed with reset
        logger.warning(f"Database reset initiated with confirmations")
        
        # Call the reset method from AnalyticsQueries
        reset_results = AnalyticsQueries.reset_database(
            confirmation_phrase=confirmation_phrase,
            backup_enabled=backup_enabled
        )
        
        if reset_results.get('success'):
            logger.info(f"Database reset completed successfully: {reset_results.get('total_records_deleted', 0)} records deleted")

            # Extract output files cleared info
            output_files_cleared = reset_results.get('output_files_cleared', {})

            # Return success response with detailed results
            return {
                'success': True,
                'message': reset_results.get('message', 'Database reset completed'),
                'results': {
                    'backup_created': reset_results.get('backup_created', False),
                    'backup_path': reset_results.get('backup_path'),
                    'total_records_deleted': reset_results.get('total_records_deleted', 0),
                    'tables_reset': len(reset_results.get('tables_reset', [])),
                    'reset_timestamp': reset_results.get('reset_timestamp'),
                    'post_reset_optimization': reset_results.get('post_reset_optimization'),
                    'output_files_cleared': output_files_cleared.get('total', 0),
                    'output_daily_cleared': output_files_cleared.get('daily', 0),
                    'output_summaries_cleared': output_files_cleared.get('summaries', 0)
                },
                'recovery_info': {
                    'backup_available': reset_results.get('backup_created', False),
                    'backup_location': reset_results.get('backup_path'),
                    'recovery_instructions': 'To restore, stop the application and replace .db/obby.db with the backup file. Note: Output files (session summaries and comprehensive summaries) cannot be restored from backup.'
                } if reset_results.get('backup_created') else None
            }
        else:
            # Reset failed
            logger.error(f"Database reset failed: {reset_results.get('error')}")
            return JSONResponse({'success': False, 'error': reset_results.get('error', 'Unknown error during reset'), 'backup_path': reset_results.get('backup_path')}, status_code=500)
            
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return JSONResponse({'success': False, 'error': f'Server error during database reset: {str(e)}'}, status_code=500)


# ============================================================================
# AGENT LOGGING ENDPOINTS
# ============================================================================

@admin_bp.get('/agent-logs')
async def get_agent_logs(request: Request):
    """
    Get paginated agent logs with optional filtering.

    Query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50)
    - operation_type: Filter by operation type (summary, chat, insights)
    - phase: Filter by phase (data_collection, file_exploration, analysis, generation, error)
    """
    try:
        from services.agent_logging_service import get_agent_logging_service

        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        operation_type = request.query_params.get('operation_type')
        phase = request.query_params.get('phase')

        # Validate parameters
        page = max(1, page)
        page_size = min(max(1, page_size), 200)  # Cap at 200
        offset = (page - 1) * page_size

        # Get logs from service
        logging_service = get_agent_logging_service()
        logs, total_count = logging_service.get_recent_logs(
            limit=page_size,
            offset=offset,
            operation_type=operation_type,
            phase=phase
        )

        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size

        return {
            'logs': logs,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1
            },
            'filters': {
                'operation_type': operation_type,
                'phase': phase
            }
        }

    except Exception as e:
        logger.error(f"Failed to get agent logs: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.get('/agent-logs/session/{session_id}')
async def get_session_logs(session_id: str):
    """Get all logs for a specific agent session (timeline view)."""
    try:
        from services.agent_logging_service import get_agent_logging_service

        logging_service = get_agent_logging_service()
        logs = logging_service.get_session_logs(session_id)

        return {
            'session_id': session_id,
            'logs': logs,
            'total_operations': len(logs)
        }

    except Exception as e:
        logger.error(f"Failed to get session logs for {session_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.get('/agent-logs/stats')
async def get_agent_logs_stats():
    """Get aggregate statistics on agent operations."""
    try:
        from services.agent_logging_service import get_agent_logging_service
        from datetime import datetime, timedelta

        logging_service = get_agent_logging_service()

        # Get overall stats
        total_logs = logging_service.count_logs()

        # Get stats for last 24 hours
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)

        recent_stats = logging_service.get_operation_stats(start_time=yesterday, end_time=now)
        weekly_stats = logging_service.get_operation_stats(start_time=last_week, end_time=now)
        tool_stats = logging_service.get_tool_usage_stats(start_time=yesterday, end_time=now)

        return {
            'total_logs': total_logs,
            'last_24_hours': {
                'operations': recent_stats['total_operations'],
                'phase_distribution': recent_stats['phase_distribution'],
                'operation_types': recent_stats['operation_types'],
                'avg_duration_ms': recent_stats['avg_duration_ms']
            },
            'last_7_days': {
                'operations': weekly_stats['total_operations'],
                'phase_distribution': weekly_stats['phase_distribution'],
                'operation_types': weekly_stats['operation_types'],
                'avg_duration_ms': weekly_stats['avg_duration_ms']
            },
            'tool_usage': tool_stats
        }

    except Exception as e:
        logger.error(f"Failed to get agent logs stats: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.get('/agent-logs/sessions')
async def get_agent_sessions(request: Request):
    """Get list of unique agent sessions with summary information."""
    try:
        from services.agent_logging_service import get_agent_logging_service

        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))

        # Validate parameters
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        offset = (page - 1) * page_size

        # Get sessions
        logging_service = get_agent_logging_service()
        sessions, total_count = logging_service.get_unique_sessions(
            limit=page_size,
            offset=offset
        )

        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size

        return {
            'sessions': sessions,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        }

    except Exception as e:
        logger.error(f"Failed to get agent sessions: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@admin_bp.post('/agent-logs/clear')
async def clear_agent_logs(request: Request):
    """
    Manual cleanup of agent logs.

    Body params:
    - action: 'all' | 'before_date' | 'session'
    - date: ISO date string (required if action='before_date')
    - session_id: Session ID (required if action='session')
    """
    try:
        from services.agent_logging_service import get_agent_logging_service
        from datetime import datetime

        data = await request.json()
        action = data.get('action')

        if not action:
            return JSONResponse({'error': 'action parameter is required'}, status_code=400)

        logging_service = get_agent_logging_service()

        if action == 'session':
            session_id = data.get('session_id')
            if not session_id:
                return JSONResponse({'error': 'session_id is required for session cleanup'}, status_code=400)

            success = logging_service.delete_session_logs(session_id)
            if success:
                return {'success': True, 'message': f'Deleted logs for session {session_id}'}
            else:
                return JSONResponse({'error': 'Failed to delete session logs'}, status_code=500)

        elif action == 'before_date':
            date_str = data.get('date')
            if not date_str:
                return JSONResponse({'error': 'date is required for date-based cleanup'}, status_code=400)

            try:
                timestamp = datetime.fromisoformat(date_str)
            except ValueError:
                return JSONResponse({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}, status_code=400)

            deleted_count = logging_service.delete_logs_before(timestamp)
            return {
                'success': True,
                'message': f'Deleted {deleted_count} logs before {date_str}',
                'deleted_count': deleted_count
            }

        elif action == 'all':
            # Delete all logs (use far future date)
            deleted_count = logging_service.delete_logs_before(datetime(2099, 12, 31))
            return {
                'success': True,
                'message': f'Deleted all {deleted_count} agent logs',
                'deleted_count': deleted_count
            }

        else:
            return JSONResponse({'error': f'Invalid action: {action}. Must be one of: all, before_date, session'}, status_code=400)

    except Exception as e:
        logger.error(f"Failed to clear agent logs: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
