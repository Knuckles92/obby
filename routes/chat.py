"""
Chat API routes (FastAPI)
Provides chat completion endpoints backed by the Claude Agent SDK.

IMPORTANT: File access is restricted to watch directories configured in .obbywatch.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import os
import json
import queue
import threading
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from config import settings as cfg
from utils.watch_handler import WatchHandler

# Import SSE client tracking from backend
import sys
if 'backend' in sys.modules:
    from backend import register_sse_client, unregister_sse_client
else:
    # Fallback if backend module not available (e.g., during testing)
    def register_sse_client(client_id: str): pass
    def unregister_sse_client(client_id: str): pass

logger = logging.getLogger(__name__)

# Try to import Claude Agent SDK (optional dependency)
try:
    from ai.claude_agent_client import CLAUDE_SDK_AVAILABLE
    from claude_agent_sdk import (
        ClaudeSDKClient, 
        ClaudeAgentOptions, 
        AssistantMessage, 
        TextBlock,
        CLINotFoundError,
        CLIConnectionError,
        ProcessError,
        ClaudeSDKError
    )
    CLAUDE_AVAILABLE = CLAUDE_SDK_AVAILABLE
except ImportError:
    CLAUDE_AVAILABLE = False
    # Define placeholder exception classes if SDK not available
    class CLINotFoundError(Exception): pass
    class CLIConnectionError(Exception): pass
    class ProcessError(Exception): pass
    class ClaudeSDKError(Exception): pass
    logger.warning("Claude Agent SDK not available. Tool-based chat features are disabled.")

chat_bp = APIRouter(prefix='/api/chat', tags=['chat'])

# SSE client management for chat progress updates
chat_sse_clients = {}
chat_sse_lock = threading.Lock()

# Active agent task tracking for cancellation
active_agent_tasks = {}


@chat_bp.get('/ping')
async def chat_ping():
    """Connectivity + readiness check for chat functionality."""
    try:
        claude_model = os.getenv("OBBY_CLAUDE_MODEL", cfg.CLAUDE_MODEL)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        available = CLAUDE_AVAILABLE and bool(api_key)

        return {
            'available': available,
            'model': claude_model,
            'claude_model': claude_model,
            'claude_sdk': CLAUDE_AVAILABLE,
            'has_api_key': bool(api_key),
        }
    except Exception as e:
        return JSONResponse({'available': False, 'error': str(e)}, status_code=200)


@chat_bp.get('/progress/{session_id}')
async def chat_progress_events(session_id: str, request: Request):
    """SSE endpoint for chat progress updates"""
    async def event_stream():
        client_id = f"chat-{session_id}"
        client_queue = asyncio.Queue(maxsize=100)

        # Register client for global tracking
        register_sse_client(client_id)

        with chat_sse_lock:
            chat_sse_clients[session_id] = client_queue

        logger.info(f"[Chat Progress] New client connected: {client_id}")

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id, 'clientId': client_id, 'message': 'Connected to chat progress updates'})}\n\n"

            while True:
                # Check if client disconnected BEFORE blocking operation
                if await request.is_disconnected():
                    logger.info(f"[Chat Progress] Client {client_id} disconnected (detected)")
                    break

                try:
                    # Wait for events with shorter timeout for faster shutdown (5s instead of 30s)
                    event = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'session_id': session_id})}\n\n"
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    # Client disconnected - this is normal, just log and exit
                    logger.debug(f"[Chat Progress] Client {client_id} disconnected: {e}")
                    break
                except Exception as e:
                    logger.error(f"[Chat Progress] SSE stream error for {client_id}: {e}")
                    break
        finally:
            # Remove client from local list
            with chat_sse_lock:
                if session_id in chat_sse_clients:
                    del chat_sse_clients[session_id]
                    logger.info(f"[Chat Progress] Client {client_id} cleaned up from local list")

            # Unregister from global tracking
            unregister_sse_client(client_id)

    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'X-Accel-Buffering': 'no'  # Disable buffering for nginx/proxy compatibility
    })


def notify_chat_progress(session_id: str, event_type: str, message: str, data: Dict = None):
    """Notify SSE clients of chat progress updates"""
    try:
        from datetime import datetime
        event = {
            'type': event_type,
            'session_id': session_id,
            'message': message,
            'timestamp': str(datetime.now().isoformat())
        }
        if data:
            event.update(data)
        
        with chat_sse_lock:
            if session_id in chat_sse_clients:
                try:
                    chat_sse_clients[session_id].put_nowait(event)
                    logger.debug(f"Sent chat progress event to session {session_id}: {event_type}")
                except asyncio.QueueFull:
                    logger.warning(f"Chat SSE queue full for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to notify chat SSE client {session_id}: {e}")
                    # Remove disconnected client
                    del chat_sse_clients[session_id]
    except Exception as e:
        logger.error(f"Failed to notify chat progress: {e}")





@chat_bp.post('/agent_query')
async def chat_with_history(request: Request):
    """
    Chat with message history using the Claude Agent SDK.

    Expects JSON: { messages: [{role, content}], temperature?, session_id? }
    """
    try:
        data = await request.json()
        messages = data.get('messages')
        session_id = data.get('session_id')  # Accept session_id from frontend

        if not isinstance(messages, list) or not messages:
            return JSONResponse({'error': 'messages must be a non-empty list'}, status_code=400)

        # Use provided session_id or generate a new one if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        provider = 'claude'
        
        # Send initial progress update with query preview
        user_msg_preview = next((m['content'][:80] + '...' if len(m['content']) > 80 else m['content']
                                for m in reversed(messages) if m['role'] == 'user'), '')
        if user_msg_preview:
            notify_chat_progress(session_id, 'started',
                f'Query: "{user_msg_preview}"', {
                'provider': provider,
                'message_count': len(messages)
            })

        if not CLAUDE_AVAILABLE:
            return JSONResponse(
                {'error': 'Claude Agent SDK not available. Install: pip install claude-agent-sdk'},
                status_code=400
            )

        logger.info("Using Claude Agent SDK for chat")
        
        # Create task for agent execution to allow cancellation
        task = asyncio.create_task(_chat_with_claude_tools(messages, session_id))
        
        # Store task for cancellation capability
        with chat_sse_lock:
            active_agent_tasks[session_id] = task
        
        try:
            # Monitor for client disconnection while waiting for task
            disconnect_check = asyncio.create_task(_check_client_disconnected(request))
            done, pending = await asyncio.wait(
                [task, disconnect_check],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Check which task completed first
            if disconnect_check in done:
                # Client disconnected - cancel the agent task
                logger.info(f"Client disconnected during chat query for session {session_id}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return JSONResponse({
                    'error': 'Client disconnected',
                    'cancelled': True
                }, status_code=499)  # 499 Client Closed Request
            
            # Agent task completed - cancel disconnect check and return result
            disconnect_check.cancel()
            try:
                await disconnect_check
            except asyncio.CancelledError:
                pass
            
            result = await task
            return result
                
        except asyncio.CancelledError:
            logger.info(f"Agent task cancelled for session {session_id}")
            if session_id:
                notify_chat_progress(session_id, 'cancelled', 'Agent operation cancelled by user')
            return JSONResponse({
                'error': 'Agent operation cancelled',
                'cancelled': True
            }, status_code=499)  # 499 Client Closed Request
        finally:
            # Clean up task tracking
            with chat_sse_lock:
                if session_id in active_agent_tasks:
                    del active_agent_tasks[session_id]

    except Exception as e:
        logger.error(f"/api/chat/agent_query failed: {e}")
        # Clean up task tracking on error
        with chat_sse_lock:
            if session_id in active_agent_tasks:
                del active_agent_tasks[session_id]
        return JSONResponse({'error': str(e)}, status_code=500)


async def _check_client_disconnected(request: Request):
    """Helper coroutine to check if client disconnected"""
    while True:
        await asyncio.sleep(1)  # Check every second
        if await request.is_disconnected():
            return True


async def _chat_with_claude_tools(messages: List[Dict], session_id: str = None) -> Dict:
    """Tool-based chat with Claude Agent SDK (automatic orchestration)."""
    import time
    import traceback
    import sys
    import asyncio
    import anyio

    start_time = time.time()

    # Initialize agent logging service for this chat session
    agent_logging_service = None
    if session_id:
        try:
            from services.agent_logging_service import get_agent_logging_service
            agent_logging_service = get_agent_logging_service()
            if agent_logging_service.enabled:
                logger.debug(f"Agent logging service initialized for chat session {session_id}")
                # Log chat start
                agent_logging_service.log_operation(
                    session_id=session_id,
                    phase='data_collection',
                    operation='Chat Query Started',
                    details={'message_count': len(messages)},
                    timing={'start_time': time.time()}
                )
        except Exception as e:
            logger.warning(f"Failed to initialize agent logging service for chat: {e}")

    try:
        # Debug: Check current event loop policy and loop type
        current_policy = asyncio.get_event_loop_policy()
        policy_name = type(current_policy).__name__
        logger.info(f"🔍 Current event loop policy: {policy_name}")

        # Check current running loop
        try:
            loop = asyncio.get_running_loop()
            loop_type = type(loop).__name__
            logger.info(f"🔍 Current running loop: {loop_type}")
            
            # On Windows, we MUST have ProactorEventLoop for subprocess support
            if sys.platform == 'win32' and loop_type != 'ProactorEventLoop':
                logger.error(f"❌ Wrong loop type on Windows: {loop_type} (need ProactorEventLoop)")
                logger.error("   This usually means uvicorn's reloader bypassed the event loop policy")
                logger.error("   Try running without --reload or restart the backend completely")
                return JSONResponse({
                    'error': f'Windows subprocess not supported with {loop_type}. Run backend.py without --reload'
                }, status_code=500)
        except RuntimeError:
            logger.info("🔍 No running loop yet")

        # Check if ANTHROPIC_API_KEY is set
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("❌ Claude SDK Error: ANTHROPIC_API_KEY not set in environment")
            return JSONResponse({'error': 'ANTHROPIC_API_KEY not configured'}, status_code=400)

        logger.info(f"✓ Claude API Key found: {api_key[:8]}...{api_key[-4:]}")
        logger.info(f"✓ Claude SDK available: {CLAUDE_AVAILABLE}")
        
        # Send progress update
        if session_id:
            notify_chat_progress(session_id, 'validating', 'Claude API key validated - SDK ready')
        
        # Get last user message
        user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not user_message:
            logger.error("❌ No user message found in conversation")
            return JSONResponse({'error': 'No user message found'}, status_code=400)

        logger.info(f"📝 User message: {user_message[:100]}..." if len(user_message) > 100 else f"📝 User message: {user_message}")

        # Build context from previous messages (last 3 for brevity)
        context_messages = [m for m in messages[:-1] if m['role'] in ('user', 'assistant')]
        if context_messages:
            context = "Previous conversation:\n"
            for msg in context_messages[-3:]:
                context += f"{msg['role']}: {msg['content'][:200]}\n"  # Truncate long messages
            user_message = context + f"\nCurrent question: {user_message}"
            logger.info(f"📚 Added {len(context_messages[-3:])} context messages")

        # Configure Claude with built-in tools only
        logger.info("🔧 Configuring Claude with built-in tools...")
        
        # Initialize WatchHandler to get watch directory restrictions
        project_root = Path.cwd()
        watch_handler = WatchHandler(project_root)
        watch_directories = []
        restricted_cwd = project_root
        
        # Get watch directories
        try:
            watch_dirs = watch_handler.get_watch_directories(project_root)
            for wd in watch_dirs:
                try:
                    rel_path = wd.relative_to(project_root)
                    watch_directories.append(str(rel_path))
                except ValueError:
                    watch_directories.append(str(wd))
            
            if not watch_directories:
                # Fallback to watch patterns if no directories resolved
                watch_directories = list(watch_handler.watch_patterns)
            
            # Set restricted cwd to first watch directory
            if watch_directories:
                first_watch_dir = watch_directories[0].rstrip('/')
                potential_cwd = project_root / first_watch_dir
                if potential_cwd.exists() and potential_cwd.is_dir():
                    restricted_cwd = potential_cwd
            
            logger.info(f"🔒 Watch directories configured: {watch_directories}")
            logger.info(f"🔒 Restricted cwd: {restricted_cwd}")
        except Exception as e:
            logger.warning(f"Failed to initialize watch restrictions: {e}")
        
        # Build watch restriction prompt
        watch_restriction = ""
        if watch_directories:
            dirs_list = ', '.join([f'`{d}`' for d in watch_directories])
            watch_restriction = (
                f"\n\nIMPORTANT FILE ACCESS RESTRICTION:"
                f"\nYou may ONLY access files within these directories: {dirs_list}"
                f"\nDo NOT read, search, or modify files outside these boundaries."
                f"\nIf asked to access files outside these directories, politely explain that you can only work within the configured watch directories."
            )
        
        # Get model from environment or config (default: haiku for cost efficiency)
        claude_model = os.getenv("OBBY_CLAUDE_MODEL", cfg.CLAUDE_MODEL)
        
        options = ClaudeAgentOptions(
            cwd=str(restricted_cwd),
            allowed_tools=[
                "Read",      # Read file contents
                "Write",     # Write to files
                "Bash",      # Execute bash/shell commands
                "Grep",      # Search files (like ripgrep)
                "Glob",      # File pattern matching
                "Edit",      # Edit files
            ],
            max_turns=25,
            model=claude_model,  # "sonnet", "opus", or "haiku"
            system_prompt=(
                "You are a helpful assistant for the Obby file monitoring system. You have access to the file system and can read files, search for content, run commands, and explore the project structure."
                + watch_restriction +
                " Always begin your investigation by searching the notes directory using the Grep tool before considering any other data sources."
                "\n\nSemantic Insights Database:"
                " You have access to a SQLite database (obby.db) containing AI-generated semantic insights about the user's notes."
                " Use the Bash tool to query it when the user asks about insights, todos, projects, or patterns in their notes."
                "\n\nKey tables:"
                "\n- semantic_insights: AI-generated insights (id, insight_type, title, summary, source_notes, evidence, confidence, priority, status, created_at)"
                "\n  - insight_type: 'active_todos', 'stale_todo', 'todo_summary', 'project_overview', 'orphan_mention', 'connection', 'theme'"
                "\n  - status: 'new', 'viewed', 'dismissed', 'pinned', 'actioned'"
                "\n- note_entities: Extracted entities (id, note_path, entity_type, entity_value, context, status, line_number)"
                "\n  - entity_type: 'todo', 'person', 'project', 'concept', 'date', 'mention', 'tag', 'link'"
                "\n\nExample queries:"
                "\n- List insights: sqlite3 obby.db \"SELECT id, insight_type, title, summary FROM semantic_insights WHERE status != 'dismissed' ORDER BY priority DESC LIMIT 10\""
                "\n- Active todos: sqlite3 obby.db \"SELECT entity_value, note_path FROM note_entities WHERE entity_type = 'todo' AND status = 'active'\""
                "\n- Get insight by ID: sqlite3 obby.db \"SELECT * FROM semantic_insights WHERE id = 5\""
                "\n\nFile References:"
                " When mentioning files in your response, format them as inline code with the full relative path:"
                " - Correct format: `frontend/src/Chat.tsx` or `backend.py` or `routes/chat.py`"
                " - Incorrect format: frontend/src/Chat.tsx (plain text without backticks)"
                " - Always use project-relative paths (e.g., `frontend/src/Chat.tsx` not `/mnt/d/Python Projects/obby/frontend/src/Chat.tsx`)"
                " - Include the path when useful for clarity (e.g., `routes/chat.py` instead of just `chat.py` if there are multiple chat.py files)"
                " - Never include absolute path prefixes like '/mnt/d/', 'D:/', or '/obby/'"
                "\n\nResponse Format:"
                " When you reference, read, modify, or create files during your response, you MUST return a structured JSON response with the following format:"
                ' {"message": "Your response text in markdown format with inline code file references", "fileReferences": [{"path": "relative/path/to/file.md", "action": "read" | "modified" | "created" | "mentioned"}]}'
                "\n\nFile Reference Actions:"
                " - read: Files you read or searched through to answer the question"
                " - modified: Files you edited or updated"
                " - created: New files you created"
                " - mentioned: Files you reference in your response without directly accessing"
                "\n\nIf you do not reference any files, return a simple text response instead of JSON."
            )
        )

        logger.info(f"⚙️  Claude options: model={claude_model}, max_turns=25, tools={options.allowed_tools}, cwd={options.cwd}, watch_dirs={watch_directories}")

        # Send progress update with tool list
        if session_id:
            tool_list = ", ".join(options.allowed_tools[:3])
            if len(options.allowed_tools) > 3:
                tool_list += f" + {len(options.allowed_tools) - 3} more"
            notify_chat_progress(session_id, 'configuring', f'Tools configured: {tool_list}')

        # Execute with Claude
        logger.info("🚀 Starting Claude SDK client...")
        conversation_messages = []  # Track separate assistant messages
        current_message_parts = []  # Text blocks for current AssistantMessage
        message_count = 0

        if session_id:
            notify_chat_progress(session_id, 'connecting', 'Connecting to Claude SDK...')

        async with ClaudeSDKClient(options=options) as client:
            logger.info("✓ Claude SDK client initialized")
            
            if session_id:
                notify_chat_progress(session_id, 'sending', 'Sending query to Claude...')
            
            await client.query(user_message)
            logger.info("✓ Query sent to Claude")
            
            if session_id:
                notify_chat_progress(session_id, 'processing', 'Claude is processing your request...')

            async for message in client.receive_response():
                # Check for cancellation before processing each message
                try:
                    # This will raise CancelledError if task was cancelled
                    await asyncio.sleep(0)  # Yield to event loop to check cancellation
                except asyncio.CancelledError:
                    logger.info(f"Agent operation cancelled during message processing for session {session_id}")
                    if session_id:
                        notify_chat_progress(session_id, 'cancelled', 'Agent operation cancelled by user')
                    raise
                
                message_count += 1
                message_type = message.__class__.__name__
                logger.info(f"📨 Received message #{message_count}: {message_type}")

                if message_type == "AssistantMessage":
                    # Save previous message if we have text blocks accumulated
                    if current_message_parts:
                        conversation_messages.append({
                            'role': 'assistant',
                            'content': '\n'.join(current_message_parts)
                        })
                        # Signal frontend to finalize current bubble and start new one
                        if session_id:
                            notify_chat_progress(session_id, 'assistant_message_complete',
                                'Completed assistant message', {
                                    'content': '\n'.join(current_message_parts)
                                })
                        current_message_parts = []  # Reset for new message

                    # Signal start of new assistant message turn
                    if session_id:
                        notify_chat_progress(session_id, 'assistant_message_start',
                            'Starting new assistant message')

                    # Extract text from message content
                    if hasattr(message, 'content'):
                        # First, check for text blocks to show assistant thinking
                        text_blocks = [block for block in message.content if hasattr(block, 'text')]
                        if text_blocks and session_id:
                            # Show preview of assistant's message
                            first_text = text_blocks[0].text.strip()
                            preview = first_text[:80] + "..." if len(first_text) > 80 else first_text
                            if preview:
                                notify_chat_progress(session_id, 'assistant_thinking', f'Claude: {preview}')

                        for idx, block in enumerate(message.content):
                            block_type = block.__class__.__name__
                            logger.info(f"   Block {idx}: {block_type}")

                            # Handle tool use blocks
                            if block_type == "ToolUseBlock" and hasattr(block, 'name'):
                                tool_name = block.name

                                # Create descriptive message with tool arguments
                                tool_message = f'Claude is using tool: {tool_name}'
                                tool_details = {'tool': tool_name}
                                current_file_path = None

                                if hasattr(block, 'input') and block.input:
                                    tool_input = block.input
                                    tool_details['input'] = str(tool_input)[:200]  # Truncate for storage

                                    # Extract key parameters for common tools
                                    if tool_name == 'Read' and isinstance(tool_input, dict):
                                        file_path = tool_input.get('file_path', '')
                                        if file_path:
                                            # Extract just the filename from path
                                            filename = file_path.split('/')[-1].split('\\')[-1]
                                            tool_message = f'Reading file: {filename}'
                                            current_file_path = file_path
                                    elif tool_name == 'Grep' and isinstance(tool_input, dict):
                                        pattern = tool_input.get('pattern', '')
                                        path = tool_input.get('path', '')
                                        if pattern:
                                            path_desc = f" in {path}" if path else ""
                                            pattern_preview = pattern[:50] + ('...' if len(pattern) > 50 else '')
                                            tool_message = f'Searching for: "{pattern_preview}"{path_desc}'
                                            current_file_path = path
                                    elif tool_name == 'Bash' and isinstance(tool_input, dict):
                                        command = tool_input.get('command', '')
                                        if command:
                                            cmd_preview = command[:50] + ('...' if len(command) > 50 else '')
                                            tool_message = f'Executing: {cmd_preview}'
                                    elif tool_name == 'Edit' and isinstance(tool_input, dict):
                                        file_path = tool_input.get('file_path', '')
                                        if file_path:
                                            filename = file_path.split('/')[-1].split('\\')[-1]
                                            tool_message = f'Editing file: {filename}'
                                            current_file_path = file_path
                                    elif tool_name == 'Glob' and isinstance(tool_input, dict):
                                        patterns = tool_input.get('patterns', [])
                                        if patterns:
                                            tool_message = f'Finding files matching: {patterns[0] if len(patterns) == 1 else f"{len(patterns)} patterns"}'
                                    elif tool_name == 'Write' and isinstance(tool_input, dict):
                                        file_path = tool_input.get('file_path', '')
                                        if file_path:
                                            filename = file_path.split('/')[-1].split('\\')[-1]
                                            tool_message = f'Writing to file: {filename}'
                                            current_file_path = file_path

                                logger.info(f"   🔧 Tool Use: {tool_message}")

                                # Log tool usage to database
                                if agent_logging_service and session_id:
                                    try:
                                        agent_logging_service.log_operation(
                                            session_id=session_id,
                                            phase='file_exploration',
                                            operation=tool_message,
                                            details=tool_details,
                                            current_file=current_file_path
                                        )
                                    except Exception as e:
                                        logger.warning(f"Failed to log tool usage: {e}")

                                if session_id:
                                    notify_chat_progress(session_id, 'tool_use', tool_message)
                            
                            # Handle text blocks
                            elif hasattr(block, 'text'):
                                text_preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                                logger.info(f"   Text: {text_preview}")
                                current_message_parts.append(block.text)

                                # Stream text chunk to frontend via SSE
                                if session_id and block.text:
                                    notify_chat_progress(session_id, 'assistant_text_chunk', block.text, {
                                        'chunk': block.text,
                                        'is_complete': False
                                    })
                    else:
                        logger.warning(f"   ⚠️  AssistantMessage has no content attribute")
                
                elif message_type == "ToolResultMessage":
                    # Try to extract result details for more informative messages
                    result_message = 'Tool execution complete'
                    if hasattr(message, 'content') and message.content:
                        # Check if it's a list of content blocks
                        if isinstance(message.content, list) and len(message.content) > 0:
                            first_block = message.content[0]
                            if hasattr(first_block, 'text'):
                                result_text = first_block.text
                                # Extract useful info from result text
                                if 'error' in result_text.lower() or 'failed' in result_text.lower():
                                    result_message = 'Tool execution failed'
                                elif 'found' in result_text.lower():
                                    # Try to extract match count
                                    import re
                                    match = re.search(r'(\d+)\s+(?:match|result|file)', result_text.lower())
                                    if match:
                                        count = match.group(1)
                                        result_message = f'Found {count} results'
                                    else:
                                        result_message = 'Search completed'
                                elif len(result_text) > 0:
                                    result_message = 'Tool execution successful'
                        elif hasattr(message.content, 'text'):
                            result_text = message.content.text
                            if 'error' in result_text.lower():
                                result_message = 'Tool execution failed'
                            elif len(result_text) > 0:
                                result_message = 'Tool execution successful'
                    
                    logger.info(f"   🔧 Tool result: {result_message}")
                    if session_id:
                        notify_chat_progress(session_id, 'tool_result', result_message)
                
                else:
                    logger.info(f"   ℹ️  Other message type: {message_type}")
                    # Send progress update for other message types with more context
                    if session_id:
                        if message_type == "SystemMessage":
                            notify_chat_progress(session_id, 'processing', 'Processing system context and instructions')
                        elif message_type == "UserMessage":
                            notify_chat_progress(session_id, 'processing', 'Processing user query')
                        else:
                            notify_chat_progress(session_id, 'processing', f'Processing: {message_type}')

        # Save final message if we have accumulated text blocks
        if current_message_parts:
            final_content = '\n'.join(current_message_parts)
            file_references = []

            # Try to parse as structured JSON response
            try:
                parsed_response = json.loads(final_content)
                if isinstance(parsed_response, dict) and 'message' in parsed_response:
                    # Extract message and file references from structured response
                    final_content = parsed_response['message']
                    file_references = parsed_response.get('fileReferences', [])
                    logger.info(f"📋 Parsed structured response with {len(file_references)} file references")

                    # Notify frontend about file references
                    if session_id and file_references:
                        notify_chat_progress(session_id, 'file_references', 'File references available', {
                            'fileReferences': file_references
                        })
            except (json.JSONDecodeError, TypeError, ValueError):
                # Not JSON or not our expected structure, use as-is
                logger.debug("Response is not structured JSON, using as plain text")
                pass

            conversation_messages.append({
                'role': 'assistant',
                'content': final_content,
                'fileReferences': file_references if file_references else None
            })

        # Calculate total characters across all messages
        total_chars = sum(len(msg['content']) for msg in conversation_messages)
        elapsed = time.time() - start_time

        logger.info(f"✅ Claude completed successfully in {elapsed:.2f}s")
        logger.info(f"📊 Response stats: {message_count} total messages, {len(conversation_messages)} assistant messages, {total_chars} chars")

        # Send text completion marker
        if session_id:
            notify_chat_progress(session_id, 'assistant_text_chunk', '', {
                'chunk': '',
                'is_complete': True
            })

        # Send completion progress update
        if session_id:
            notify_chat_progress(session_id, 'completed', f'Claude completed in {elapsed:.2f}s', {
                'message_count': message_count,
                'assistant_messages': len(conversation_messages),
                'response_length': total_chars,
                'elapsed_time': elapsed
            })

        # Log chat completion to database
        if agent_logging_service and session_id:
            try:
                agent_logging_service.log_operation(
                    session_id=session_id,
                    phase='generation',
                    operation='Chat Query Completed',
                    details={
                        'message_count': message_count,
                        'assistant_messages': len(conversation_messages),
                        'response_length': total_chars
                    },
                    timing={
                        'start_time': start_time,
                        'end_time': time.time(),
                        'duration': elapsed
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log chat completion: {e}")

        # Return conversation array for proper multi-bubble display
        return {
            'reply': conversation_messages[-1]['content'] if conversation_messages else "No response generated",
            'conversation': conversation_messages,
            'model': 'claude-3-5-sonnet',
            'finish_reason': 'stop',
            'tools_used': True,
            'provider_used': 'claude',
            'backend': 'claude-agent-sdk',
            'session_id': session_id
        }
    
    except asyncio.CancelledError:
        # Re-raise cancellation to be handled by caller
        raise
    except CLINotFoundError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ CLINotFoundError after {elapsed:.2f}s")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Install Claude Agent SDK: pip install claude-agent-sdk")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")

        # Log error to database
        if agent_logging_service and session_id:
            try:
                agent_logging_service.log_operation(
                    session_id=session_id,
                    phase='error',
                    operation='Chat Query Failed: CLI Not Found',
                    details={'error': str(e), 'error_type': 'CLINotFoundError'},
                    timing={'start_time': start_time, 'end_time': time.time(), 'duration': elapsed}
                )
            except Exception:
                pass

        # Send error progress update
        if session_id:
            notify_chat_progress(session_id, 'error', f'Claude CLI not found: {str(e)}', {
                'error_type': 'CLINotFoundError',
                'elapsed_time': elapsed
            })

        return JSONResponse({'error': f'Claude CLI not found: {str(e)}'}, status_code=500)

    except CLIConnectionError as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        tb_str = traceback.format_exc()
        logger.error(f"❌ CLIConnectionError after {elapsed:.2f}s")
        logger.error(f"   Error: {error_msg}")

        # Send error progress update
        if session_id:
            if 'Windows' in error_msg or 'subprocess' in error_msg:
                notify_chat_progress(session_id, 'error', 'Windows subprocess not supported. Restart backend to apply WindowsProactorEventLoopPolicy fix.', {
                    'error_type': 'CLIConnectionError',
                    'elapsed_time': elapsed,
                    'platform': 'win32'
                })
            
            return JSONResponse({
                'error': 'Windows subprocess not supported. Restart backend to apply WindowsProactorEventLoopPolicy fix.'
            }, status_code=500)

        elif 'UnicodeDecodeError' in error_msg or 'charmap' in error_msg:
            logger.error("   ⚠️  Encoding issue detected (Windows charmap problem)")
            logger.error("   Solution: Upgrade claude-agent-sdk or set PYTHONIOENCODING=utf-8")

        logger.error(f"   Traceback:\n{tb_str}")
        return JSONResponse({'error': f'Claude CLI connection failed: {error_msg}'}, status_code=500)

    except ProcessError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ProcessError after {elapsed:.2f}s")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   This usually indicates the Claude process crashed or was killed")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        return JSONResponse({'error': f'Claude process error: {str(e)}'}, status_code=500)

    except ClaudeSDKError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ClaudeSDKError after {elapsed:.2f}s")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        return JSONResponse({'error': f'Claude SDK error: {str(e)}'}, status_code=500)

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Unexpected error after {elapsed:.2f}s")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error message: {str(e)}")
        logger.error(f"   Full traceback:\n{traceback.format_exc()}")

        # Try to extract useful debugging info
        if hasattr(e, '__dict__'):
            logger.error(f"   Error attributes: {e.__dict__}")

        # Log error to database
        if agent_logging_service and session_id:
            try:
                agent_logging_service.log_operation(
                    session_id=session_id,
                    phase='error',
                    operation=f'Chat Query Failed: {type(e).__name__}',
                    details={'error': str(e), 'error_type': type(e).__name__},
                    timing={'start_time': start_time, 'end_time': time.time(), 'duration': elapsed}
                )
            except Exception:
                pass

        # Send error progress update
        if session_id:
            notify_chat_progress(session_id, 'error', f'Unexpected Claude error: {type(e).__name__}: {str(e)}', {
                'error_type': type(e).__name__,
                'elapsed_time': elapsed
            })

        return JSONResponse({'error': f'Unexpected Claude error: {type(e).__name__}: {str(e)}'}, status_code=500)


@chat_bp.post('/cancel/{session_id}')
async def cancel_agent(session_id: str):
    """Cancel an active agent operation."""
    try:
        with chat_sse_lock:
            task = active_agent_tasks.get(session_id)
            
            if not task:
                return JSONResponse({
                    'success': False,
                    'message': f'No active agent task found for session {session_id}'
                }, status_code=404)
            
            # Cancel the task
            task.cancel()
            logger.info(f"Cancelling agent task for session {session_id}")
            
            # Send cancellation notification via SSE
            notify_chat_progress(session_id, 'cancelled', 'Agent operation cancelled by user')
            
            return {
                'success': True,
                'message': f'Agent operation cancelled for session {session_id}'
            }
    except Exception as e:
        logger.error(f"Failed to cancel agent for session {session_id}: {e}")
        return JSONResponse({
            'success': False,
            'error': str(e)
        }, status_code=500)


@chat_bp.get('/tools')
async def get_available_tools():
    """Get list of available tools and their schemas."""
    try:
        # Claude built-in tools expressed in a schema compatible with the frontend expectations
        tool_schemas = [
            {
                'type': 'function',
                'function': {
                    'name': 'Read',
                    'description': 'Read the contents of a file within the workspace.'
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'Write',
                    'description': 'Write or overwrite file contents.'
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'Bash',
                    'description': 'Execute shell commands inside the workspace.'
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'Grep',
                    'description': 'Search files for matching text (powered by ripgrep).'
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'Glob',
                    'description': 'Match files using glob patterns.'
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'Edit',
                    'description': 'Apply structured edits to files.'
                }
            }
        ]
        tool_names = [schema['function']['name'] for schema in tool_schemas]

        tools_info = {
            'claude_available': CLAUDE_AVAILABLE,
            'tools': tool_schemas,
            'tool_names': tool_names,
            'backends': [
                {
                    'name': 'claude-agent-sdk',
                    'tools': tool_schemas,
                    'tool_names': tool_names
                }
            ]
        }

        return tools_info
    except Exception as e:
        logger.error(f"/api/chat/tools failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
