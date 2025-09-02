"""
File Management API routes
Handles file events, diffs, history, and file tree operations
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import os
from pathlib import Path
from database.queries import FileQueries, EventQueries

logger = logging.getLogger(__name__)

files_bp = APIRouter(prefix='/api/files', tags=['files'])


@files_bp.get('/events')
async def get_recent_events(request: Request):
    """Get recent file events from database"""
    try:
        limit = int(request.query_params.get('limit', 50))
        events = EventQueries.get_recent_events(limit=limit)
        return {'events': events}
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/diffs')
async def get_recent_diffs(request: Request):
    """Get recent content diffs from database with pagination support"""
    try:
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        file_path = request.query_params.get('file_path', None)
        
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
        
        return response
    except Exception as e:
        logger.error(f"Failed to get recent diffs: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/diffs/{diff_id}')
async def get_full_diff_content(diff_id: str):
    """Get full diff content by ID"""
    try:
        logger.info(f"FULL DIFF CONTENT API CALLED - ID: {diff_id}")
        
        # Get content diff by ID from content_diffs table
        diff_data = FileQueries.get_diff_content(diff_id)
        
        if diff_data is None:
            logger.warning(f"Diff not found: {diff_id}")
            return JSONResponse({'error': 'Diff not found'}, status_code=404)
        
        logger.info(f"Retrieved full diff content for ID: {diff_id}")
        return diff_data
        
    except Exception as e:
        logger.error(f"Error retrieving full diff content: {e}")
        return JSONResponse({'error': 'Failed to retrieve diff content'}, status_code=500)


@files_bp.get('/changes')
async def get_recent_file_changes(request: Request):
    """Get recent file changes with pagination support"""
    try:
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        change_type = request.query_params.get('type', None)
        
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
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving file changes: {e}")
        return JSONResponse({'error': 'Failed to retrieve file changes'}, status_code=500)


@files_bp.get('/recent-changes')
async def get_recent_file_changes_alt(request: Request):
    """Alternative endpoint for recent file changes"""
    return await get_recent_file_changes(request)


@files_bp.get('/monitoring-status')
async def get_file_monitoring_status():
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
        return status
        
    except Exception as e:
        logger.error(f"Error retrieving monitoring status: {e}")
        return JSONResponse({'error': 'Failed to retrieve monitoring status'}, status_code=500)


@files_bp.get('/status')
async def get_file_monitoring_status_alt():
    """Alternative endpoint for file monitoring status"""
    return await get_file_monitoring_status()


@files_bp.post('/scan')
async def scan_files(request: Request):
    """Manually scan files for changes"""
    try:
        from core.file_tracker import file_tracker
        from config.settings import get_configured_notes_folder
        
        # Get scan parameters
        notes_folder = get_configured_notes_folder()
        data = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        directory = data.get('directory', str(notes_folder))
        recursive = data.get('recursive', True)
        
        # Perform file scan
        files_processed = file_tracker.scan_directory(directory, recursive=recursive)
        
        logger.info(f"Manual file scan completed: {files_processed} files processed")
        return {
            'message': 'File scan completed successfully',
            'filesProcessed': files_processed,
            'directory': directory,
            'recursive': recursive
        }
        
    except Exception as e:
        logger.error(f"Error during manual file scan: {e}")
        return JSONResponse({'error': f'Failed to scan files: {str(e)}'}, status_code=500)


@files_bp.post('/clear')
async def clear_file_data():
    """Clear all file tracking data"""
    try:
        # Clear all file data
        clear_result = FileQueries.clear_all_file_data()
        
        if clear_result['success']:
            logger.info(f"File data cleared successfully")
            return {
                'message': 'File data cleared successfully',
                'clearedRecords': {
                    'contentDiffs': clear_result.get('content_diffs_cleared', 0),
                    'fileVersions': clear_result.get('file_versions_cleared', 0),
                    'fileChanges': clear_result.get('file_changes_cleared', 0),
                    'fileStates': clear_result.get('file_states_cleared', 0)
                }
            }
        else:
            return JSONResponse({'error': 'Failed to clear file data', 'details': clear_result.get('error', 'Unknown error')}, status_code=500)
        
    except Exception as e:
        logger.error(f"Error clearing file data: {e}")
        return JSONResponse({'error': f'Failed to clear file data: {str(e)}'}, status_code=500)


@files_bp.post('/clear-unwatched')
async def clear_unwatched_file_diffs():
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
            return {
                'message': 'Unwatched file diffs cleared successfully',
                'clearedRecords': {
                    'contentDiffs': clear_result.get('content_diffs_cleared', 0),
                    'unwatchedFilesRemoved': clear_result.get('unwatched_files_removed', 0)
                }
            }
        else:
            return JSONResponse({'error': 'Failed to clear unwatched file diffs', 'details': clear_result.get('error', 'Unknown error')}, status_code=500)
        
    except Exception as e:
        logger.error(f"Error clearing unwatched file diffs: {e}")
        return JSONResponse({'error': f'Failed to clear unwatched file diffs: {str(e)}'}, status_code=500)


@files_bp.get('/{file_path:path}/history')
async def get_file_history(file_path: str):
    """Get version history for a specific file"""
    try:
        history = FileQueries.get_file_history(file_path)
        return {'history': history}
    except Exception as e:
        logger.error(f"Failed to get file history for {file_path}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/{file_path:path}/diff')
async def get_file_diff(file_path: str, request: Request):
    """Get diff between file versions"""
    try:
        version1 = request.query_params.get('version1')
        version2 = request.query_params.get('version2')
        
        if not version1 or not version2:
            return JSONResponse({'error': 'Both version1 and version2 parameters are required'}, status_code=400)
        
        diff = FileQueries.get_file_diff(file_path, version1, version2)
        return {'diff': diff}
    except Exception as e:
        logger.error(f"Failed to get file diff for {file_path}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/{file_path:path}/state')
async def get_file_state(file_path: str):
    """Get current state of a file"""
    try:
        state = FileQueries.get_file_state(file_path)
        return {'state': state}
    except Exception as e:
        logger.error(f"Failed to get file state for {file_path}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/tree')
async def get_file_tree():
    """Get file tree structure"""
    try:
        from config.settings import get_configured_notes_folder
        root_path = get_configured_notes_folder()
        tree = build_file_tree(root_path)
        return {'tree': tree}
    except Exception as e:
        logger.error(f"Failed to build file tree: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/watched')
async def get_watched_files():
    """Get detailed information about watched files"""
    try:
        from config.settings import get_configured_notes_folder
        from routes.monitoring import monitoring_active
        
        watched_files = []
        directories = {}
        
        notes_folder = get_configured_notes_folder()
        if os.path.exists(notes_folder):
            root_path = Path(notes_folder)
            
            for file_path in root_path.rglob('*.md'):
                if file_path.is_file():
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    
                    try:
                        stat = file_path.stat()
                        relative_path = file_path.relative_to(root_path)
                        
                        file_info = {
                            'path': str(relative_path),
                            'relativePath': str(relative_path),
                            'name': file_path.name,
                            'size': stat.st_size,
                            'lastModified': int(stat.st_mtime)
                        }
                        
                        # Group files by directory
                        dir_path = relative_path.parent if relative_path.parent != Path('.') else Path('')
                        dir_key = str(dir_path) if str(dir_path) != '.' else 'root'
                        
                        if dir_key not in directories:
                            directories[dir_key] = {
                                'path': str(dir_path) if str(dir_path) != '.' else 'notes',
                                'name': dir_path.name if dir_path.name else 'notes',
                                'fileCount': 0,
                                'files': []
                            }
                        
                        directories[dir_key]['files'].append(file_info)
                        directories[dir_key]['fileCount'] += 1
                        watched_files.append(file_info)
                        
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Could not access file {file_path}: {e}")
                        continue
        
        # Convert directories dict to list and sort files within each directory
        directories_list = []
        for dir_data in directories.values():
            # Sort files by last modified (most recent first)
            dir_data['files'].sort(key=lambda x: x.get('lastModified', 0), reverse=True)
            # Limit to first 10 files for display (keep fileCount accurate)
            if len(dir_data['files']) > 10:
                dir_data['files'] = dir_data['files'][:10]
            directories_list.append(dir_data)
        
        # Sort directories by name
        directories_list.sort(key=lambda x: x['name'])
        
        return {
            'isActive': monitoring_active,
            'directories': directories_list,
            'totalFiles': len(watched_files),
            'totalDirectories': len(directories_list)
        }
    except Exception as e:
        logger.error(f"Failed to get watched files: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


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
