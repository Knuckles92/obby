"""
Chat API routes (FastAPI)
Provides chat completion endpoints with hybrid AI support:
- OpenAI for simple chat (fast, cost-effective)
- Claude Agent SDK for tool-based chat (automatic orchestration)
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import os
import json
import queue
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from ai.openai_client import OpenAIClient
from ai.agent_orchestrator import get_orchestrator
from config import settings as cfg

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
    logger.warning("Claude Agent SDK not available. Tool-based chat will use OpenAI orchestrator.")

chat_bp = APIRouter(prefix='/api/chat', tags=['chat'])

# SSE client management for chat progress updates
chat_sse_clients = {}
chat_sse_lock = threading.Lock()


@chat_bp.get('/ping')
async def chat_ping():
    """Connectivity + readiness check for chat functionality."""
    try:
        client = OpenAIClient.get_instance()
        available = client.is_available()
        model = getattr(client, 'model', None)
        return {
            'available': bool(available),
            'model': model,
        }
    except Exception as e:
        return JSONResponse({'available': False, 'error': str(e)}, status_code=200)


@chat_bp.get('/progress/{session_id}')
async def chat_progress_events(session_id: str):
    """SSE endpoint for chat progress updates"""
    def event_stream():
        client_queue = queue.Queue()
        
        with chat_sse_lock:
            chat_sse_clients[session_id] = client_queue
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id, 'message': 'Connected to chat progress updates'})}\n\n"
            
            while True:
                try:
                    # Wait for events with timeout
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive', 'session_id': session_id})}\n\n"
                except Exception as e:
                    logger.error(f"Chat SSE stream error: {e}")
                    break
        finally:
            # Remove client from list when disconnected
            with chat_sse_lock:
                if session_id in chat_sse_clients:
                    del chat_sse_clients[session_id]
    
    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
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
                except queue.Full:
                    logger.warning(f"Chat SSE queue full for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to notify chat SSE client {session_id}: {e}")
                    # Remove disconnected client
                    del chat_sse_clients[session_id]
    except Exception as e:
        logger.error(f"Failed to notify chat progress: {e}")


@chat_bp.post('/message')
async def chat_single_message(request: Request):
    """Stateless chat: send a single message and get a reply."""
    try:
        data = await request.json()
        message = (data.get('message') or '').strip()
        system_prompt = (data.get('system') or 'You are a helpful assistant.').strip()
        temperature = float(data.get('temperature') or cfg.OPENAI_TEMPERATURES.get('chat', 0.7))

        if not message:
            return JSONResponse({'error': 'message is required'}, status_code=400)

        client = OpenAIClient.get_instance()
        if not client.is_available():
            return JSONResponse({'error': 'OpenAI client not configured; set OPENAI_API_KEY'}, status_code=400)

        if not getattr(OpenAIClient, '_warmed_up', False):
            try:
                client.warm_up()
            except Exception:
                pass

        try:
            resp = client._retry_with_backoff(  # reuse internal backoff helper for resilience
                client._invoke_model,
                model=client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                max_completion_tokens=cfg.OPENAI_TOKEN_LIMITS.get('chat', 2000),
                temperature=client._get_temperature(temperature),
            )
            reply = resp.choices[0].message.content.strip()
            finish_reason = getattr(resp.choices[0], 'finish_reason', None)
            return {
                'reply': reply,
                'model': client.model,
                'finish_reason': finish_reason,
            }
        except Exception as api_err:
            logger.error(f"Chat API error: {api_err}")
            return JSONResponse({'error': f'Chat failed: {str(api_err)}'}, status_code=500)

    except Exception as e:
        logger.error(f"/api/chat/message failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@chat_bp.post('/complete')
async def chat_with_history(request: Request):
    """
    Chat with messages history and AI provider selection.

    Provider-based approach:
    - provider='openai': Use OpenAI with tool orchestrator
    - provider='claude': Use Claude Agent SDK with tools
    - enable_fallback=true: Automatically fallback to other provider on failure

    Expects JSON: { messages: [{role, content}], temperature?, provider?, enable_fallback? }
    """
    try:
        data = await request.json()
        messages = data.get('messages')
        provider = data.get('provider', 'claude').lower()  # Default to Claude
        enable_fallback = data.get('enable_fallback', False)  # Default to disabled
        session_id = data.get('session_id')  # Accept session_id from frontend

        if not isinstance(messages, list) or not messages:
            return JSONResponse({'error': 'messages must be a non-empty list'}, status_code=400)

        if provider not in ('openai', 'claude'):
            return JSONResponse({'error': f'Invalid provider: {provider}. Use "openai" or "claude"'}, status_code=400)

        # Use provided session_id or generate a new one if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Send initial progress update with query preview
        user_msg_preview = next((m['content'][:80] + '...' if len(m['content']) > 80 else m['content']
                                for m in reversed(messages) if m['role'] == 'user'), '')
        if user_msg_preview:
            notify_chat_progress(session_id, 'started',
                f'Query: "{user_msg_preview}"', {
                'provider': provider,
                'message_count': len(messages)
            })

        # Route based on provider selection
        if provider == 'claude':
            if CLAUDE_AVAILABLE:
                logger.info("Using Claude Agent SDK (user selected)")
                result = await _chat_with_claude_tools(messages, data, session_id)

                # Check if Claude failed and fallback is enabled
                if isinstance(result, JSONResponse) and enable_fallback:
                    logger.info("Claude failed, falling back to OpenAI")
                    result = await _chat_with_openai_tools(messages, data)
                    if isinstance(result, dict):
                        result['fallback_occurred'] = True
                        result['fallback_reason'] = 'Claude provider failed'
                return result
            else:
                if enable_fallback:
                    logger.info("Claude not available, falling back to OpenAI")
                    result = await _chat_with_openai_tools(messages, data, session_id)
                    if isinstance(result, dict):
                        result['fallback_occurred'] = True
                        result['fallback_reason'] = 'Claude SDK not available'
                    return result
                else:
                    return JSONResponse({'error': 'Claude Agent SDK not available. Install: pip install claude-agent-sdk'}, status_code=400)
        else:
            # OpenAI provider
            logger.info("Using OpenAI orchestrator (user selected)")
            result = await _chat_with_openai_tools(messages, data, session_id)

            # Check if OpenAI failed and fallback is enabled
            if isinstance(result, JSONResponse) and enable_fallback and CLAUDE_AVAILABLE:
                logger.info("OpenAI failed, falling back to Claude")
                result = await _chat_with_claude_tools(messages, data, session_id)
                if isinstance(result, dict):
                    result['fallback_occurred'] = True
                    result['fallback_reason'] = 'OpenAI provider failed'
            return result

    except Exception as e:
        logger.error(f"/api/chat/complete failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


async def _chat_with_openai_tools(messages: List[Dict], data: Dict, session_id: str = None) -> Dict:
    """Tool-based chat with OpenAI + AgentOrchestrator (fallback)."""
    # Normalize messages with tool support
    normalized = []
    for m in messages:
        role = (m.get('role') or '').strip()
        content = (m.get('content') or '').strip()
        
        if role not in ('system', 'user', 'assistant', 'tool'):
            return JSONResponse({'error': f'invalid role: {role}'}, status_code=400)
        
        if role == 'tool':
            if not m.get('tool_call_id'):
                return JSONResponse({'error': 'tool messages must have tool_call_id'}, status_code=400)
            normalized.append({
                'role': role,
                'content': content,
                'tool_call_id': m['tool_call_id'],
                'name': m.get('name', '')
            })
        else:
            if not content and role != 'assistant':
                return JSONResponse({'error': 'message content cannot be empty'}, status_code=400)
            
            msg = {'role': role, 'content': content}
            if role == 'assistant' and 'tool_calls' in m:
                msg['tool_calls'] = m['tool_calls']
            
            normalized.append(msg)
    
    client = OpenAIClient.get_instance()
    if not client.is_available():
        return JSONResponse({'error': 'OpenAI client not configured; set OPENAI_API_KEY'}, status_code=400)
    
    if not getattr(OpenAIClient, '_warmed_up', False):
        try:
            client.warm_up()
        except Exception:
            pass
    
    try:
        orchestrator = get_orchestrator()
        agent_actions: List[Dict[str, Any]] = []

        def record_agent_event(event_type: str, payload: Dict[str, Any]):
            # Record actionable items and intermediate assistant reasoning for the activity stream
            if event_type not in {"tool_call", "tool_result", "error", "warning", "assistant_thinking"}:
                # Ignore other low-signal events
                return

            timestamp = datetime.utcnow().isoformat() + "Z"
            action: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "type": event_type,
                "timestamp": timestamp,
            }
            if session_id:
                action["session_id"] = session_id

            if event_type == "assistant_thinking":
                # Capture intermediate assistant messages that introduce tool calls
                content = payload.get("content", "")
                if content.strip():
                    # Extract meaningful preview from content
                    preview = content.strip()[:120]
                    if len(content.strip()) > 120:
                        preview += "..."

                    tool_count = payload.get("tool_count", 0)
                    if tool_count:
                        action["label"] = f"Planning to use {tool_count} tool{'s' if tool_count > 1 else ''}"
                        action["detail"] = preview
                    else:
                        action["label"] = f"Analyzing: {preview}"
                        action["detail"] = content[:500] if len(content) > 120 else None

                    if session_id:
                        notify_chat_progress(session_id, 'assistant_thinking', action["label"])
                else:
                    # Empty reasoning, skip it
                    return

            elif event_type == "tool_call":
                tool_name = payload.get("name", "tool")
                arguments = payload.get("arguments")

                # Create descriptive label based on tool and arguments
                if tool_name == "notes_search" and isinstance(arguments, dict):
                    query = arguments.get("query", "")
                    max_matches = arguments.get("max_matches")
                    if query:
                        label = f"Searching: '{query[:60]}{'...' if len(query) > 60 else ''}'"
                        if max_matches:
                            label += f" (max {max_matches} results)"
                        action["label"] = label
                    else:
                        action["label"] = f"Searching notes"
                else:
                    action["label"] = f"Using {tool_name}"

                # Include full arguments in detail
                if isinstance(arguments, dict):
                    action["detail"] = json.dumps(arguments, indent=2)
                elif isinstance(arguments, str) and arguments:
                    action["detail"] = arguments

                action["tool_call_id"] = payload.get("tool_call_id")
                if session_id:
                    notify_chat_progress(session_id, 'tool_use', action["label"], {
                        'tool_call_id': payload.get("tool_call_id"),
                        'tool_name': tool_name
                    })

            elif event_type == "tool_result":
                tool_name = payload.get("name", "tool")
                content = payload.get("content")
                
                # Create descriptive label with result summary
                label = f"{tool_name} result"
                if content and tool_name == "notes_search":
                    content_str = str(content)
                    # Try to extract match count and file information
                    if "Found" in content_str and "matches" in content_str:
                        # Parse "Found X matches in Y files"
                        import re
                        match = re.search(r'Found (\d+) matches? in (\d+) files?', content_str)
                        if match:
                            match_count = match.group(1)
                            file_count = match.group(2)
                            label = f"Found {match_count} matches in {file_count} files"
                        else:
                            # Fallback: count line breaks to estimate matches
                            lines = content_str.count('\n')
                            if lines > 0:
                                label = f"{tool_name} returned {lines} lines"
                    elif "Error:" in content_str or "failed" in content_str.lower():
                        label = f"{tool_name} failed"
                    elif "No matches found" in content_str or "0 matches" in content_str:
                        label = "No matches found"
                
                action["label"] = label
                
                # Include content summary in detail
                if content:
                    detail_text = str(content)
                    if len(detail_text) > 1500:
                        detail_text = detail_text[:1500] + "..."
                    action["detail"] = detail_text
                    
                action["tool_call_id"] = payload.get("tool_call_id")
                action["success"] = payload.get("success")
                if payload.get("error"):
                    action["error"] = payload.get("error")
                if session_id:
                    # Use descriptive label for SSE notification too
                    notify_chat_progress(session_id, 'tool_result', label, {
                        'tool_call_id': payload.get("tool_call_id"),
                        'tool_name': tool_name,
                        'success': payload.get("success")
                    })

            elif event_type == "error":
                error_msg = payload.get("error") or payload.get("message") or "Unknown error"
                error_type = payload.get("exception_type")

                # Create more descriptive error label
                if error_type:
                    action["label"] = f"Error: {error_type}"
                else:
                    action["label"] = f"Error: {error_msg[:60]}{'...' if len(error_msg) > 60 else ''}"

                action["detail"] = error_msg
                action["error_type"] = error_type

                if session_id:
                    notify_chat_progress(session_id, 'error', action["label"], {
                        'error_type': error_type
                    })

            elif event_type == "warning":
                warning_msg = payload.get("message", "Agent warning")
                action["label"] = warning_msg[:80] + "..." if len(warning_msg) > 80 else warning_msg
                action["detail"] = json.dumps(payload) if payload else None
                if session_id:
                    notify_chat_progress(session_id, 'warning', action["label"], payload)

            # Avoid adding empty labels
            if action.get("label"):
                agent_actions.append(action)

        reply, full_conversation = orchestrator.execute_chat_with_tools(
            normalized,
            max_iterations=5,
            on_agent_event=record_agent_event
        )

        # Include user/system messages and ALL assistant responses in chat
        # Tool messages go only to agent actions
        sanitized_conversation: List[Dict[str, Any]] = []
        for message in full_conversation:
            role = message.get('role')
            
            # Skip tool messages - they're in agent_actions
            if role == 'tool':
                continue
            
            # Include user, system, and assistant messages
            if role in ('user', 'system', 'assistant'):
                sanitized_conversation.append(dict(message))

        tools_used_flag = any(action['type'] in {"tool_call", "tool_result"} for action in agent_actions)

        return {
            'reply': reply,
            'model': client.model,
            'finish_reason': 'stop',
            'conversation': sanitized_conversation,
            'raw_conversation': full_conversation,
            'agent_actions': agent_actions,
            'tools_used': tools_used_flag,
            'provider_used': 'openai',
            'backend': 'openai-orchestrator',
            'session_id': session_id
        }
    except Exception as api_err:
        logger.error(f"OpenAI tool chat error: {api_err}")
        return JSONResponse({'error': f'Chat failed: {str(api_err)}'}, status_code=500)


async def _chat_with_claude_tools(messages: List[Dict], data: Dict, session_id: str = None) -> Dict:
    """Tool-based chat with Claude Agent SDK (automatic orchestration)."""
    import time
    import traceback
    import sys
    import asyncio
    import anyio

    start_time = time.time()

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
        
        options = ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            allowed_tools=[
                "Read",      # Read file contents
                "Write",     # Write to files
                "Bash",      # Execute bash/shell commands
                "Grep",      # Search files (like ripgrep)
                "Glob",      # File pattern matching
                "Edit",      # Edit files
            ],
            max_turns=10,
            system_prompt=(
                "You are a helpful assistant for the Obby file monitoring system. You have access to the file system and can read files, search for content, run commands, and explore the project structure."
                " Always begin your investigation by searching the notes directory using the Grep tool before considering any other data sources."
                " Only run SQL or other database queries as a last resort when the notes search cannot provide the required context."
            )
        )

        logger.info(f"⚙️  Claude options: max_turns=10, tools={options.allowed_tools}, cwd={options.cwd}")

        # Send progress update with tool list
        if session_id:
            tool_list = ", ".join(options.allowed_tools[:3])
            if len(options.allowed_tools) > 3:
                tool_list += f" + {len(options.allowed_tools) - 3} more"
            notify_chat_progress(session_id, 'configuring', f'Tools configured: {tool_list}')

        # Execute with Claude
        logger.info("🚀 Starting Claude SDK client...")
        response_parts = []
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
                message_count += 1
                message_type = message.__class__.__name__
                logger.info(f"📨 Received message #{message_count}: {message_type}")

                if message_type == "AssistantMessage":
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
                                if hasattr(block, 'input') and block.input:
                                    tool_input = block.input
                                    # Extract key parameters for common tools
                                    if tool_name == 'Read' and isinstance(tool_input, dict):
                                        file_path = tool_input.get('file_path', '')
                                        if file_path:
                                            # Extract just the filename from path
                                            filename = file_path.split('/')[-1].split('\\')[-1]
                                            tool_message = f'Reading file: {filename}'
                                    elif tool_name == 'Grep' and isinstance(tool_input, dict):
                                        pattern = tool_input.get('pattern', '')
                                        path = tool_input.get('path', '')
                                        if pattern:
                                            path_desc = f" in {path}" if path else ""
                                            pattern_preview = pattern[:50] + ('...' if len(pattern) > 50 else '')
                                            tool_message = f'Searching for: "{pattern_preview}"{path_desc}'
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
                                    elif tool_name == 'Glob' and isinstance(tool_input, dict):
                                        patterns = tool_input.get('patterns', [])
                                        if patterns:
                                            tool_message = f'Finding files matching: {patterns[0] if len(patterns) == 1 else f"{len(patterns)} patterns"}'
                                    elif tool_name == 'Write' and isinstance(tool_input, dict):
                                        file_path = tool_input.get('file_path', '')
                                        if file_path:
                                            filename = file_path.split('/')[-1].split('\\')[-1]
                                            tool_message = f'Writing to file: {filename}'
                                
                                logger.info(f"   🔧 Tool Use: {tool_message}")
                                if session_id:
                                    notify_chat_progress(session_id, 'tool_use', tool_message)
                            
                            # Handle text blocks
                            elif hasattr(block, 'text'):
                                text_preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                                logger.info(f"   Text: {text_preview}")
                                response_parts.append(block.text)

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

        reply = "\n".join(response_parts) if response_parts else "No response generated"
        elapsed = time.time() - start_time

        logger.info(f"✅ Claude completed successfully in {elapsed:.2f}s")
        logger.info(f"📊 Response stats: {message_count} messages, {len(response_parts)} text blocks, {len(reply)} chars")

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
                'text_blocks': len(response_parts),
                'response_length': len(reply),
                'elapsed_time': elapsed
            })

        return {
            'reply': reply,
            'model': 'claude-3-5-sonnet',
            'finish_reason': 'stop',
            'tools_used': True,
            'provider_used': 'claude',
            'backend': 'claude-agent-sdk',
            'session_id': session_id
        }
    
    except CLINotFoundError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ CLINotFoundError after {elapsed:.2f}s")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Install Claude CLI: npm install -g @anthropic-ai/claude-code")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        
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

        # Check for specific error types
        if 'NotImplementedError' in tb_str and sys.platform == 'win32':
            logger.error("   ⚠️  Windows asyncio subprocess issue detected")
            logger.error("   Root cause: uvicorn started without WindowsProactorEventLoopPolicy")
            logger.error("   Solution: The backend.py should set this BEFORE any imports:")
            logger.error("      if sys.platform == 'win32':")
            logger.error("          asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())")
            logger.error("   Then RESTART the backend server completely")
            
            # Send error progress update
            if session_id:
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

        # Send error progress update
        if session_id:
            notify_chat_progress(session_id, 'error', f'Unexpected Claude error: {type(e).__name__}: {str(e)}', {
                'error_type': type(e).__name__,
                'elapsed_time': elapsed
            })

        return JSONResponse({'error': f'Unexpected Claude error: {type(e).__name__}: {str(e)}'}, status_code=500)


@chat_bp.get('/tools')
async def get_available_tools():
    """Get list of available tools and their schemas."""
    try:
        tools_info = {
            'claude_available': CLAUDE_AVAILABLE,
            'backends': []
        }
        
        # OpenAI orchestrator tools
        orchestrator = get_orchestrator()
        tools_info['backends'].append({
            'name': 'openai-orchestrator',
            'tools': orchestrator.get_tool_schemas(),
            'tool_names': list(orchestrator.tools.keys())
        })
        
        # Claude built-in tools
        if CLAUDE_AVAILABLE:
            tools_info['backends'].append({
                'name': 'claude-agent-sdk',
                'tools': [
                    'Read - Read file contents',
                    'Write - Write to files',
                    'Bash - Execute shell commands',
                    'Grep - Search files',
                    'Glob - File pattern matching',
                    'Edit - Edit files'
                ],
                'tool_names': ['Read', 'Write', 'Bash', 'Grep', 'Glob', 'Edit']
            })
        
        return tools_info
    except Exception as e:
        logger.error(f"/api/chat/tools failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
