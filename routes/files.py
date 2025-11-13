"""
File Management API routes
Handles file events, diffs, history, file tree operations, and file content read/write
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import os
import json
import queue
import threading
from datetime import datetime
from pathlib import Path
from database.queries import FileQueries, EventQueries
from services.file_service import get_file_service

logger = logging.getLogger(__name__)

files_bp = APIRouter(prefix='/api/files', tags=['files'])

# SSE client management for file content updates
file_update_clients = {}
file_update_lock = threading.Lock()


def notify_file_update(file_path: str, event_type: str = 'modified', content: str = None):
    """Notify SSE clients of file content updates"""
    try:
        event = {
            'type': event_type,
            'filePath': file_path,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        if content is not None:
            event['content'] = content

        logger.info(f"[File Updates] Broadcasting update for: {file_path} to {len(file_update_clients)} clients")

        with file_update_lock:
            disconnected_clients = []
            for client_id, client_queue in file_update_clients.items():
                try:
                    client_queue.put_nowait(event)
                    logger.debug(f"[File Updates] Sent to client {client_id}: {file_path}")
                except queue.Full:
                    logger.warning(f"[File Updates] Queue full for client {client_id}")
                    disconnected_clients.append(client_id)
                except Exception as e:
                    logger.warning(f"[File Updates] Failed to notify client {client_id}: {e}")
                    disconnected_clients.append(client_id)

            # Remove disconnected clients
            for client_id in disconnected_clients:
                del file_update_clients[client_id]
                logger.info(f"[File Updates] Removed disconnected client {client_id}")

    except Exception as e:
        logger.error(f"[File Updates] Failed to notify: {e}")


@files_bp.get('/updates/stream')
async def file_updates_stream():
    """SSE endpoint for real-time file content updates"""
    def event_stream():
        client_id = f"client-{datetime.now().timestamp()}"
        client_queue = queue.Queue(maxsize=100)

        with file_update_lock:
            file_update_clients[client_id] = client_queue

        logger.info(f"[File Updates] New client connected: {client_id}")

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'clientId': client_id, 'message': 'Connected to file updates'})}\n\n"

            while True:
                try:
                    # Wait for events with timeout
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                except Exception as e:
                    logger.error(f"File update SSE stream error: {e}")
                    break
        finally:
            # Remove client from list when disconnected
            with file_update_lock:
                if client_id in file_update_clients:
                    del file_update_clients[client_id]
                    logger.info(f"File update client {client_id} disconnected")

    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })


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


@files_bp.get('/events/{event_id}/details')
async def get_event_details(event_id: str):
    """Get detailed information for a specific event including associated diff"""
    try:
        # Get the event details
        event = EventQueries.get_event_by_id(event_id)

        if not event:
            return JSONResponse({'error': 'Event not found'}, status_code=404)

        # Get diffs for the file around the event timestamp
        file_path = event.get('path')
        event_timestamp = event.get('timestamp')

        # Get all recent diffs (not filtered by file path) to find matches
        # This is needed because events store relative paths but diffs store absolute paths
        diffs = FileQueries.get_recent_diffs(limit=50)

        # Find the diff closest to the event timestamp
        associated_diff = None
        if diffs:
            # Sort diffs by how close they are to the event timestamp
            from datetime import datetime

            def parse_timestamp(ts):
                """Parse timestamp string to datetime for comparison"""
                if isinstance(ts, str):
                    # Handle ISO format with or without 'Z'
                    ts = ts.replace('Z', '+00:00')
                    return datetime.fromisoformat(ts)
                return ts

            event_dt = parse_timestamp(event_timestamp)

            # Find the diff with timestamp closest to event timestamp that matches the file path
            # Handle both absolute and relative paths (events use relative, diffs use absolute)
            closest_diff = None
            min_diff_seconds = float('inf')

            for diff in diffs:
                # Check if this diff matches the event's file path
                diff_path = diff.get('filePath', '')

                # Match if: diff path ends with event path OR event path ends with diff path
                # OR they're equal (handle both absolute and relative)
                path_matches = (
                    diff_path.endswith(file_path) or
                    file_path.endswith(diff_path) or
                    diff_path == file_path or
                    diff_path.replace('\\', '/').endswith(file_path.replace('\\', '/'))
                )

                if not path_matches:
                    continue

                diff_dt = parse_timestamp(diff.get('timestamp'))
                time_diff = abs((event_dt - diff_dt).total_seconds())

                if time_diff < min_diff_seconds:
                    min_diff_seconds = time_diff
                    closest_diff = diff

            # Only include the diff if it's within 60 seconds of the event
            if closest_diff and min_diff_seconds < 60:
                associated_diff = closest_diff

        # Format response
        response = {
            'event': {
                'id': str(event['id']),
                'type': event['type'],
                'path': event['path'],
                'timestamp': event['timestamp'],
                'size': event.get('size'),
                'processed': event.get('processed', False)
            },
            'diff': associated_diff  # Will be None if no close match found
        }

        logger.info(f"Retrieved event details for ID: {event_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to get event details for {event_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@files_bp.get('/activity')
async def get_recent_activity(request: Request):
    """Get recent file activity in simplified format for dashboard"""
    try:
        limit = int(request.query_params.get('limit', 10))

        # Initialize watch handler to filter by watch patterns
        watch_handler = None
        try:
            from utils.watch_handler import WatchHandler
            from pathlib import Path
            root_folder = Path(__file__).parent.parent
            watch_handler = WatchHandler(root_folder)
        except Exception as e:
            logger.warning(f"Could not load watch patterns, showing all activity: {e}")

        # Get recent content diffs
        diffs = FileQueries.get_recent_diffs(limit=limit, watch_handler=watch_handler)

        # Transform to activity format
        activities = []
        for diff in diffs:
            # Extract file name from path
            file_path = diff['filePath']
            file_name = file_path.split('/')[-1]

            activity = {
                'id': diff['id'],
                'type': diff['changeType'],
                'filePath': file_path,
                'fileName': file_name,
                'timestamp': diff['timestamp'],
                'linesAdded': diff.get('linesAdded', 0),
                'linesRemoved': diff.get('linesRemoved', 0),
                'hasContent': bool(diff.get('diffContent'))
            }
            activities.append(activity)

        return {'activities': activities, 'count': len(activities)}

    except Exception as e:
        logger.error(f"Failed to get recent activity: {e}")
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


@files_bp.get('/diffs/{diff_id}/details')
async def get_diff_details(diff_id: str):
    """Get detailed information for a specific diff (for EventDetailsModal)"""
    try:
        # Get the diff content
        diff_data = FileQueries.get_diff_content(diff_id)

        if diff_data is None:
            logger.warning(f"Diff not found: {diff_id}")
            return JSONResponse({'error': 'Diff not found'}, status_code=404)

        # Format response to match EventDetailsModal expectations
        # Create a synthetic event from the diff
        response = {
            'event': {
                'id': str(diff_data['id']),
                'type': diff_data['changeType'],
                'path': diff_data['filePath'],
                'timestamp': diff_data['timestamp'],
                'size': None,  # Diffs don't track file size
                'processed': True  # Diffs are by definition processed
            },
            'diff': diff_data  # The full diff is already available
        }

        logger.info(f"Retrieved diff details for ID: {diff_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to get diff details for {diff_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


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


@files_bp.post('/diffs/clear')
async def clear_diffs():
    """Clear all content diffs (for Recent Activity clear all button)"""
    try:
        # Clear only content diffs
        from database.models import db

        # Get counts before clearing
        diffs_result = db.execute_query("SELECT COUNT(*) as count FROM content_diffs")
        diffs_count = diffs_result[0]['count'] if diffs_result else 0

        # Clear diffs
        db.execute_update("DELETE FROM content_diffs")

        logger.info(f"Cleared {diffs_count} content diffs")
        return {
            'message': 'Content diffs cleared successfully',
            'clearedRecords': diffs_count
        }

    except Exception as e:
        logger.error(f"Error clearing content diffs: {e}")
        return JSONResponse({'error': f'Failed to clear content diffs: {str(e)}'}, status_code=500)


@files_bp.post('/clear-unwatched')
async def clear_unwatched_file_diffs():
    """Clear file diffs for files no longer being watched - STRICT MODE: removes all unwatched file data"""
    try:
        # Initialize watch handler
        from utils.watch_handler import WatchHandler
        from pathlib import Path
        root_folder = Path(__file__).parent.parent
        watch_handler = WatchHandler(root_folder)
        
        # AUDIT: Log unwatched files before clearing
        logger.warning("=" * 60)
        logger.warning("CLEARING UNWATCHED FILE DATA - AUDIT LOG")
        logger.warning("=" * 60)
        
        # Clear unwatched diffs
        clear_result = FileQueries.clear_unwatched_file_diffs(watch_handler)
        
        if clear_result['success']:
            logger.warning(f"✓ Cleared {clear_result.get('content_diffs_cleared', 0)} unwatched file diffs")
            logger.warning(f"✓ Removed {clear_result.get('unwatched_files_removed', 0)} unwatched file references")
            logger.warning("=" * 60)
            
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

@files_bp.post('/clear-semantic')
async def clear_semantic_data():
    """Clear semantic AI data (entries/topics/keywords/FTS/comprehensive summaries) and on-disk semantic index, output files, and AI-related config values."""
    try:
        result = FileQueries.clear_semantic_data()
        if result.get('success'):
            return {
                'message': 'Cleared semantic AI data',
                'clearedRecords': {
                    'semanticEntries': result.get('semantic_entries_cleared', 0),
                    'semanticTopics': result.get('semantic_topics_cleared', 0),
                    'semanticKeywords': result.get('semantic_keywords_cleared', 0),
                    'semanticSearch': result.get('semantic_search_cleared', 0),
                    'comprehensiveSummaries': result.get('comprehensive_summaries_cleared', 0),
                    'outputFiles': result.get('output_files_cleared', 0),
                    'configValues': result.get('config_values_cleared', 0),
                },
                'semanticIndexRemoved': result.get('semantic_index_removed', False),
                'outputFilesDetail': result.get('output_files_detail', {})
            }
        return JSONResponse({'error': 'Failed to clear semantic data', 'details': result.get('error')}, status_code=500)
    except Exception as e:
        logger.error(f"Error clearing semantic data: {e}")
        return JSONResponse({'error': f'Failed to clear semantic data: {str(e)}'}, status_code=500)


@files_bp.post('/clear-missing')
async def clear_missing_file_diffs():
    """Clear content diffs (and related change rows) for files that no longer exist on disk - STRICT MODE."""
    try:
        # AUDIT: Log before clearing
        logger.warning("=" * 60)
        logger.warning("CLEARING MISSING FILE DATA - AUDIT LOG")
        logger.warning("=" * 60)
        
        clear_result = FileQueries.clear_nonexistent_file_diffs()
        if clear_result.get('success'):
            logger.warning(f"✓ Cleared {clear_result.get('content_diffs_cleared', 0)} diffs for non-existent files")
            logger.warning(f"✓ Cleared {clear_result.get('file_changes_cleared', 0)} file changes")
            logger.warning(f"✓ Affected {clear_result.get('files_affected', 0)} files")
            logger.warning("=" * 60)
            
            return {
                'message': 'Cleared diffs for non-existent files',
                'clearedRecords': {
                    'contentDiffs': clear_result.get('content_diffs_cleared', 0),
                    'fileChanges': clear_result.get('file_changes_cleared', 0),
                    'filesAffected': clear_result.get('files_affected', 0),
                }
            }
        return JSONResponse({'error': 'Failed to clear diffs for non-existent files', 'details': clear_result.get('error')}, status_code=500)
    except Exception as e:
        logger.error(f"Error clearing diffs for non-existent files: {e}")
        return JSONResponse({'error': f'Failed to clear diffs for non-existent files: {str(e)}'}, status_code=500)


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
    """Get detailed information about watched files - STRICT MODE: only returns files matching .obbywatch patterns"""
    try:
        from config.settings import get_configured_notes_folder
        from routes.monitoring import monitoring_active
        from utils.watch_handler import WatchHandler
        from utils.ignore_handler import IgnoreHandler
        
        # STRICT: Initialize watch and ignore handlers
        root_folder = Path(__file__).parent.parent
        watch_handler = WatchHandler(root_folder)
        notes_folder = get_configured_notes_folder()
        ignore_handler = IgnoreHandler(root_folder, notes_folder)
        
        watched_files = []
        directories = {}

        if os.path.exists(notes_folder):
            root_path = Path(notes_folder).resolve()  # Convert to absolute path

            for file_path in root_path.rglob('*.md'):
                if file_path.is_file():
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in file_path.parts):
                        continue

                    # STRICT: Check if file should be ignored
                    if ignore_handler.should_ignore(file_path):
                        continue

                    # STRICT: Check if file matches watch patterns (pass resolved absolute path)
                    if not watch_handler.should_watch(file_path.resolve()):
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


@files_bp.get('/content/{file_path:path}')
async def get_file_content(file_path: str):
    """Read file content with metadata"""
    try:
        file_service = get_file_service()
        result = file_service.read_file_content(file_path)
        logger.info(f"Successfully read file: {file_path}")
        return result
    except FileNotFoundError as e:
        logger.warning(f"File not found: {file_path}")
        return JSONResponse({'error': str(e)}, status_code=404)
    except ValueError as e:
        logger.warning(f"Invalid file path: {file_path} - {e}")
        return JSONResponse({'error': str(e)}, status_code=403)
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return JSONResponse({'error': f'Failed to read file: {str(e)}'}, status_code=500)


@files_bp.put('/content/{file_path:path}')
async def write_file_content(file_path: str, request: Request):
    """Write file content with atomic operation and backup"""
    try:
        data = await request.json()
        content = data.get('content', '')
        create_backup = data.get('createBackup', True)

        file_service = get_file_service()
        result = file_service.write_file_content(file_path, content, create_backup)
        logger.info(f"Successfully wrote file: {file_path}")

        # Notify connected clients about the file update using the relativePath
        # This ensures consistency with frontend file paths
        notification_path = result.get('relativePath', file_path)
        logger.info(f"Sending file update notification for: {notification_path}")
        notify_file_update(notification_path, event_type='modified', content=content)

        return result
    except ValueError as e:
        logger.warning(f"Invalid file path: {file_path} - {e}")
        return JSONResponse({'error': str(e)}, status_code=403)
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return JSONResponse({'error': f'Failed to write file: {str(e)}'}, status_code=500)


@files_bp.post('/search')
async def search_files(request: Request):
    """Fuzzy search across watched files"""
    try:
        data = await request.json()
        query = data.get('query', '')
        max_results = data.get('maxResults', 50)

        if not query:
            return {'results': []}

        file_service = get_file_service()
        results = file_service.search_files(query, max_results)

        logger.info(f"File search for '{query}' returned {len(results)} results")
        return {'results': results, 'query': query, 'count': len(results)}
    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        return JSONResponse({'error': f'Failed to search files: {str(e)}'}, status_code=500)


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
