"""
Chat API routes (FastAPI)
Provides chat completion endpoints with hybrid AI support:
- OpenAI for simple chat (fast, cost-effective)
- Claude Agent SDK for tool-based chat (automatic orchestration)
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import os
from pathlib import Path
from typing import Dict, List, Any
from ai.openai_client import OpenAIClient
from ai.agent_orchestrator import get_orchestrator
from config import settings as cfg

logger = logging.getLogger(__name__)

# Try to import Claude Agent SDK (optional dependency)
try:
    from ai.claude_agent_client import create_obby_mcp_server, CLAUDE_SDK_AVAILABLE
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

        if not isinstance(messages, list) or not messages:
            return JSONResponse({'error': 'messages must be a non-empty list'}, status_code=400)

        if provider not in ('openai', 'claude'):
            return JSONResponse({'error': f'Invalid provider: {provider}. Use "openai" or "claude"'}, status_code=400)

        # Route based on provider selection
        if provider == 'claude':
            if CLAUDE_AVAILABLE:
                logger.info("Using Claude Agent SDK (user selected)")
                result = await _chat_with_claude_tools(messages, data)

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
                    result = await _chat_with_openai_tools(messages, data)
                    if isinstance(result, dict):
                        result['fallback_occurred'] = True
                        result['fallback_reason'] = 'Claude SDK not available'
                    return result
                else:
                    return JSONResponse({'error': 'Claude Agent SDK not available. Install: pip install claude-agent-sdk'}, status_code=400)
        else:
            # OpenAI provider
            logger.info("Using OpenAI orchestrator (user selected)")
            result = await _chat_with_openai_tools(messages, data)

            # Check if OpenAI failed and fallback is enabled
            if isinstance(result, JSONResponse) and enable_fallback and CLAUDE_AVAILABLE:
                logger.info("OpenAI failed, falling back to Claude")
                result = await _chat_with_claude_tools(messages, data)
                if isinstance(result, dict):
                    result['fallback_occurred'] = True
                    result['fallback_reason'] = 'OpenAI provider failed'
            return result

    except Exception as e:
        logger.error(f"/api/chat/complete failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


async def _chat_with_openai_simple(messages: List[Dict], data: Dict) -> Dict:
    """Simple chat with OpenAI (no tools)."""
    # Normalize messages
    normalized = []
    for m in messages:
        role = (m.get('role') or '').strip()
        content = (m.get('content') or '').strip()
        
        if role not in ('system', 'user', 'assistant'):
            return JSONResponse({'error': f'invalid role: {role}'}, status_code=400)
        if not content:
            return JSONResponse({'error': 'message content cannot be empty'}, status_code=400)
        
        normalized.append({'role': role, 'content': content})
    
    temperature = float(data.get('temperature') or cfg.OPENAI_TEMPERATURES.get('chat', 0.7))
    
    client = OpenAIClient.get_instance()
    if not client.is_available():
        return JSONResponse({'error': 'OpenAI client not configured; set OPENAI_API_KEY'}, status_code=400)
    
    if not getattr(OpenAIClient, '_warmed_up', False):
        try:
            client.warm_up()
        except Exception:
            pass
    
    try:
        resp = client._retry_with_backoff(
            client._invoke_model,
            model=client.model,
            messages=normalized,
            max_completion_tokens=cfg.OPENAI_TOKEN_LIMITS.get('chat', 2000),
            temperature=client._get_temperature(temperature),
        )
        reply = resp.choices[0].message.content.strip()
        finish_reason = getattr(resp.choices[0], 'finish_reason', None)
        
        return {
            'reply': reply,
            'model': client.model,
            'finish_reason': finish_reason,
            'tools_used': False,
            'provider_used': 'openai',
            'backend': 'openai'
        }
    except Exception as api_err:
        logger.error(f"OpenAI simple chat error: {api_err}")
        return JSONResponse({'error': f'Chat failed: {str(api_err)}'}, status_code=500)


async def _chat_with_openai_tools(messages: List[Dict], data: Dict) -> Dict:
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
        reply, full_conversation = orchestrator.execute_chat_with_tools(
            normalized, max_iterations=5
        )
        
        return {
            'reply': reply,
            'model': client.model,
            'finish_reason': 'stop',
            'conversation': full_conversation,
            'tools_used': True,
            'provider_used': 'openai',
            'backend': 'openai-orchestrator'
        }
    except Exception as api_err:
        logger.error(f"OpenAI tool chat error: {api_err}")
        return JSONResponse({'error': f'Chat failed: {str(api_err)}'}, status_code=500)


async def _chat_with_claude_tools(messages: List[Dict], data: Dict) -> Dict:
    """Tool-based chat with Claude Agent SDK (automatic orchestration)."""
    import time
    import traceback
    import sys
    import asyncio
    import anyio

    start_time = time.time()

    try:
        # Debug: Check current event loop policy
        current_policy = asyncio.get_event_loop_policy()
        policy_name = type(current_policy).__name__
        logger.info(f"🔍 Current event loop policy: {policy_name}")

        # Check current running loop
        try:
            loop = asyncio.get_running_loop()
            loop_type = type(loop).__name__
            logger.info(f"🔍 Current running loop: {loop_type}")
        except RuntimeError:
            logger.info("🔍 No running loop yet")

        # Check if ANTHROPIC_API_KEY is set
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("❌ Claude SDK Error: ANTHROPIC_API_KEY not set in environment")
            return JSONResponse({'error': 'ANTHROPIC_API_KEY not configured'}, status_code=400)

        logger.info(f"✓ Claude API Key found: {api_key[:8]}...{api_key[-4:]}")
        logger.info(f"✓ Claude SDK available: {CLAUDE_AVAILABLE}")
        
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

        # Create Obby MCP server with tools
        logger.info("🔧 Creating Obby MCP server with tools...")
        obby_server = create_obby_mcp_server()

        options = ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            mcp_servers={"obby": obby_server},
            allowed_tools=[
                "Read",
                "mcp__obby__get_file_history",    # MCP tools must have mcp__<server>__ prefix
                "mcp__obby__get_recent_changes"
            ],
            max_turns=10,
            system_prompt="You are a helpful assistant for the Obby file monitoring system. Use the get_file_history and get_recent_changes tools when needed to answer questions about files and their change history."
        )

        logger.info(f"⚙️  Claude options: max_turns=10, tools={options.allowed_tools}, cwd={options.cwd}")

        # Execute with Claude
        logger.info("🚀 Starting Claude SDK client...")
        response_parts = []
        message_count = 0

        async with ClaudeSDKClient(options=options) as client:
            logger.info("✓ Claude SDK client initialized")
            await client.query(user_message)
            logger.info("✓ Query sent to Claude")

            async for message in client.receive_response():
                message_count += 1
                message_type = message.__class__.__name__
                logger.info(f"📨 Received message #{message_count}: {message_type}")

                if message_type == "AssistantMessage":
                    # Extract text from message content
                    if hasattr(message, 'content'):
                        for idx, block in enumerate(message.content):
                            block_type = block.__class__.__name__
                            logger.info(f"   Block {idx}: {block_type}")
                            if hasattr(block, 'text'):
                                text_preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                                logger.info(f"   Text: {text_preview}")
                                response_parts.append(block.text)
                    else:
                        logger.warning(f"   ⚠️  AssistantMessage has no content attribute")
                else:
                    logger.info(f"   ℹ️  Skipping non-assistant message: {message_type}")

        reply = "\n".join(response_parts) if response_parts else "No response generated"
        elapsed = time.time() - start_time

        logger.info(f"✅ Claude completed successfully in {elapsed:.2f}s")
        logger.info(f"📊 Response stats: {message_count} messages, {len(response_parts)} text blocks, {len(reply)} chars")

        return {
            'reply': reply,
            'model': 'claude-3-5-sonnet',
            'finish_reason': 'stop',
            'tools_used': True,
            'provider_used': 'claude',
            'backend': 'claude-agent-sdk'
        }
    
    except CLINotFoundError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ CLINotFoundError after {elapsed:.2f}s")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Install Claude CLI: npm install -g @anthropic-ai/claude-code")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
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
        
        # Claude MCP tools
        if CLAUDE_AVAILABLE:
            tools_info['backends'].append({
                'name': 'claude-agent-sdk',
                'tools': [
                    'Read',
                    'get_file_history',
                    'get_recent_changes'
                ],
                'tool_names': ['Read', 'get_file_history', 'get_recent_changes']
            })
        
        return tools_info
    except Exception as e:
        logger.error(f"/api/chat/tools failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
