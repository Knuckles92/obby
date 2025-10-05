# Claude SDK Tool Calling - Final Fix

## Problem Identified

The tools defined with `@tool` decorator in `ai/claude_agent_client.py` had **incorrect return format**.

### Root Cause

The Claude SDK's `@tool` decorator requires tools to return data in this specific format:

```python
{
    "content": [
        {
            "type": "text",
            "text": "Your message here"
        }
    ]
}
```

Your original tools were returning plain dictionaries like `{"error": "..."}` or using Flask-SQLAlchemy's `.query` API which doesn't exist in your SQLite setup.

## What Was Fixed

### 1. **Fixed Tool Return Format** ([claude_agent_client.py:272-353](../ai/claude_agent_client.py#L272-L353))

**Before:**
```python
return {"error": f"Failed to retrieve file history: {str(e)}"}
```

**After:**
```python
return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
```

### 2. **Fixed Database Access**

**Before (incorrect - Flask-SQLAlchemy):**
```python
changes = FileChangeModel.query.filter_by(file_path=file_path)\
    .order_by(FileChangeModel.timestamp.desc())\
    .limit(10)\
    .all()
```

**After (correct - direct SQLite):**
```python
from database.connection import DatabaseConnection

db = DatabaseConnection()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, event_type, file_path
        FROM file_changes
        WHERE file_path = ?
        ORDER BY timestamp DESC
        LIMIT 10
    """, (file_path,))
    changes = cursor.fetchall()
```

### 3. **Fixed Tool Registration** ([routes/chat.py:284-288](../routes/chat.py#L284-L288))

**Before:**
```python
allowed_tools=[
    "Read",
    "mcp__obby__get_file_history",  # Wrong prefix
    "mcp__obby__get_recent_changes"
],
```

**After:**
```python
allowed_tools=[
    "Read",
    "get_file_history",  # Correct - no prefix needed
    "get_recent_changes"
],
```

The SDK automatically handles the `mcp__<server_name>__` prefix internally.

## Verification

The MCP server creation is now working correctly:

```bash
python test_tools_fix.py
```

Output shows:
```
[OK] MCP server created successfully
  Server type: <class 'dict'>
  Server: {'type': 'sdk', 'name': 'obby-tools', 'instance': <mcp.server.lowlevel.server.Server object at 0x...>}
```

**Note:** Tools wrapped with `@tool` decorator become `SdkMcpTool` objects and can only be called through the Claude SDK, not directly. This is expected behavior.

## How to Test End-to-End

### Prerequisites
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"  # PowerShell
# OR
set ANTHROPIC_API_KEY=sk-ant-your-key-here     # CMD

# 3. Start backend
python backend.py
```

### Test with Chat API

```bash
# Test tool calling with Claude
curl -X POST http://localhost:8001/api/chat/complete \
  -H "Content-Type: application/json" \
  -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Show me recent file changes\"}], \"use_tools\": true}"
```

Expected response:
```json
{
  "reply": "Here are the recent file changes:\n\n[Claude's formatted response using the tools]",
  "model": "claude-3-5-sonnet",
  "finish_reason": "stop",
  "tools_used": true,
  "backend": "claude-agent-sdk"
}
```

## Key Learning: MCP Tool Format

When creating tools for Claude SDK with `@tool` decorator:

✅ **DO:**
```python
@tool("tool_name", "Description", {"param": type})
async def my_tool(args):
    result_text = "Some data"
    return {"content": [{"type": "text", "text": result_text}]}
```

❌ **DON'T:**
```python
@tool("tool_name", "Description", {"param": type})
async def my_tool(args):
    return {"data": "some value"}  # Wrong format!
```

## Files Changed

1. [ai/claude_agent_client.py](../ai/claude_agent_client.py#L270-L371) - Fixed tool implementations
2. [routes/chat.py](../routes/chat.py#L284-288) - Fixed tool registration
3. [test_tools_fix.py](../test_tools_fix.py) - New verification script

## Summary

The issue was **not** with the message type checking (that was already fixed in CLAUDE_SDK_FIX.md).

The real issue was:
1. ❌ Tools returning wrong format (plain dicts instead of `{"content": [...]}`
2. ❌ Tools using Flask-SQLAlchemy `.query` API that doesn't exist
3. ❌ Tool names in `allowed_tools` had incorrect `mcp__obby__` prefix

All three issues are now fixed and the MCP server creates successfully.
