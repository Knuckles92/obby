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
    Chat with messages history and optional tool calling support.
    
    Hybrid approach:
    - use_tools=false: OpenAI (fast, simple)
    - use_tools=true: Claude Agent SDK if available, else OpenAI orchestrator
    
    Expects JSON: { messages: [{role, content}], temperature?, use_tools? }
    """
    try:
        data = await request.json()
        messages = data.get('messages')
        use_tools = data.get('use_tools', False)  # Default to false for backward compatibility
        
        if not isinstance(messages, list) or not messages:
            return JSONResponse({'error': 'messages must be a non-empty list'}, status_code=400)

        # Route based on tool usage
        if use_tools:
            # Try Claude first for tool-based chat, fallback to OpenAI orchestrator
            if CLAUDE_AVAILABLE:
                logger.info("Using Claude Agent SDK for tool-based chat")
                return await _chat_with_claude_tools(messages, data)
            else:
                logger.info("Using OpenAI orchestrator for tool-based chat (Claude not available)")
                return await _chat_with_openai_tools(messages, data)
        else:
            # Simple chat with OpenAI
            logger.debug("Using OpenAI for simple chat")
            return await _chat_with_openai_simple(messages, data)

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
            'backend': 'openai-orchestrator'
        }
    except Exception as api_err:
        logger.error(f"OpenAI tool chat error: {api_err}")
        return JSONResponse({'error': f'Chat failed: {str(api_err)}'}, status_code=500)


async def _chat_with_claude_tools(messages: List[Dict], data: Dict) -> Dict:
    """Tool-based chat with Claude Agent SDK (automatic orchestration)."""
    try:
        # Check if ANTHROPIC_API_KEY is set
        if not os.getenv('ANTHROPIC_API_KEY'):
            logger.warning("ANTHROPIC_API_KEY not set. Falling back to OpenAI orchestrator.")
            return await _chat_with_openai_tools(messages, data)
        
        # Get last user message
        user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not user_message:
            return JSONResponse({'error': 'No user message found'}, status_code=400)
        
        # Build context from previous messages (last 3 for brevity)
        context_messages = [m for m in messages[:-1] if m['role'] in ('user', 'assistant')]
        if context_messages:
            context = "Previous conversation:\n"
            for msg in context_messages[-3:]:
                context += f"{msg['role']}: {msg['content'][:200]}\n"  # Truncate long messages
            user_message = context + f"\nCurrent question: {user_message}"
        
        # Create Obby MCP server with tools
        obby_server = create_obby_mcp_server()
        
        options = ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            mcp_servers={"obby": obby_server},
            allowed_tools=[
                "Read",
                "mcp__obby__get_file_history",
                "mcp__obby__get_recent_changes"
            ],
            max_turns=10,
            system_prompt="You are a helpful assistant for the Obby file monitoring system. Use tools when needed to answer questions about files, changes, and history."
        )
        
        # Execute with Claude
        response_parts = []
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_message)
            
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_parts.append(block.text)
        
        reply = "\n".join(response_parts) if response_parts else "No response generated"
        
        return {
            'reply': reply,
            'model': 'claude-3-5-sonnet',
            'finish_reason': 'stop',
            'tools_used': True,
            'backend': 'claude-agent-sdk'
        }
    
    except CLINotFoundError as e:
        logger.error(f"Claude CLI not found: {e}. Install: npm install -g @anthropic-ai/claude-code")
        logger.info("Falling back to OpenAI orchestrator")
        return await _chat_with_openai_tools(messages, data)
    
    except CLIConnectionError as e:
        error_msg = str(e)
        logger.error(f"Claude CLI connection error: {error_msg}")
        
        # Check if it's an encoding error
        if 'UnicodeDecodeError' in error_msg or 'charmap' in error_msg:
            logger.warning("Claude CLI encountered encoding issues on Windows. Consider upgrading claude-agent-sdk.")
        
        logger.info("Falling back to OpenAI orchestrator")
        return await _chat_with_openai_tools(messages, data)
    
    except ProcessError as e:
        logger.error(f"Claude process error: {e}")
        logger.info("Falling back to OpenAI orchestrator")
        return await _chat_with_openai_tools(messages, data)
    
    except ClaudeSDKError as e:
        logger.error(f"Claude SDK error: {e}")
        logger.info("Falling back to OpenAI orchestrator")
        return await _chat_with_openai_tools(messages, data)
    
    except Exception as e:
        logger.error(f"Claude tool chat unexpected error: {type(e).__name__}: {e}", exc_info=True)
        # Fallback to OpenAI orchestrator
        logger.info("Falling back to OpenAI orchestrator")
        return await _chat_with_openai_tools(messages, data)


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
