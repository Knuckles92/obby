# Claude SDK Integration Fix

## Problem Summary

The Claude SDK features weren't working since implementation. The issue was that the code wasn't following the patterns shown in the working examples from the `claude sdk examples/` folder.

## Root Causes

### 1. **Incorrect Message Type Checking**
**Before:**
```python
if isinstance(message, AssistantMessage):
    for block in message.content:
        if isinstance(block, TextBlock):
            result.append(block.text)
```

**After (from working examples):**
```python
message_type = message.__class__.__name__

if message_type == "AssistantMessage":
    if hasattr(message, 'content'):
        for block in message.content:
            if hasattr(block, 'text'):
                result.append(block.text)
```

**Why:** Using `isinstance()` doesn't work reliably with Claude SDK message types. The working examples use `__class__.__name__` string comparison and `hasattr()` checks.

### 2. **Missing Error Logging**
**Before:**
```python
except Exception as e:
    logger.error(f"Error: {e}")
```

**After:**
```python
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
```

**Why:** Adding `exc_info=True` provides full stack traces for debugging.

### 3. **Missing Dependencies**
The `requirements.txt` was missing:
- `claude-agent-sdk>=0.1.0`
- `anyio>=4.0.0` (required by claude-agent-sdk)

## Files Fixed

### 1. `ai/claude_agent_client.py`
- ✅ Fixed `analyze_diff()` - now properly extracts text from AssistantMessage
- ✅ Fixed `summarize_changes()` - uses correct message type checking
- ✅ Fixed `interactive_analysis()` - properly handles async iteration
- ✅ Fixed `ask_question()` - matches working example patterns
- ✅ Added proper exception logging with stack traces

### 2. `routes/chat.py`
- ✅ Fixed `_chat_with_claude_tools()` - uses correct message type checking
- ✅ Properly extracts text from message content blocks
- ✅ Maintains existing error handling and fallback logic

### 3. `requirements.txt`
- ✅ Added `claude-agent-sdk>=0.1.0`
- ✅ Added `anyio>=4.0.0`
- ✅ Added helpful comments about npm dependency

## Key Patterns from Working Examples

### Pattern 1: Message Type Checking
```python
async for message in query(prompt=prompt, options=options):
    message_type = message.__class__.__name__
    
    match message_type:
        case "SystemMessage":
            # Session initialization
            pass
        
        case "AssistantMessage":
            # Claude's response - extract text here
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        result.append(block.text)
        
        case "ResultMessage":
            # Performance metrics
            pass
```

### Pattern 2: Using anyio for Script Execution
```python
import anyio

async def main():
    # Your async code here
    pass

if __name__ == "__main__":
    anyio.run(main)  # Not asyncio.run(main())
```

### Pattern 3: Proper Error Handling
```python
try:
    # Claude SDK calls
    pass
except CLINotFoundError:
    logger.error("Install: npm install -g @anthropic-ai/claude-code")
    # Fallback logic
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    # Fallback logic
```

## Testing

### Quick Test
Run the test script:
```bash
python test_claude_fix.py
```

This will:
1. Test basic query functionality
2. Test diff analysis
3. Test batch change summary

### Prerequisites
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Claude Code CLI (required by claude-agent-sdk)
npm install -g @anthropic-ai/claude-code

# Set API key
# Windows PowerShell:
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Windows CMD:
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Linux/Mac:
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### Manual Test via API

Start the backend:
```bash
python backend.py
```

Test the chat endpoint with tools:
```bash
curl -X POST http://localhost:8001/api/chat/complete \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is 2 + 2?"}
    ],
    "use_tools": true
  }'
```

Expected response:
```json
{
  "reply": "2 + 2 equals 4.",
  "model": "claude-3-5-sonnet",
  "finish_reason": "stop",
  "tools_used": true,
  "backend": "claude-agent-sdk"
}
```

## Working Examples Reference

The `claude sdk examples/` folder contains fully working examples:

1. **`01_basic_query.py`** - Simple hello world
2. **`02_streaming_response.py`** - Streaming responses
3. **`03_custom_tools.py`** - Custom tool integration
4. **`04_hooks.py`** - Pre/post processing hooks
5. **`05_error_handling.py`** - Error handling patterns
6. **`06_mcp_server.py`** - MCP server integration

Run any example:
```bash
cd "D:\Python Projects\obby"
python "claude sdk examples/01_basic_query.py"
```

## Verification Checklist

- [x] Fixed message type checking in all methods
- [x] Added proper error logging with stack traces
- [x] Updated `requirements.txt` with dependencies
- [x] Created test script (`test_claude_fix.py`)
- [x] Verified no linter errors
- [x] Documented fix in `docs/CLAUDE_SDK_FIX.md`

## Usage in Obby

### Chat API
Use `use_tools=true` to enable Claude:
```javascript
// Frontend example
fetch('/api/chat/complete', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: 'Analyze recent changes' }
    ],
    use_tools: true  // Enable Claude Agent SDK
  })
})
```

### Programmatic Use
```python
from ai.claude_agent_client import ClaudeAgentClient

client = ClaudeAgentClient()

# Simple question
answer = await client.ask_question("What is Python?")

# Analyze a diff
analysis = await client.analyze_diff(diff_content, context="...")

# Summarize changes
summary = await client.summarize_changes(changes, max_length="brief")
```

## Fallback Behavior

If Claude SDK is unavailable:
1. Chat API automatically falls back to OpenAI orchestrator
2. All error handling is already in place
3. User gets a consistent experience

## Next Steps

1. ✅ **Test the fix**: Run `python test_claude_fix.py`
2. ✅ **Verify API**: Start backend and test chat endpoint
3. ⏭️ **Optional**: Integrate Claude into batch processing
4. ⏭️ **Optional**: Add Claude support to living notes
5. ⏭️ **Optional**: Create hybrid workflows (OpenAI + Claude)

## References

- Working examples: `claude sdk examples/`
- Original implementation: `examples/claude_integration_example.py`
- Setup guide: `docs/CLAUDE_SETUP.md`
- SDK documentation: https://github.com/anthropic-ai/claude-agent-sdk

