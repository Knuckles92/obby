"""
Summary Notes API routes (FastAPI)
Handles individual summary note files with pagination support
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import queue
import json
from datetime import datetime
from services.summary_note_service import SummaryNoteService

logger = logging.getLogger(__name__)

summary_note_bp = APIRouter(prefix='/api/summary-notes', tags=['summary-notes'])

# SSE client management for summary notes
summary_sse_clients = []
summary_note_service = SummaryNoteService()


@summary_note_bp.get('/')
async def get_summary_notes(request: Request):
    """Get paginated list of summary notes"""
    try:
        # Get pagination and search parameters from query string
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        search_query = (request.query_params.get('search', '') or '').strip()
        
        # Validate parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:  # Limit page size to reasonable range
            page_size = 10
        
        # Convert empty string to None for consistency
        if not search_query:
            search_query = None
        
        data = summary_note_service.get_summary_list(page=page, page_size=page_size, search_query=search_query)
        return data
        
    except Exception as e:
        logger.error(f"Failed to get summary notes: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@summary_note_bp.get('/events')
async def summary_note_events():
    """SSE endpoint for summary note updates"""
    logger.info("SummaryNotes SSE: /api/summary-notes/events handler invoked")
    def event_stream():
        client_queue = queue.Queue()
        summary_sse_clients.append(client_queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to summary note updates'})}\n\n"
            
            while True:
                try:
                    # Wait for events with timeout
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                except Exception as e:
                    logger.error(f"Summary SSE stream error: {e}")
                    break
        finally:
            # Remove client from list when disconnected
            if client_queue in summary_sse_clients:
                summary_sse_clients.remove(client_queue)
    
    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })


@summary_note_bp.get('/{filename}')
async def get_summary_note(filename: str):
    """Get content of a specific summary note"""
    try:
        logger.debug(f"SummaryNotes get_summary_note called with filename={filename}")
        # Validate filename to prevent path traversal
        if not filename.endswith('.md') or '/' in filename or '\\' in filename or '..' in filename:
            logger.warning(f"SummaryNotes invalid filename received: {filename}")
            return JSONResponse({'error': 'Invalid filename', 'filename': filename}, status_code=400)
        
        data = summary_note_service.get_summary_content(filename)
        return data
        
    except FileNotFoundError:
        return JSONResponse({'error': 'Summary note not found'}, status_code=404)
    except Exception as e:
        logger.error(f"Failed to get summary note {filename}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@summary_note_bp.delete('/{filename}')
async def delete_summary_note(filename: str):
    """Delete a specific summary note"""
    try:
        # Validate filename to prevent path traversal
        if not filename.endswith('.md') or '/' in filename or '\\' in filename or '..' in filename:
            return JSONResponse({'error': 'Invalid filename'}, status_code=400)
        
        result = summary_note_service.delete_summary(filename)
        
        # Notify SSE clients about the deletion
        notify_summary_note_change('deleted', filename)
        
        return result
        
    except FileNotFoundError:
        return JSONResponse({'error': 'Summary note not found'}, status_code=404)
    except Exception as e:
        logger.error(f"Failed to delete summary note {filename}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@summary_note_bp.post('/bulk/delete')
async def delete_multiple_summary_notes(request: Request):
    """Delete multiple summary notes in bulk"""
    try:
        data = await request.json()
        if not data or 'filenames' not in data:
            return JSONResponse({'error': 'filenames array is required'}, status_code=400)
        
        filenames = data['filenames']
        if not isinstance(filenames, list):
            return JSONResponse({'error': 'filenames must be an array'}, status_code=400)
        
        if len(filenames) == 0:
            return JSONResponse({'error': 'At least one filename must be provided'}, status_code=400)
        
        if len(filenames) > 50:  # Reasonable limit to prevent abuse
            return JSONResponse({'error': 'Cannot delete more than 50 files at once'}, status_code=400)
        
        # Perform bulk deletion
        result = summary_note_service.delete_multiple_summaries(filenames)
        
        # Notify SSE clients about the bulk deletion
        for filename in filenames:
            # Only notify for successfully deleted files
            deleted_files = [r['filename'] for r in result.get('results', []) if r.get('success', False)]
            if filename in deleted_files:
                notify_summary_note_change('deleted', filename)
        
        # Also send a bulk notification
        notify_summary_note_change('bulk_deleted', None)
        
        # Return appropriate status code based on results
        if result['success']:
            return result
        elif result['summary']['succeeded'] > 0:
            # Partial success (use 207 semantics via explicit response)
            return JSONResponse(result, status_code=207)
        else:
            return JSONResponse(result, status_code=400)
        
    except Exception as e:
        logger.error(f"Failed to delete multiple summary notes: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@summary_note_bp.post('/')
async def create_summary_note(request: Request):
    """Create a new summary note"""
    try:
        data = await request.json()
        if not data or 'content' not in data:
            return JSONResponse({'error': 'Content is required'}, status_code=400)
        
        content = data['content']
        timestamp_str = data.get('timestamp')
        
        # Parse timestamp if provided
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse({'error': 'Invalid timestamp format'}, status_code=400)
        
        result = summary_note_service.create_summary(content, timestamp)
        
        # Notify SSE clients about the new summary
        notify_summary_note_change('created', result['filename'])
        
        return JSONResponse(result, status_code=201)
        
    except Exception as e:
        logger.error(f"Failed to create summary note: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@summary_note_bp.get('/stats')
async def get_summary_stats():
    """Get statistics about summary notes"""
    try:
        data = summary_note_service.get_stats()
        return data
        
    except Exception as e:
        logger.error(f"Failed to get summary stats: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


def notify_summary_note_change(action: str, filename: str = None):
    """Notify all SSE clients of summary note changes
    
    Args:
        action: Type of change ('created', 'deleted', 'updated')
        filename: Name of the affected file
    """
    try:
        # Create notification event
        event = {
            'type': 'summary_note_changed',
            'action': action,
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to all connected SSE clients
        disconnected_clients = []
        for client_queue in summary_sse_clients:
            try:
                client_queue.put_nowait(event)
            except queue.Full:
                # Mark client for removal if queue is full
                disconnected_clients.append(client_queue)
            except Exception as e:
                logger.warning(f"Failed to notify summary SSE client: {e}")
                disconnected_clients.append(client_queue)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            if client in summary_sse_clients:
                summary_sse_clients.remove(client)
        
        logger.info(f"Notified {len(summary_sse_clients)} SSE clients of summary note {action}: {filename}")
        
    except Exception as e:
        logger.error(f"Failed to notify summary SSE clients: {e}")
