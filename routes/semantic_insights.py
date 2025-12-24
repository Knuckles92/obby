"""
Semantic Insights API Routes
============================

Provides endpoints for:
- Listing and filtering semantic insights
- Getting individual insight details
- Performing user actions (dismiss, pin, mark_done)
- Getting statistics
- Triggering processing
- Checking processing status
"""

import logging
import asyncio
import json
import uuid
import threading
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from services.semantic_insights_service import get_semantic_insights_service

logger = logging.getLogger(__name__)

# SSE client management for action execution progress
action_sse_clients = {}
action_sse_lock = threading.Lock()

# Import SSE client tracking from backend.py
# Note: These functions are defined in backend.py but may not be available
# when this module is imported (they're defined after route imports).
# We use fallback no-op functions - SSE tracking is optional for graceful shutdown.
def register_sse_client(client_id: str): 
    """Register SSE client (no-op fallback)."""
    pass

def unregister_sse_client(client_id: str): 
    """Unregister SSE client (no-op fallback)."""
    pass

# Try to get the real functions at runtime if available
def _get_sse_functions():
    """Try to get SSE tracking functions from backend.py at runtime."""
    try:
        import sys
        main_module = sys.modules.get('__main__')
        if main_module and hasattr(main_module, 'register_sse_client'):
            return main_module.register_sse_client, main_module.unregister_sse_client
    except Exception:
        pass
    return register_sse_client, unregister_sse_client

semantic_insights_bp = APIRouter(prefix='/api/semantic-insights', tags=['semantic-insights'])


class ActionRequest(BaseModel):
    """Request body for insight actions."""
    action: str
    data: Optional[dict] = None


@semantic_insights_bp.get('')
async def get_semantic_insights(
    type: Optional[str] = Query(None, description="Filter by insight type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum results to return"),
    offset: int = Query(0, description="Pagination offset")
):
    """
    Get semantic insights with optional filtering.

    Parameters:
    - type: Filter by insight type (e.g., 'stale_todo', 'orphan_mention')
    - status: Filter by status (e.g., 'new', 'viewed', 'dismissed', 'pinned')
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)

    Returns:
    - insights: List of insight objects
    - meta: Pagination info and counts by type/status
    """
    try:
        service = get_semantic_insights_service()
        result = service.get_insights(
            insight_type=type,
            status=status,
            limit=limit,
            offset=offset
        )

        logger.info(f"Retrieved {len(result.get('insights', []))} semantic insights")
        return {
            'success': True,
            **result
        }

    except Exception as e:
        logger.error(f"Error retrieving semantic insights: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/stats')
async def get_semantic_insights_stats():
    """
    Get statistics about semantic insights.

    Returns counts by type, status, and entity information.
    """
    try:
        service = get_semantic_insights_service()
        stats = service.get_stats()

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.error(f"Error getting semantic insights stats: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/processing-status')
async def get_processing_status():
    """
    Get current processing status.

    Returns scheduler state, last run info, and queue size.
    """
    try:
        service = get_semantic_insights_service()
        status = service.get_processing_status()

        return {
            'success': True,
            'status': status
        }

    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.post('/trigger')
async def trigger_processing():
    """
    Manually trigger semantic processing.

    Runs a processing cycle immediately, ignoring the normal schedule.
    Returns processing summary when complete.
    """
    try:
        service = get_semantic_insights_service()
        result = await service.trigger_processing()

        if 'error' in result:
            return JSONResponse(
                {'success': False, 'error': result['error']},
                status_code=500
            )

        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        logger.error(f"Error triggering processing: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/{insight_id}')
async def get_semantic_insight(insight_id: int):
    """
    Get a single semantic insight by ID.

    Automatically marks the insight as 'viewed' if it was 'new'.
    """
    try:
        service = get_semantic_insights_service()
        insight = service.get_insight_by_id(insight_id)

        if not insight:
            return JSONResponse(
                {'success': False, 'error': 'Insight not found'},
                status_code=404
            )

        return {
            'success': True,
            'insight': insight
        }

    except Exception as e:
        logger.error(f"Error getting semantic insight {insight_id}: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.post('/{insight_id}/action')
async def perform_insight_action(insight_id: int, request: ActionRequest):
    """
    Perform a user action on an insight.

    Available actions:
    - dismiss: Hide the insight
    - pin: Pin the insight to top
    - unpin: Unpin a pinned insight
    - mark_done: Mark todo as completed
    - open_note: Record that user opened the source note
    - restore: Restore a dismissed insight
    """
    try:
        service = get_semantic_insights_service()
        result = service.perform_action(
            insight_id=insight_id,
            action=request.action,
            data=request.data
        )

        if not result.get('success'):
            return JSONResponse(
                {'success': False, 'error': result.get('error', 'Unknown error')},
                status_code=400
            )

        return {
            'success': True,
            **result
        }

    except Exception as e:
        logger.error(f"Error performing action on insight {insight_id}: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/{insight_id}/suggested-actions')
async def get_suggested_actions(insight_id: int):
    """
    Get AI-generated suggested actions for a todo insight.
    
    Only available for todo-type insights (stale_todo, active_todos).
    Returns 2-4 contextual action suggestions that can be used in chat.
    """
    try:
        service = get_semantic_insights_service()
        result = await service.generate_suggested_actions(insight_id)
        
        if not result.get('success'):
            return JSONResponse(
                {'success': False, 'error': result.get('error', 'Unknown error')},
                status_code=400 if result.get('error') else 500
            )
        
        return {
            'success': True,
            'actions': result.get('actions', [])
        }
        
    except Exception as e:
        logger.error(f"Error getting suggested actions for insight {insight_id}: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


class ExecuteActionRequest(BaseModel):
    """Request body for executing an action."""
    action_text: str


def notify_action_progress(execution_id: str, event_type: str, message: str, data: dict = None):
    """Notify SSE clients about action execution progress."""
    try:
        event = {
            'type': event_type,
            'execution_id': execution_id,
            'message': message,
            'timestamp': str(datetime.now().isoformat())
        }
        if data:
            event.update(data)
        
        with action_sse_lock:
            if execution_id in action_sse_clients:
                try:
                    action_sse_clients[execution_id].put_nowait(event)
                    logger.debug(f"Sent action progress event to execution {execution_id}: {event_type}")
                except asyncio.QueueFull:
                    logger.warning(f"Action SSE queue full for execution {execution_id}")
                except Exception as e:
                    logger.warning(f"Failed to notify action SSE client {execution_id}: {e}")
                    # Remove disconnected client
                    if execution_id in action_sse_clients:
                        del action_sse_clients[execution_id]
    except Exception as e:
        logger.error(f"Failed to notify action progress: {e}")


@semantic_insights_bp.get('/execute-action/{execution_id}/progress')
async def action_progress_events(execution_id: str, request: Request):
    """SSE endpoint for action execution progress updates."""
    async def event_stream():
        client_id = f"action-{execution_id}"
        client_queue = asyncio.Queue(maxsize=100)

        # Register client for global tracking (may be no-op)
        reg_func, unreg_func = _get_sse_functions()
        reg_func(client_id)

        with action_sse_lock:
            action_sse_clients[execution_id] = client_queue

        logger.info(f"[Action Progress] New client connected: {client_id}")

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'execution_id': execution_id, 'clientId': client_id, 'message': 'Connected to action execution progress'})}\n\n"

            while True:
                # Check if client disconnected BEFORE blocking operation
                if await request.is_disconnected():
                    logger.info(f"[Action Progress] Client {client_id} disconnected (detected)")
                    break

                try:
                    # Wait for events with shorter timeout for faster shutdown
                    event = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'execution_id': execution_id})}\n\n"
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    # Client disconnected - this is normal, just log and exit
                    logger.debug(f"[Action Progress] Client {client_id} disconnected: {e}")
                    break
                except Exception as e:
                    logger.error(f"[Action Progress] SSE stream error for {client_id}: {e}")
                    break
        finally:
            # Remove client from local list
            with action_sse_lock:
                if execution_id in action_sse_clients:
                    del action_sse_clients[execution_id]
                    logger.info(f"[Action Progress] Client {client_id} cleaned up from local list")

            # Unregister from global tracking (may be no-op)
            _, unreg_func = _get_sse_functions()
            unreg_func(client_id)

    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'X-Accel-Buffering': 'no'
    })


@semantic_insights_bp.post('/{insight_id}/execute-action')
async def execute_action(insight_id: int, request: ExecuteActionRequest):
    """
    Execute a suggested action for a todo insight using Claude Agent.
    
    Streams progress via SSE endpoint at /execute-action/{execution_id}/progress
    """
    try:
        import os
        from pathlib import Path
        from config import settings as cfg
        from utils.watch_handler import WatchHandler
        
        # Check if Claude SDK is available
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
            CLAUDE_AVAILABLE = True
        except ImportError:
            CLAUDE_AVAILABLE = False
            return JSONResponse(
                {'success': False, 'error': 'Claude Agent SDK not available'},
                status_code=400
            )
        
        if not CLAUDE_AVAILABLE:
            return JSONResponse(
                {'success': False, 'error': 'Claude Agent SDK not available'},
                status_code=400
            )
        
        # Get the insight
        service = get_semantic_insights_service()
        insight = service.get_insight_by_id(insight_id)
        
        if not insight:
            return JSONResponse(
                {'success': False, 'error': 'Insight not found'},
                status_code=404
            )
        
        # Validate it's a todo type
        if insight['type'] not in ('stale_todo', 'active_todos'):
            return JSONResponse(
                {'success': False, 'error': 'Action execution only available for todo insights'},
                status_code=400
            )
        
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Start execution in background task
        asyncio.create_task(_execute_action_async(
            insight_id=insight_id,
            insight=insight,
            action_text=request.action_text,
            execution_id=execution_id
        ))
        
        return {
            'success': True,
            'execution_id': execution_id,
            'message': 'Action execution started'
        }
        
    except Exception as e:
        logger.error(f"Error starting action execution for insight {insight_id}: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


async def _execute_action_async(insight_id: int, insight: dict, action_text: str, execution_id: str):
    """Execute the action using Claude Agent and stream progress."""
    try:
        import os
        from pathlib import Path
        from config import settings as cfg
        from utils.watch_handler import WatchHandler
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        
        notify_action_progress(execution_id, 'started', f'Starting action execution: {action_text}')
        
        # Extract todo information
        evidence = insight.get('evidence', {})
        source_notes = insight.get('sourceNotes', [])
        todo_text = evidence.get('todo_text', '')
        note_path = source_notes[0].get('path', '') if source_notes else ''
        
        # Check API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            notify_action_progress(execution_id, 'error', 'ANTHROPIC_API_KEY not configured')
            return
        
        # Initialize WatchHandler
        project_root = Path.cwd()
        watch_handler = WatchHandler(project_root)
        watch_directories = []
        restricted_cwd = project_root
        
        try:
            watch_dirs = watch_handler.get_watch_directories(project_root)
            for wd in watch_dirs:
                try:
                    rel_path = wd.relative_to(project_root)
                    watch_directories.append(str(rel_path))
                except ValueError:
                    watch_directories.append(str(wd))
            
            if watch_directories:
                first_watch_dir = watch_directories[0].rstrip('/')
                potential_cwd = project_root / first_watch_dir
                if potential_cwd.exists() and potential_cwd.is_dir():
                    restricted_cwd = potential_cwd
        except Exception as e:
            logger.warning(f"Failed to initialize watch restrictions: {e}")
        
        # Build prompt
        prompt = f"""You are helping to execute an action on a todo item.

Todo: {todo_text}
Note: {note_path}
Action requested: {action_text}

Please execute this action contextually. You may need to:
- Read the note file to understand context
- Make changes to files if needed
- Break down tasks, add deadlines, move items, etc.

Execute the action now and provide a summary of what you did."""

        system_prompt = """You are a helpful assistant that executes actions on todo items.
You have access to file reading, writing, and editing tools.
Execute actions contextually and provide clear feedback about what you did."""

        claude_model = os.getenv("OBBY_CLAUDE_MODEL", cfg.CLAUDE_MODEL)
        
        options = ClaudeAgentOptions(
            cwd=str(restricted_cwd),
            allowed_tools=["Read", "Write", "Edit", "Grep", "Glob", "Bash"],
            max_turns=10,
            model=claude_model,
            system_prompt=system_prompt
        )
        
        notify_action_progress(execution_id, 'progress', 'Connecting to Claude Agent...')
        
        # Execute with Claude Agent SDK
        result_text = []
        async with ClaudeSDKClient(options=options) as client:
            notify_action_progress(execution_id, 'progress', 'Sending request to Claude...')
            await client.query(prompt)
            
            notify_action_progress(execution_id, 'progress', 'Claude is processing your request...')
            
            async for message in client.receive_response():
                message_type = message.__class__.__name__
                
                if message_type == "AssistantMessage":
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                result_text.append(block.text)
                                notify_action_progress(execution_id, 'progress', 'Agent processing...')
                            elif hasattr(block, 'name'):  # ToolUseBlock
                                tool_name = block.name
                                tool_message = f'Using tool: {tool_name}'
                                
                                # Extract file path if available
                                if hasattr(block, 'input') and isinstance(block.input, dict):
                                    file_path = block.input.get('file_path', '')
                                    if file_path:
                                        filename = file_path.split('/')[-1].split('\\')[-1]
                                        if tool_name == 'Read':
                                            tool_message = f'Reading file: {filename}'
                                        elif tool_name == 'Edit':
                                            tool_message = f'Editing file: {filename}'
                                        elif tool_name == 'Write':
                                            tool_message = f'Writing to file: {filename}'
                                
                                notify_action_progress(
                                    execution_id,
                                    'tool_call',
                                    tool_message,
                                    {'tool': tool_name}
                                )
                
                elif message_type == "ToolResultBlock":
                    notify_action_progress(
                        execution_id,
                        'tool_result',
                        'Tool execution completed',
                        {}
                    )
        
        full_response = "\n".join(result_text)
        
        notify_action_progress(
            execution_id,
            'completed',
            'Action execution completed successfully',
            {'result': full_response[:500]}  # Truncate for SSE
        )
        
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        notify_action_progress(execution_id, 'error', f'Error: {str(e)}')
