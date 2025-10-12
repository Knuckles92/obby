# Tests

This directory contains automated tests for the Obby project.

## Available Tests

### Chat API Tests (`test_chat_api.py`) ✅
Comprehensive test suite for all chat functionality:
- OpenAI simple chat
- OpenAI with tools (orchestrator)
- Claude Agent SDK with tools
- Provider selection and fallback
- Error handling and edge cases

**Total: 16 tests, all passing ✅**

## Running Tests

### Prerequisites
```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio
```

### Quick Manual Tests
Run without pytest - performs real API calls:
```powershell
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
Run all automated tests with mocks:
```powershell
# All tests
pytest tests/test_chat_api.py -v

# Specific test class
pytest tests/test_chat_api.py::TestClaudeTools -v

# Specific test
pytest tests/test_chat_api.py::TestClaudeTools::test_claude_event_loop_detection_windows -v
```

## Test Coverage

### Chat API (`test_chat_api.py`)
- ✅ Single message endpoint (`/api/chat/message`)
- ✅ Chat with history endpoint (`/api/chat/complete`)
- ✅ OpenAI provider (simple & tools)
- ✅ Claude provider (Agent SDK)
- ✅ Provider fallback mechanism
- ✅ Error handling
- ✅ Windows subprocess support
- ✅ Invalid input validation

## Environment Requirements

### For Manual Tests (Real API Calls)
- `OPENAI_API_KEY` - Required for OpenAI tests
- `ANTHROPIC_API_KEY` - Required for Claude tests
- Claude CLI installed: `npm install -g @anthropic-ai/claude-code`

### For Automated Tests (Mocked)
- No API keys needed (tests use mocks)
- Faster execution
- Isolated from external services

## Future Structure

As we add more tests, we'll organize them into:

```
tests/
├── test_chat_api.py           # Chat API tests (16 tests) ✅
├── unit/                       # Unit tests for individual components
│   ├── test_diff_generation.py
│   ├── test_file_tracking.py
│   └── test_ai_prompts.py
├── integration/                # Integration tests for API endpoints
│   ├── test_monitoring_api.py
│   ├── test_sse_streams.py
│   └── test_session_summary_api.py
├── fixtures/                   # Test data and fixtures
└── conftest.py                 # Pytest configuration
```

## Planned Tests

Future test additions:
- Unit tests for diff generation (`core/file_tracker.py`)
- Unit tests for file monitoring (`core/monitor.py`)
- Integration tests for SSE streams
- Integration tests for session summaries
- Performance/load tests
- Frontend component tests (vitest)

## Documentation

See `docs/CHAT_API_FIX_AND_TESTS.md` for:
- Detailed test descriptions
- Troubleshooting guide
- API testing examples
- Success criteria

## Development Testing

For debugging and investigation scripts, see the `/debug/` directory.
