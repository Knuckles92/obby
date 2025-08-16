"""
Admin & System API routes
Handles system statistics, database optimization, and health monitoring
"""

from flask import Blueprint, jsonify, request
import logging
import os
import psutil
import shutil
from database.queries import AnalyticsQueries

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/system/stats', methods=['GET'])
def get_system_stats():
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
        
        return jsonify({
            'stats': stats,
            'timestamp': psutil.boot_time()
        })
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/database/stats', methods=['GET'])
def get_database_stats():
    """Get database-specific statistics"""
    try:
        stats = AnalyticsQueries.get_database_stats()
        
        return jsonify({
            'database_stats': stats,
            'success': True
        })
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/database/optimize', methods=['POST'])
def optimize_database():
    """Optimize the database"""
    try:
        optimization_results = AnalyticsQueries.optimize_database()
        
        logger.info("Database optimization completed")
        
        return jsonify({
            'success': True,
            'message': 'Database optimization completed',
            'results': optimization_results
        })
    except Exception as e:
        logger.error(f"Failed to optimize database: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/system/clear-logs', methods=['POST'])
def clear_system_logs():
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
        
        return jsonify({
            'success': True,
            'message': f'Cleared {logs_cleared} log files',
            'logs_cleared': logs_cleared
        })
    except Exception as e:
        logger.error(f"Failed to clear system logs: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/system/health', methods=['GET'])
def get_system_health():
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
        
        return jsonify({
            'health': health_status,
            'timestamp': psutil.boot_time()
        })
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/database/reset', methods=['POST'])
def reset_database():
    """Reset the entire database with safety confirmations"""
    try:
        # Parse request data
        data = request.get_json() or {}
        
        # Extract safety confirmation parameters
        confirmation_phrase = data.get('confirmationPhrase', '')
        slider_confirmed = data.get('sliderConfirmed', False)
        backup_enabled = data.get('enableBackup', True)
        
        # Validate that both safety measures are confirmed
        if not slider_confirmed:
            return jsonify({
                'success': False,
                'error': 'Slider confirmation required. Reset aborted.',
                'required_confirmations': {
                    'slider': False,
                    'phrase': len(confirmation_phrase.strip()) > 0
                }
            }), 400
        
        # Validate confirmation phrase (case-insensitive)
        expected_phrase = "if I ruin my database it is my fault"
        if confirmation_phrase.strip().lower() != expected_phrase:
            return jsonify({
                'success': False,
                'error': 'Invalid confirmation phrase. Reset aborted.',
                'expected_phrase': expected_phrase,
                'required_confirmations': {
                    'slider': True,
                    'phrase': False
                }
            }), 400
        
        # Both safety measures confirmed, proceed with reset
        logger.warning(f"Database reset initiated with confirmations")
        
        # Call the reset method from AnalyticsQueries
        reset_results = AnalyticsQueries.reset_database(
            confirmation_phrase=confirmation_phrase,
            backup_enabled=backup_enabled
        )
        
        if reset_results.get('success'):
            logger.info(f"Database reset completed successfully: {reset_results.get('total_records_deleted', 0)} records deleted")
            
            # Return success response with detailed results
            return jsonify({
                'success': True,
                'message': reset_results.get('message', 'Database reset completed'),
                'results': {
                    'backup_created': reset_results.get('backup_created', False),
                    'backup_path': reset_results.get('backup_path'),
                    'total_records_deleted': reset_results.get('total_records_deleted', 0),
                    'tables_reset': len(reset_results.get('tables_reset', [])),
                    'reset_timestamp': reset_results.get('reset_timestamp'),
                    'post_reset_optimization': reset_results.get('post_reset_optimization')
                },
                'recovery_info': {
                    'backup_available': reset_results.get('backup_created', False),
                    'backup_location': reset_results.get('backup_path'),
                    'recovery_instructions': 'To restore, stop the application and replace obby.db with the backup file.'
                } if reset_results.get('backup_created') else None
            })
        else:
            # Reset failed
            logger.error(f"Database reset failed: {reset_results.get('error')}")
            return jsonify({
                'success': False,
                'error': reset_results.get('error', 'Unknown error during reset'),
                'backup_path': reset_results.get('backup_path')
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during database reset: {str(e)}'
        }), 500
