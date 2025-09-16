"""
Chat API routes (FastAPI)
Provides a minimal chat completion endpoint backed by OpenAIClient
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
from ai.openai_client import OpenAIClient
from config import settings as cfg

logger = logging.getLogger(__name__)

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
    """Chat with messages history. Expects JSON { messages: [{role, content}], temperature? }"""
    try:
        data = await request.json()
        messages = data.get('messages')
        if not isinstance(messages, list) or not messages:
            return JSONResponse({'error': 'messages must be a non-empty list'}, status_code=400)

        # Basic validation/normalization
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
            }
        except Exception as api_err:
            logger.error(f"Chat (history) API error: {api_err}")
            return JSONResponse({'error': f'Chat failed: {str(api_err)}'}, status_code=500)

    except Exception as e:
        logger.error(f"/api/chat/complete failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
