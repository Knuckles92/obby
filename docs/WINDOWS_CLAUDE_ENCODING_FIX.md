# Windows Claude CLI Encoding Fix

## Problem

When running the Obby backend on Windows with Claude Agent SDK integration, you may encounter the following errors:

```
ERROR:routes.chat:Claude CLI connection error: Failed to start Claude Code: 
UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 157: character maps to <undefined>
ERROR:ai.agent_orchestrator:Notes search failed: 'NoneType' object has no attribute 'strip'
```

## Root Cause

The Claude Agent SDK spawns the Claude CLI as a subprocess to communicate with Claude's API. On Windows, Python's subprocess module defaults to using the system's code page (typically CP1252) for decoding subprocess output. However, the Claude CLI may output UTF-8 encoded text, which can contain bytes that are invalid in CP1252, causing a `UnicodeDecodeError`.

This issue has two cascading effects:
1. The Claude CLI connection fails due to encoding errors
2. When tools like notes_search try to process the failed output (which is `None`), they crash with `'NoneType' object has no attribute 'strip'`

## Solution

We've implemented multiple layers of fixes to handle this issue:

### 1. **Global UTF-8 Environment Setup** (`backend.py`)

At startup, we configure the Python environment to use UTF-8 encoding for all subprocess communication:

```python
if sys.platform == 'win32':
    # Force UTF-8 encoding for subprocess communication
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Set console code page to UTF-8 if possible
    try:
        import subprocess as _sp
        _sp.run(['chcp', '65001'], shell=True, capture_output=True, check=False)
    except Exception:
        pass  # Silently fail if chcp doesn't work
```

This ensures that:
- `PYTHONIOENCODING=utf-8` tells Python to use UTF-8 for subprocess I/O
- Code page 65001 (UTF-8) is set for the Windows console
- The system will log encoding configuration for debugging

### 2. **Explicit UTF-8 in subprocess calls** (`ai/ai_tooling.py`)

The notes search tool now explicitly specifies UTF-8 encoding with error handling:

```python
completed = subprocess.run(
    command,
    cwd=str(self.notes_dir),
    capture_output=True,
    text=True,
    encoding='utf-8',  # Explicitly specify UTF-8 encoding
    errors='replace',  # Replace invalid chars instead of crashing
)

# Handle None output gracefully
stdout = (completed.stdout or "").strip()
stderr = (completed.stderr or "").strip()
```

This prevents `NoneType` errors when subprocess output is None due to encoding failures.

### 3. **Improved Error Handling** (`ai/agent_orchestrator.py`)

The agent orchestrator now validates tool results before processing:

```python
if result and hasattr(result, 'format_for_agent'):
    return result.format_for_agent()
else:
    logger.error("Notes search returned invalid result")
    return "Error: Notes search returned an invalid result"
```

### 4. **Better Error Messages** (`routes/chat.py`)

Claude connection errors are now logged with helpful context:

```python
except CLIConnectionError as e:
    error_msg = str(e)
    logger.error(f"Claude CLI connection error: {error_msg}")
    
    # Check if it's an encoding error
    if 'UnicodeDecodeError' in error_msg or 'charmap' in error_msg:
        logger.warning("Claude CLI encountered encoding issues on Windows. Consider upgrading claude-agent-sdk.")
    
    logger.info("Falling back to OpenAI orchestrator")
    return await _chat_with_openai_tools(messages, data)
```

## Fallback Behavior

When Claude fails due to encoding or other issues, the system **automatically falls back to the OpenAI orchestrator**, ensuring that tool-based chat continues to work without user intervention.

## Testing

After implementing these fixes:

1. **Restart the backend** to apply the encoding configuration:
   ```bash
   python backend.py
   ```

2. **Check the startup logs** for encoding confirmation:
   ```
   INFO:__main__:Windows platform detected - PYTHONIOENCODING: utf-8
   INFO:__main__:Default encoding: utf-8, stdout encoding: utf-8
   ```

3. **Test tool-based chat** through the frontend or API:
   ```json
   POST /api/chat/complete
   {
     "messages": [{"role": "user", "content": "Search my notes for 'test'"}],
     "use_tools": true
   }
   ```

4. **Check logs** for successful fallback if Claude still fails:
   ```
   INFO:routes.chat:Using Claude Agent SDK for tool-based chat
   ERROR:routes.chat:Claude CLI connection error: ...
   INFO:routes.chat:Falling back to OpenAI orchestrator
   INFO:routes.chat:Using OpenAI orchestrator for tool-based chat
   ```

## Known Limitations

1. **Claude SDK Limitation**: The underlying `claude-agent-sdk` package may still have encoding issues if it doesn't respect the `PYTHONIOENCODING` environment variable. This is a known issue with some Python packages on Windows.

2. **Workaround**: If Claude continues to fail, the system will use the OpenAI orchestrator as a fallback. This provides the same functionality (tool calling, notes search, etc.) but uses OpenAI's API instead of Claude.

3. **Future Fix**: When the `claude-agent-sdk` package is updated to properly handle Windows encoding, these workarounds may no longer be necessary.

## Alternatives

If you continue to experience issues with Claude on Windows, consider:

1. **Use WSL2** (Windows Subsystem for Linux): Run the backend in WSL2 where encoding is handled properly
2. **Disable Claude**: Set only `OPENAI_API_KEY` and remove `ANTHROPIC_API_KEY` to use OpenAI exclusively
3. **Use Docker**: Run the backend in a Docker container with proper UTF-8 locale

## Related Files

- `backend.py` - Global encoding setup and logging
- `ai/ai_tooling.py` - Notes search tool with explicit UTF-8 encoding
- `ai/agent_orchestrator.py` - Improved error handling for tool execution
- `routes/chat.py` - Fallback logic and error detection



