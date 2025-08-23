"""
Summary Notes API routes
Handles individual summary note files with pagination support
"""

from flask import Blueprint, jsonify, request
import logging
import queue
import json
from datetime import datetime
from services.summary_note_service import SummaryNoteService

logger = logging.getLogger(__name__)

summary_note_bp = Blueprint('summary_note', __name__, url_prefix='/api/summary-notes')

# SSE client management for summary notes
summary_sse_clients = []
summary_note_service = SummaryNoteService()


@summary_note_bp.route('/', methods=['GET'])
def get_summary_notes():
    """Get paginated list of summary notes"""
    try:
        # Get pagination and search parameters from query string
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        search_query = request.args.get('search', '').strip()
        
        # Validate parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:  # Limit page size to reasonable range
            page_size = 10
        
        # Convert empty string to None for consistency
        if not search_query:
            search_query = None
        
        data = summary_note_service.get_summary_list(page=page, page_size=page_size, search_query=search_query)
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Failed to get summary notes: {e}")
        return jsonify({'error': str(e)}), 500


@summary_note_bp.route('/<filename>', methods=['GET'])
def get_summary_note(filename):
    """Get content of a specific summary note"""
    try:
        # Validate filename to prevent path traversal
        if not filename.endswith('.md') or '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        data = summary_note_service.get_summary_content(filename)
        return jsonify(data)
        
    except FileNotFoundError:
        return jsonify({'error': 'Summary note not found'}), 404
    except Exception as e:
        logger.error(f"Failed to get summary note {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@summary_note_bp.route('/<filename>', methods=['DELETE'])
def delete_summary_note(filename):
    """Delete a specific summary note"""
    try:
        # Validate filename to prevent path traversal
        if not filename.endswith('.md') or '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        result = summary_note_service.delete_summary(filename)
        
        # Notify SSE clients about the deletion
        notify_summary_note_change('deleted', filename)
        
        return jsonify(result)
        
    except FileNotFoundError:
        return jsonify({'error': 'Summary note not found'}), 404
    except Exception as e:
        logger.error(f"Failed to delete summary note {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@summary_note_bp.route('/bulk', methods=['DELETE'])
def delete_multiple_summary_notes():
    """Delete multiple summary notes in bulk"""
    try:
        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({'error': 'filenames array is required'}), 400
        
        filenames = data['filenames']
        if not isinstance(filenames, list):
            return jsonify({'error': 'filenames must be an array'}), 400
        
        if len(filenames) == 0:
            return jsonify({'error': 'At least one filename must be provided'}), 400
        
        if len(filenames) > 50:  # Reasonable limit to prevent abuse
            return jsonify({'error': 'Cannot delete more than 50 files at once'}), 400
        
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
            return jsonify(result), 200
        elif result['summary']['succeeded'] > 0:
            # Partial success
            return jsonify(result), 207  # Multi-Status
        else:
            # Complete failure
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Failed to delete multiple summary notes: {e}")
        return jsonify({'error': str(e)}), 500


@summary_note_bp.route('/', methods=['POST'])
def create_summary_note():
    """Create a new summary note"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content']
        timestamp_str = data.get('timestamp')
        
        # Parse timestamp if provided
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
        
        result = summary_note_service.create_summary(content, timestamp)
        
        # Notify SSE clients about the new summary
        notify_summary_note_change('created', result['filename'])
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Failed to create summary note: {e}")
        return jsonify({'error': str(e)}), 500


@summary_note_bp.route('/stats', methods=['GET'])
def get_summary_stats():
    """Get statistics about summary notes"""
    try:
        data = summary_note_service.get_stats()
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Failed to get summary stats: {e}")
        return jsonify({'error': str(e)}), 500


@summary_note_bp.route('/events')
def summary_note_events():
    """SSE endpoint for summary note updates"""
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
    
    from flask import Response
    return Response(event_stream(), mimetype='text/event-stream', 
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*'})


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