"""
Comprehensive Tests for Chat API
=================================

Tests all chat endpoints and internal functions:
- Simple OpenAI chat
- OpenAI with tools (orchestrator)
- Claude Agent SDK with tools
- Provider selection and fallback logic
- Error handling

Run with: pytest tests/test_chat_api.py -v
Or: python tests/test_chat_api.py (for quick manual testing)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set Windows event loop policy BEFORE any async imports
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request
from fastapi.responses import JSONResponse

# Import chat functions
from routes.chat import (
    chat_single_message,
    chat_with_history,
    _chat_with_openai_simple,
    _chat_with_openai_tools,
    _chat_with_claude_tools,
    CLAUDE_AVAILABLE
)


class TestChatSingleMessage:
    """Test /api/chat/message endpoint (simple single message)"""
    
    @pytest.mark.asyncio
    async def test_simple_message_success(self):
        """Test successful simple message response"""
        # Mock request
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={
            'message': 'Hello, how are you?',
            'system': 'You are a helpful assistant.',
            'temperature': 0.7
        })
        
        # Mock OpenAI client
        with patch('routes.chat.OpenAIClient') as mock_client_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.model = 'gpt-4o-mini'
            mock_instance._get_temperature.return_value = 0.7
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "I'm doing well, thank you!"
            mock_response.choices[0].finish_reason = 'stop'
            
            mock_instance._retry_with_backoff.return_value = mock_response
            mock_client_class.get_instance.return_value = mock_instance
            
            result = await chat_single_message(request)
            
            assert 'reply' in result
            assert result['reply'] == "I'm doing well, thank you!"
            assert result['model'] == 'gpt-4o-mini'
            assert result['finish_reason'] == 'stop'
    
    @pytest.mark.asyncio
    async def test_missing_message(self):
        """Test error when message is missing"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={'message': ''})
        
        result = await chat_single_message(request)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == 400
    
    @pytest.mark.asyncio
    async def test_openai_not_configured(self):
        """Test error when OpenAI is not configured"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={'message': 'Hello'})
        
        with patch('routes.chat.OpenAIClient') as mock_client_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = False
            mock_client_class.get_instance.return_value = mock_instance
            
            result = await chat_single_message(request)
            
            assert isinstance(result, JSONResponse)
            assert result.status_code == 400


class TestChatWithHistory:
    """Test /api/chat/complete endpoint (with history and provider selection)"""
    
    @pytest.mark.asyncio
    async def test_provider_selection_openai(self):
        """Test explicit OpenAI provider selection"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'provider': 'openai',
            'enable_fallback': False
        })
        
        with patch('routes.chat._chat_with_openai_tools') as mock_openai:
            mock_openai.return_value = {'reply': 'OpenAI response', 'provider_used': 'openai'}
            
            result = await chat_with_history(request)
            
            assert result['reply'] == 'OpenAI response'
            assert result['provider_used'] == 'openai'
            mock_openai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_provider_selection_claude(self):
        """Test explicit Claude provider selection"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'provider': 'claude',
            'enable_fallback': False
        })
        
        if not CLAUDE_AVAILABLE:
            pytest.skip("Claude SDK not available")
        
        with patch('routes.chat._chat_with_claude_tools') as mock_claude:
            mock_claude.return_value = {'reply': 'Claude response', 'provider_used': 'claude'}
            
            result = await chat_with_history(request)
            
            assert result['reply'] == 'Claude response'
            assert result['provider_used'] == 'claude'
            mock_claude.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_claude_to_openai(self):
        """Test fallback from Claude to OpenAI when Claude fails"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'provider': 'claude',
            'enable_fallback': True
        })
        
        with patch('routes.chat._chat_with_claude_tools') as mock_claude, \
             patch('routes.chat._chat_with_openai_tools') as mock_openai:
            
            # Claude fails
            mock_claude.return_value = JSONResponse({'error': 'Claude failed'}, status_code=500)
            # OpenAI succeeds
            mock_openai.return_value = {'reply': 'OpenAI fallback', 'provider_used': 'openai'}
            
            result = await chat_with_history(request)
            
            assert result['reply'] == 'OpenAI fallback'
            assert result.get('fallback_occurred') == True
            assert result.get('fallback_reason') == 'Claude provider failed'
    
    @pytest.mark.asyncio
    async def test_invalid_provider(self):
        """Test error with invalid provider"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'provider': 'invalid_provider'
        })
        
        result = await chat_with_history(request)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == 400
    
    @pytest.mark.asyncio
    async def test_empty_messages(self):
        """Test error with empty messages list"""
        request = Mock(spec=Request)
        request.json = AsyncMock(return_value={
            'messages': [],
            'provider': 'openai'
        })
        
        result = await chat_with_history(request)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == 400


class TestOpenAITools:
    """Test OpenAI orchestrator with tools"""
    
    @pytest.mark.asyncio
    async def test_openai_tools_success(self):
        """Test successful OpenAI tool execution"""
        messages = [{'role': 'user', 'content': 'Search my notes for testing'}]
        data = {}
        
        with patch('routes.chat.OpenAIClient') as mock_client_class, \
             patch('routes.chat.get_orchestrator') as mock_orchestrator_fn:
            
            # Mock client
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.model = 'gpt-4o-mini'
            mock_client_class.get_instance.return_value = mock_client
            
            # Mock orchestrator
            mock_orchestrator = Mock()
            mock_orchestrator.execute_chat_with_tools.return_value = (
                "Found 3 notes about testing",
                [{'role': 'assistant', 'content': 'Found 3 notes about testing'}]
            )
            mock_orchestrator_fn.return_value = mock_orchestrator
            
            result = await _chat_with_openai_tools(messages, data)

            assert 'reply' in result
            assert result['reply'] == "Found 3 notes about testing"
            assert result['tools_used'] is False
            assert result['provider_used'] == 'openai'
            assert result['backend'] == 'openai-orchestrator'
            assert result['agent_actions'] == []
            assert 'raw_conversation' in result

            args, kwargs = mock_orchestrator.execute_chat_with_tools.call_args
            assert 'on_agent_event' in kwargs
            assert callable(kwargs['on_agent_event'])
    
    @pytest.mark.asyncio
    async def test_openai_tools_with_tool_messages(self):
        """Test OpenAI with tool call history"""
        messages = [
            {'role': 'user', 'content': 'Search notes'},
            {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'call_123', 'function': {'name': 'notes_search'}}]},
            {'role': 'tool', 'content': 'Found results', 'tool_call_id': 'call_123', 'name': 'notes_search'}
        ]
        data = {}
        
        with patch('routes.chat.OpenAIClient') as mock_client_class, \
             patch('routes.chat.get_orchestrator') as mock_orchestrator_fn:
            
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client_class.get_instance.return_value = mock_client
            
            mock_orchestrator = Mock()
            mock_orchestrator.execute_chat_with_tools.return_value = ("Results processed", [])
            mock_orchestrator_fn.return_value = mock_orchestrator
            
            result = await _chat_with_openai_tools(messages, data)

            assert isinstance(result, dict)
            assert 'reply' in result
            assert 'agent_actions' in result


class TestClaudeTools:
    """Test Claude Agent SDK with tools"""
    
    @pytest.mark.asyncio
    async def test_claude_missing_api_key(self):
        """Test error when ANTHROPIC_API_KEY is missing"""
        messages = [{'role': 'user', 'content': 'Hello'}]
        data = {}
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}, clear=False):
            result = await _chat_with_claude_tools(messages, data)
            
            assert isinstance(result, JSONResponse)
            assert result.status_code == 400
    
    @pytest.mark.asyncio
    async def test_claude_no_user_message(self):
        """Test error when no user message found"""
        messages = [{'role': 'system', 'content': 'System prompt'}]
        data = {}
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-test-key'}):
            result = await _chat_with_claude_tools(messages, data)
            
            assert isinstance(result, JSONResponse)
            assert result.status_code == 400
    
    @pytest.mark.asyncio
    async def test_claude_event_loop_detection_windows(self):
        """Test Windows event loop type detection"""
        if sys.platform != 'win32':
            pytest.skip("Windows-specific test")
        
        messages = [{'role': 'user', 'content': 'Hello'}]
        data = {}
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-test-key'}):
            # Mock to simulate wrong loop type
            with patch('asyncio.get_running_loop') as mock_loop:
                mock_loop_instance = Mock()
                mock_loop_instance.__class__.__name__ = 'SelectorEventLoop'  # Wrong type!
                mock_loop.return_value = mock_loop_instance
                
                result = await _chat_with_claude_tools(messages, data)
                
                assert isinstance(result, JSONResponse)
                assert result.status_code == 500
                assert 'SelectorEventLoop' in result.body.decode()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not CLAUDE_AVAILABLE, reason="Claude SDK not available")
    async def test_claude_with_context_messages(self):
        """Test Claude with conversation history"""
        messages = [
            {'role': 'user', 'content': 'What is Python?'},
            {'role': 'assistant', 'content': 'Python is a programming language.'},
            {'role': 'user', 'content': 'Tell me more'}
        ]
        data = {}
        
        # This test would require a real Claude CLI setup, so we'll mock it
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-test-key'}):
            with patch('routes.chat.ClaudeSDKClient') as mock_client_class:
                # Mock the async context manager
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.query = AsyncMock()
                
                # Mock message stream - must be an async generator, not coroutine
                async def mock_receive():
                    mock_msg = Mock()
                    mock_msg.__class__.__name__ = 'AssistantMessage'
                    mock_text_block = Mock()
                    mock_text_block.text = 'Python is a versatile language...'
                    mock_msg.content = [mock_text_block]
                    yield mock_msg
                
                # Make receive_response return the async generator directly
                mock_client.receive_response = mock_receive
                mock_client_class.return_value = mock_client
                
                result = await _chat_with_claude_tools(messages, data)
                
                assert isinstance(result, dict)
                assert 'reply' in result
                assert result['provider_used'] == 'claude'


class TestErrorHandling:
    """Test error handling across all chat functions"""
    
    @pytest.mark.asyncio
    async def test_openai_api_error(self):
        """Test handling of OpenAI API errors"""
        messages = [{'role': 'user', 'content': 'Hello'}]
        data = {}
        
        with patch('routes.chat.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client_class.get_instance.return_value = mock_client
            
            with patch('routes.chat.get_orchestrator') as mock_orchestrator_fn:
                mock_orchestrator = Mock()
                mock_orchestrator.execute_chat_with_tools.side_effect = Exception("API Error")
                mock_orchestrator_fn.return_value = mock_orchestrator
                
                result = await _chat_with_openai_tools(messages, data)
                
                assert isinstance(result, JSONResponse)
                assert result.status_code == 500
    
    @pytest.mark.asyncio
    async def test_invalid_message_role(self):
        """Test handling of invalid message roles"""
        messages = [{'role': 'invalid_role', 'content': 'Hello'}]
        data = {}
        
        with patch('routes.chat.OpenAIClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client_class.get_instance.return_value = mock_client
            
            result = await _chat_with_openai_simple(messages, data)
            
            assert isinstance(result, JSONResponse)
            assert result.status_code == 400


# Manual testing functions for quick verification
async def manual_test_openai():
    """Manual test for OpenAI (requires OPENAI_API_KEY)"""
    print("\n=== Testing OpenAI Simple Chat ===")
    messages = [{'role': 'user', 'content': 'Say "OpenAI works!" in exactly those words.'}]
    result = await _chat_with_openai_simple(messages, {})
    
    if isinstance(result, dict):
        print(f"✅ Success: {result['reply']}")
        return True
    else:
        print(f"❌ Failed: {result}")
        return False


async def manual_test_openai_tools():
    """Manual test for OpenAI with tools (requires OPENAI_API_KEY)"""
    print("\n=== Testing OpenAI with Tools ===")
    messages = [{'role': 'user', 'content': 'List files in the notes directory'}]
    result = await _chat_with_openai_tools(messages, {})
    
    if isinstance(result, dict):
        print(f"✅ Success: {result['reply'][:200]}...")
        print(f"   Tools used: {result.get('tools_used', False)}")
        return True
    else:
        print(f"❌ Failed: {result}")
        return False


async def manual_test_claude():
    """Manual test for Claude (requires ANTHROPIC_API_KEY and Claude CLI)"""
    if not CLAUDE_AVAILABLE:
        print("\n⚠️  Claude SDK not available - skipping")
        return None
    
    print("\n=== Testing Claude Agent SDK ===")
    messages = [{'role': 'user', 'content': 'Say "Claude works!" in exactly those words.'}]
    result = await _chat_with_claude_tools(messages, {})
    
    if isinstance(result, dict) and 'reply' in result:
        print(f"✅ Success: {result['reply'][:200]}")
        print(f"   Event loop: {asyncio.get_running_loop().__class__.__name__}")
        return True
    else:
        print(f"❌ Failed: {result}")
        return False


async def run_manual_tests():
    """Run all manual tests"""
    print("=" * 60)
    print("CHAT API MANUAL TESTS")
    print("=" * 60)
    
    results = {}
    
    # Test OpenAI
    if os.getenv('OPENAI_API_KEY'):
        results['openai_simple'] = await manual_test_openai()
        results['openai_tools'] = await manual_test_openai_tools()
    else:
        print("\n⚠️  OPENAI_API_KEY not set - skipping OpenAI tests")
    
    # Test Claude
    if os.getenv('ANTHROPIC_API_KEY'):
        results['claude'] = await manual_test_claude()
    else:
        print("\n⚠️  ANTHROPIC_API_KEY not set - skipping Claude tests")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        if result is True:
            print(f"✅ {test_name}: PASSED")
        elif result is False:
            print(f"❌ {test_name}: FAILED")
        else:
            print(f"⚠️  {test_name}: SKIPPED")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    # Run manual tests (no pytest required)
    print("Running manual tests...")
    print(f"Platform: {sys.platform}")
    print(f"Event loop policy: {asyncio.get_event_loop_policy().__class__.__name__}")
    
    asyncio.run(run_manual_tests())

