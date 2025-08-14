"""
File Management API routes
Handles file events, diffs, history, and file tree operations
"""

from flask import Blueprint, jsonify, request
import logging
import os
from pathlib import Path
from database.queries import FileQueries, EventQueries

logger = logging.getLogger(__name__)

files_bp = Blueprint('files', __name__, url_prefix='/api/files')


@files_bp.route('/events', methods=['GET'])
def get_recent_events():
    """Get recent file events from database"""
    try:
        events = EventQueries.get_recent_events()
        return jsonify({'events': events})
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        return jsonify({'error': str(e)}), 500


@files_bp.route('/diffs', methods=['GET'])
def get_recent_diffs():
    """Get recent content diffs from database with pagination support"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        file_path = request.args.get('file_path', None)
        
        # Initialize watch handler to filter by watch patterns
        watch_handler = None
        try:
            from utils.watch_handler import WatchHandler
            from pathlib import Path
            # Use the root directory which contains the user's .obbywatch file
            root_folder = Path(__file__).parent.parent
            watch_handler = WatchHandler(root_folder)
            logger.debug(f"Loaded watch patterns: {watch_handler.watch_patterns}")
        except Exception as e:
            logger.warning(f"Could not load watch patterns, showing all diffs: {e}")
        
        # Get recent content diffs from content_diffs table with filtering
        diffs = FileQueries.get_recent_diffs(limit=limit, offset=offset, file_path=file_path, watch_handler=watch_handler)
        
        # Get total count for pagination metadata
        total_count = FileQueries.get_diffs_count(file_path=file_path, watch_handler=watch_handler)
        
        # Calculate pagination metadata
        has_more = offset + len(diffs) < total_count
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        response = {
            'diffs': diffs,
            'pagination': {
                'total': total_count,
                'count': len(diffs),
                'offset': offset,
                'limit': limit,
                'hasMore': has_more,
                'currentPage': current_page,
                'totalPages': total_pages
            }
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Failed to get recent diffs: {e}")
        return jsonify({'error': str(e)}), 500


@files_bp.route('/diffs/<diff_id>', methods=['GET'])
def get_full_diff_content(diff_id):
    """Get full diff content by ID"""
    try:
        logger.info(f"FULL DIFF CONTENT API CALLED - ID: {diff_id}")
        
        # Get content diff by ID from content_diffs table
        diff_data = FileQueries.get_diff_content(diff_id)
        
        if diff_data is None:
            logger.warning(f"Diff not found: {diff_id}")
            return jsonify({'error': 'Diff not found'}), 404
        
        logger.info(f"Retrieved full diff content for ID: {diff_id}")
        return jsonify(diff_data)
        
    except Exception as e:
        logger.error(f"Error retrieving full diff content: {e}")
        return jsonify({'error': 'Failed to retrieve diff content'}), 500


@files_bp.route('/changes', methods=['GET'])
def get_recent_file_changes():
    """Get recent file changes with pagination support"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        change_type = request.args.get('type', None)
        
        from database.models import FileChangeModel
        raw_changes = FileChangeModel.get_recent(limit=limit, offset=offset, change_type=change_type)
        
        # Transform snake_case to camelCase for frontend
        file_changes = []
        for change in raw_changes:
            transformed_change = {
                'id': str(change['id']),
                'filePath': change['file_path'],
                'changeType': change['change_type'],
                'oldContentHash': change.get('old_content_hash'),
                'newContentHash': change.get('new_content_hash'),
                'timestamp': change['timestamp']
            }
            file_changes.append(transformed_change)
        
        # Get total count for pagination metadata
        total_count = FileChangeModel.get_count(change_type=change_type)
        
        # Calculate pagination metadata
        has_more = offset + len(file_changes) < total_count
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        response = {
            'changes': file_changes,
            'pagination': {
                'total': total_count,
                'count': len(file_changes),
                'offset': offset,
                'limit': limit,
                'hasMore': has_more,
                'currentPage': current_page,
                'totalPages': total_pages
            }
        }
        
        logger.info(f"Retrieved {len(file_changes)} recent file changes")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error retrieving file changes: {e}")
        return jsonify({'error': 'Failed to retrieve file changes'}), 500


@files_bp.route('/recent-changes', methods=['GET'])
def get_recent_file_changes_alt():
    """Alternative endpoint for recent file changes"""
    return get_recent_file_changes()


@files_bp.route('/monitoring-status', methods=['GET'])
def get_file_monitoring_status():
    """Get current file monitoring status"""
    try:
        from database.models import PerformanceModel, FileVersionModel, FileChangeModel
        
        # Get monitoring statistics
        stats = PerformanceModel.get_stats()
        
        # Add file-specific stats
        recent_versions = FileVersionModel.get_recent(limit=10)
        recent_changes = FileChangeModel.get_recent(limit=10)
        
        # Access global monitoring state (this will be False if not initialized)
        try:
            from routes.monitoring import monitoring_active
        except ImportError:
            monitoring_active = False
        
        status = {
            'monitoring_active': monitoring_active,
            'database_stats': stats,
            'recent_activity': {
                'versions': len(recent_versions),
                'changes': len(recent_changes)
            },
            'last_activity': recent_changes[0]['timestamp'] if recent_changes else None
        }
        
        logger.info("Retrieved file monitoring status")
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error retrieving monitoring status: {e}")
        return jsonify({'error': 'Failed to retrieve monitoring status'}), 500


@files_bp.route('/status', methods=['GET'])
def get_file_monitoring_status_alt():
    """Alternative endpoint for file monitoring status"""
    return get_file_monitoring_status()


@files_bp.route('/scan', methods=['POST'])
def scan_files():
    """Manually scan files for changes"""
    try:
        from core.file_tracker import file_tracker
        from config.settings import NOTES_FOLDER
        
        # Get scan parameters
        directory = request.json.get('directory', str(NOTES_FOLDER)) if request.json else str(NOTES_FOLDER)
        recursive = request.json.get('recursive', True) if request.json else True
        
        # Perform file scan
        files_processed = file_tracker.scan_directory(directory, recursive=recursive)
        
        logger.info(f"Manual file scan completed: {files_processed} files processed")
        return jsonify({
            'message': 'File scan completed successfully',
            'filesProcessed': files_processed,
            'directory': directory,
            'recursive': recursive
        })
        
    except Exception as e:
        logger.error(f"Error during manual file scan: {e}")
        return jsonify({'error': f'Failed to scan files: {str(e)}'}), 500


@files_bp.route('/clear', methods=['POST'])
def clear_file_data():
    """Clear all file tracking data"""
    try:
        # Clear all file data
        clear_result = FileQueries.clear_all_file_data()
        
        if clear_result['success']:
            logger.info(f"File data cleared successfully")
            return jsonify({
                'message': 'File data cleared successfully',
                'clearedRecords': {
                    'contentDiffs': clear_result.get('content_diffs_cleared', 0),
                    'fileVersions': clear_result.get('file_versions_cleared', 0),
                    'fileChanges': clear_result.get('file_changes_cleared', 0),
                    'fileStates': clear_result.get('file_states_cleared', 0)
                }
            })
        else:
            return jsonify({
                'error': 'Failed to clear file data',
                'details': clear_result.get('error', 'Unknown error')
            }), 500
        
    except Exception as e:
        logger.error(f"Error clearing file data: {e}")
        return jsonify({'error': f'Failed to clear file data: {str(e)}'}), 500


@files_bp.route('/clear-unwatched', methods=['POST'])
def clear_unwatched_file_diffs():
    """Clear file diffs for files no longer being watched"""
    try:
        # Initialize watch handler
        from utils.watch_handler import WatchHandler
        from pathlib import Path
        root_folder = Path(__file__).parent.parent
        watch_handler = WatchHandler(root_folder)
        
        # Clear unwatched diffs
        clear_result = FileQueries.clear_unwatched_file_diffs(watch_handler)
        
        if clear_result['success']:
            logger.info(f"Cleared unwatched file diffs successfully")
            return jsonify({
                'message': 'Unwatched file diffs cleared successfully',
                'clearedRecords': {
                    'contentDiffs': clear_result.get('content_diffs_cleared', 0),
                    'unwatchedFilesRemoved': clear_result.get('unwatched_files_removed', 0)
                }
            })
        else:
            return jsonify({
                'error': 'Failed to clear unwatched file diffs',
                'details': clear_result.get('error', 'Unknown error')
            }), 500
        
    except Exception as e:
        logger.error(f"Error clearing unwatched file diffs: {e}")
        return jsonify({'error': f'Failed to clear unwatched file diffs: {str(e)}'}), 500


@files_bp.route('/<path:file_path>/history', methods=['GET'])
def get_file_history(file_path):
    """Get version history for a specific file"""
    try:
        history = FileQueries.get_file_history(file_path)
        return jsonify({'history': history})
    except Exception as e:
        logger.error(f"Failed to get file history for {file_path}: {e}")
        return jsonify({'error': str(e)}), 500


@files_bp.route('/<path:file_path>/diff', methods=['GET'])
def get_file_diff(file_path):
    """Get diff between file versions"""
    try:
        version1 = request.args.get('version1')
        version2 = request.args.get('version2')
        
        if not version1 or not version2:
            return jsonify({'error': 'Both version1 and version2 parameters are required'}), 400
        
        diff = FileQueries.get_file_diff(file_path, version1, version2)
        return jsonify({'diff': diff})
    except Exception as e:
        logger.error(f"Failed to get file diff for {file_path}: {e}")
        return jsonify({'error': str(e)}), 500


@files_bp.route('/<path:file_path>/state', methods=['GET'])
def get_file_state(file_path):
    """Get current state of a file"""
    try:
        state = FileQueries.get_file_state(file_path)
        return jsonify({'state': state})
    except Exception as e:
        logger.error(f"Failed to get file state for {file_path}: {e}")
        return jsonify({'error': str(e)}), 500


@files_bp.route('/tree', methods=['GET'])
def get_file_tree():
    """Get file tree structure"""
    try:
        from config.settings import NOTES_FOLDER
        root_path = Path(NOTES_FOLDER)
        tree = build_file_tree(root_path)
        return jsonify({'tree': tree})
    except Exception as e:
        logger.error(f"Failed to build file tree: {e}")
        return jsonify({'error': str(e)}), 500


@files_bp.route('/watched', methods=['GET'])
def get_watched_files():
    """Get detailed information about watched files"""
    try:
        from config.settings import NOTES_FOLDER
        
        watched_files = []
        if os.path.exists(NOTES_FOLDER):
            root_path = Path(NOTES_FOLDER)
            
            for file_path in root_path.rglob('*.md'):
                if file_path.is_file():
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    
                    try:
                        stat = file_path.stat()
                        relative_path = file_path.relative_to(root_path)
                        
                        file_info = {
                            'path': str(file_path),
                            'relative_path': str(relative_path),
                            'name': file_path.name,
                            'size': stat.st_size,
                            'modified': stat.st_mtime,
                            'is_watching': True  # All found files are being watched
                        }
                        
                        # Get recent events for this file
                        recent_events = EventQueries.get_events_for_file(str(file_path), limit=1)
                        if recent_events:
                            file_info['last_event'] = recent_events[0]
                        
                        watched_files.append(file_info)
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Could not access file {file_path}: {e}")
                        continue
        
        # Sort by modification time (most recent first)
        watched_files.sort(key=lambda x: x.get('modified', 0), reverse=True)
        
        return jsonify({
            'watched_files': watched_files,
            'total_count': len(watched_files),
            'base_path': str(NOTES_FOLDER) if os.path.exists(NOTES_FOLDER) else None
        })
    except Exception as e:
        logger.error(f"Failed to get watched files: {e}")
        return jsonify({'error': str(e)}), 500


def build_file_tree(path: Path, max_depth: int = 3, current_depth: int = 0):
    """Build a file tree structure focusing on relevant directories and markdown files"""
    if current_depth > max_depth:
        return None
    
    if not path.exists():
        return None
    
    node = {
        'name': path.name,
        'path': str(path),
        'type': 'directory' if path.is_dir() else 'file',
    }
    
    if path.is_file():
        try:
            stat = path.stat()
            node.update({
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'extension': path.suffix
            })
        except (OSError, PermissionError):
            pass
        return node
    
    # For directories, add children
    children = []
    try:
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            # Skip hidden files and directories
            if child.name.startswith('.'):
                continue
            
            # For files, only include markdown files
            if child.is_file() and not child.name.endswith('.md'):
                continue
            
            child_node = build_file_tree(child, max_depth, current_depth + 1)
            if child_node:
                children.append(child_node)
    except (OSError, PermissionError):
        pass
    
    if children:
        node['children'] = children
    
    return node
