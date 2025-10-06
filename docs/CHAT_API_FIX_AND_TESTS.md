# Chat API Fix and Comprehensive Testing

## Problem Summary

The chat API was experiencing issues with Claude Agent SDK on Windows, specifically:
- `CLIConnectionError: Failed to start Claude Code`
- Windows asyncio subprocess issue
- Event loop policy not being applied correctly

## Root Causes Fixed

### 1. Missing Virtual Environment Activation
**Problem**: Running `python backend.py` without activating the venv caused `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Always activate venv first:
```powershell
.\venv\Scripts\activate
```

### 2. Uvicorn Event Loop Issue
**Problem**: Even though `WindowsProactorEventLoopPolicy` was set at the top of `backend.py`, uvicorn's reloader wasn't using it properly.

**Solution**: Explicitly specify `loop='asyncio'` in uvicorn config:
```python
if sys.platform == 'win32':
    uvicorn_config['loop'] = 'asyncio'  # Use asyncio with ProactorEventLoopPolicy
```

### 3. Loop Type Detection
**Problem**: No way to detect if the wrong loop type was being used.

**Solution**: Added detection in `_chat_with_claude_tools()`:
```python
loop = asyncio.get_running_loop()
loop_type = type(loop).__name__

if sys.platform == 'win32' and loop_type != 'ProactorEventLoop':
    logger.error(f"❌ Wrong loop type: {loop_type} (need ProactorEventLoop)")
    return JSONResponse({'error': 'Windows subprocess not supported'}, status_code=500)
```

## Files Modified

### 1. `backend.py`
- Added explicit `loop='asyncio'` parameter for uvicorn on Windows
- Ensures uvicorn respects the `WindowsProactorEventLoopPolicy`

### 2. `routes/chat.py`
- Added event loop type detection
- Enhanced error logging for debugging
- Improved error messages for Windows subprocess issues

### 3. `requirements.txt`
- Added `pytest>=7.0.0`
- Added `pytest-asyncio>=0.21.0`

### 4. `tests/test_chat_api.py` (NEW)
- Comprehensive test suite for all chat functions
- 16 tests covering all edge cases and error handling
- Manual test runner for quick verification

### 5. `docs/WINDOWS_CLAUDE_SUBPROCESS_FIX.md` (NEW)
- Detailed documentation of the subprocess issue
- Technical explanation of ProactorEventLoop vs SelectorEventLoop
- Alternative solutions if issues persist

## Test Coverage

### Test Suite Overview
```
tests/test_chat_api.py - 16 tests, all passing ✅
├── TestChatSingleMessage (3 tests)
│   ├── test_simple_message_success
│   ├── test_missing_message
│   └── test_openai_not_configured
│
├── TestChatWithHistory (5 tests)
│   ├── test_provider_selection_openai
│   ├── test_provider_selection_claude
│   ├── test_fallback_claude_to_openai
│   ├── test_invalid_provider
│   └── test_empty_messages
│
├── TestOpenAITools (2 tests)
│   ├── test_openai_tools_success
│   └── test_openai_tools_with_tool_messages
│
├── TestClaudeTools (4 tests)
│   ├── test_claude_missing_api_key
│   ├── test_claude_no_user_message
│   ├── test_claude_event_loop_detection_windows
│   └── test_claude_with_context_messages
│
└── TestErrorHandling (2 tests)
    ├── test_openai_api_error
    └── test_invalid_message_role
```

### Manual Tests (All Passing ✅)
```
✅ openai_simple: Basic OpenAI chat
✅ openai_tools: OpenAI with tool orchestrator (file listing)
✅ claude: Claude Agent SDK with tools
   Event loop: ProactorEventLoop ✅
```

## Running Tests

### Quick Manual Tests
```powershell
# Activate venv
.\venv\Scripts\activate

# Run manual tests (no pytest needed)
python tests/test_chat_api.py
```

Expected output:
```
✅ openai_simple: PASSED
✅ openai_tools: PASSED
✅ claude: PASSED
   Event loop: ProactorEventLoop
```

### Full Pytest Suite
```powershell
# Run all tests with verbose output
pytest tests/test_chat_api.py -v

# Run specific test class
pytest tests/test_chat_api.py::TestClaudeTools -v

# Run specific test
pytest tests/test_chat_api.py::TestClaudeTools::test_claude_event_loop_detection_windows -v
```

Expected output:
```
============================= 16 passed in 26.67s =============================
```

## Verification Checklist

After starting the backend, verify these log messages:

1. **Event loop policy set correctly**:
   ```
   🪟 [STARTUP] Windows: Set WindowsProactorEventLoopPolicy for Claude SDK subprocess support
   ```

2. **Uvicorn using asyncio loop**:
   ```
   INFO:__main__:Using asyncio loop with WindowsProactorEventLoopPolicy for Claude SDK support
   ```

3. **When chatting with Claude**:
   ```
   INFO:routes.chat:🔍 Current event loop policy: WindowsProactorEventLoopPolicy
   INFO:routes.chat:🔍 Current running loop: ProactorEventLoop
   INFO:routes.chat:✓ Claude API Key found: sk-ant-a...
   INFO:routes.chat:🚀 Starting Claude SDK client...
   INFO:routes.chat:✓ Claude SDK client initialized
   INFO:routes.chat:✅ Claude completed successfully in 2.45s
   ```

## Testing the API

### Test OpenAI Chat
```powershell
curl -X POST http://localhost:8001/api/chat/complete `
  -H "Content-Type: application/json" `
  -d '{"messages": [{"role": "user", "content": "Say hello"}], "provider": "openai"}'
```

### Test Claude Chat
```powershell
curl -X POST http://localhost:8001/api/chat/complete `
  -H "Content-Type: application/json" `
  -d '{"messages": [{"role": "user", "content": "List files in notes directory"}], "provider": "claude"}'
```

### Test Fallback Behavior
```powershell
curl -X POST http://localhost:8001/api/chat/complete `
  -H "Content-Type: application/json" `
  -d '{"messages": [{"role": "user", "content": "Hello"}], "provider": "claude", "enable_fallback": true}'
```

## What Each Test Validates

### Simple Message Tests
- ✅ Basic OpenAI chat works
- ✅ Error handling for missing messages
- ✅ Error handling when API key not configured

### History & Provider Tests
- ✅ Explicit provider selection (openai/claude)
- ✅ Fallback from Claude to OpenAI
- ✅ Invalid provider rejection
- ✅ Empty message list rejection

### OpenAI Tools Tests
- ✅ Tool execution with orchestrator
- ✅ Tool call history handling
- ✅ Tool result processing

### Claude Tools Tests
- ✅ Missing API key detection
- ✅ Missing user message detection
- ✅ **Event loop type detection (Windows-specific)**
- ✅ Conversation history context building

### Error Handling Tests
- ✅ API error handling
- ✅ Invalid message role handling

## Known Limitations

### Windows Subprocess Support
- Requires `ProactorEventLoop` (handled automatically now)
- Uvicorn's reloader can sometimes interfere (fixed by `loop='asyncio'`)
- If issues persist, run without reload: `uvicorn.run(..., reload=False)`

### Claude SDK Requirements
- Python package: `claude-agent-sdk>=0.1.0` (installed)
- NPM CLI: `@anthropic-ai/claude-code@2.0.5` (installed globally)
- API key: `ANTHROPIC_API_KEY` environment variable

### Testing Limitations
- Claude tests mock the SDK client (full integration requires Claude CLI)
- Manual tests perform actual API calls (require valid API keys)
- Some tests may be slower due to real API calls

## Troubleshooting

### If tests fail:
1. **Check API keys**: `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` must be set
2. **Check venv**: Ensure `.\venv\Scripts\activate` is run first
3. **Check dependencies**: Run `pip install -r requirements.txt`
4. **Check Claude CLI**: Run `npm list -g @anthropic-ai/claude-code`

### If Claude still fails in production:
1. **Check logs** for event loop type
2. **Restart backend completely** (not just reload)
3. **Try without reload**: Modify `backend.py` to use `reload=False`
4. **Use fallback**: Set `enable_fallback=true` in API calls

## Success Metrics

✅ **All 16 automated tests pass**  
✅ **All 3 manual tests pass**  
✅ **Event loop: ProactorEventLoop (Windows)**  
✅ **Claude chat works end-to-end**  
✅ **OpenAI chat works end-to-end**  
✅ **Fallback mechanism works**  

## Related Documentation

- `docs/WINDOWS_CLAUDE_SUBPROCESS_FIX.md` - Subprocess issue details
- `docs/CLAUDE_SDK_FIX.md` - General Claude SDK fixes
- `docs/WINDOWS_CLAUDE_ENCODING_FIX.md` - Encoding issues
- `docs/CLAUDE_SDK_SIMPLIFICATION.md` - Built-in tools approach

## Next Steps

1. ✅ **All tests passing**
2. ✅ **Backend runs without errors**
3. ✅ **Claude works on Windows**
4. ⏭️ Optional: Add more integration tests
5. ⏭️ Optional: Add performance tests
6. ⏭️ Optional: Add load testing

## Conclusion

The chat API is now fully tested and working on Windows with:
- Comprehensive test coverage (16 tests)
- Proper Windows event loop configuration
- Clear error messages and debugging
- Automatic fallback mechanisms
- Full documentation

Both OpenAI and Claude providers work reliably with tool support. 🎉

