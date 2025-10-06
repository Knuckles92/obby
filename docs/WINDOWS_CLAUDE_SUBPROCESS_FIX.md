# Windows Claude SDK Subprocess Fix

## Problem

When running the Obby backend on Windows with Claude Agent SDK integration, you encounter:

```
ERROR:routes.chat:❌ CLIConnectionError after 0.05s
ERROR:routes.chat:   Error: Failed to start Claude Code: 
ERROR:routes.chat:   ⚠️  Windows asyncio subprocess issue detected
```

Even though `WindowsProactorEventLoopPolicy` is set at the top of `backend.py`, the error still occurs.

## Root Cause

The issue is with **uvicorn's reloader** on Windows. When uvicorn runs with `reload=True`, it:
1. Creates a parent process that watches for file changes
2. Spawns child worker processes to handle requests
3. These child processes may not properly inherit the event loop policy

The Claude Agent SDK requires spawning subprocesses to communicate with the Claude CLI (`@anthropic-ai/claude-code`). On Windows, this REQUIRES the `ProactorEventLoop`, but uvicorn's default loop implementation might be using `SelectorEventLoop` instead.

## Solution

### Fix 1: Explicitly Specify Loop Implementation (`backend.py`)

```python
uvicorn_config = {
    'app': 'backend:app',
    'host': '0.0.0.0',
    'port': 8001,
    'reload': True,
}

# On Windows, explicitly specify loop implementation for subprocess support
if sys.platform == 'win32':
    uvicorn_config['loop'] = 'asyncio'  # Use asyncio (with our ProactorEventLoopPolicy)
    logger.info('Using asyncio loop with WindowsProactorEventLoopPolicy for Claude SDK support')

uvicorn.run(**uvicorn_config)
```

This tells uvicorn to use the `asyncio` loop implementation, which will respect the `WindowsProactorEventLoopPolicy` we set at the top of the file.

### Fix 2: Loop Type Detection (`routes/chat.py`)

Added detection to check if the running loop is the correct type:

```python
loop = asyncio.get_running_loop()
loop_type = type(loop).__name__

if sys.platform == 'win32' and loop_type != 'ProactorEventLoop':
    logger.error(f"❌ Wrong loop type on Windows: {loop_type} (need ProactorEventLoop)")
    return JSONResponse({
        'error': f'Windows subprocess not supported with {loop_type}. Run backend.py without --reload'
    }, status_code=500)
```

## Testing

1. **Stop the current backend** (Ctrl+C in the terminal)

2. **Restart the backend completely**:
   ```powershell
   python backend.py
   ```

3. **Check startup logs** for confirmation:
   ```
   🪟 [STARTUP] Windows: Set WindowsProactorEventLoopPolicy for Claude SDK subprocess support
   INFO:__main__:Using asyncio loop with WindowsProactorEventLoopPolicy for Claude SDK support
   INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
   ```

4. **Test Claude chat** through the frontend or API:
   ```powershell
   # From another terminal
   curl -X POST http://localhost:8001/api/chat/complete `
     -H "Content-Type: application/json" `
     -d '{"messages": [{"role": "user", "content": "What files are in the notes directory?"}], "provider": "claude"}'
   ```

5. **Check logs** for successful Claude connection:
   ```
   INFO:routes.chat:🔍 Current event loop policy: WindowsProactorEventLoopPolicy
   INFO:routes.chat:🔍 Current running loop: ProactorEventLoop
   INFO:routes.chat:✓ Claude API Key found: sk-ant-a...
   INFO:routes.chat:🚀 Starting Claude SDK client...
   INFO:routes.chat:✓ Claude SDK client initialized
   ```

## Alternative Solutions

If the issue persists:

### Option 1: Run without reload
```python
# In backend.py, change:
uvicorn.run('backend:app', host='0.0.0.0', port=8001, reload=False)
```

### Option 2: Use WSL2
Run the backend in Windows Subsystem for Linux where asyncio subprocess support is native.

### Option 3: Use Docker
Run in a Docker container with proper Linux environment.

### Option 4: Fallback to OpenAI
The chat API automatically falls back to OpenAI orchestrator if Claude fails, providing the same tool-calling functionality.

## Technical Details

### Why ProactorEventLoop?

On Windows, Python's asyncio has two event loop implementations:
- **SelectorEventLoop** (default): Uses select() for I/O multiplexing, doesn't support subprocesses
- **ProactorEventLoop**: Uses Windows I/O Completion Ports (IOCP), supports subprocesses

The Claude SDK spawns the Claude CLI as a subprocess, requiring ProactorEventLoop.

### Why uvicorn's loop parameter?

Uvicorn supports different loop implementations:
- `uvloop` (Unix only, fastest)
- `asyncio` (cross-platform, uses Python's default policy)
- `auto` (default, tries uvloop first, falls back to asyncio)

By explicitly setting `loop='asyncio'`, we ensure uvicorn uses Python's asyncio with our custom policy.

## Verification

After restart, the logs should show:
```
INFO:routes.chat:🔍 Current event loop policy: WindowsProactorEventLoopPolicy
INFO:routes.chat:🔍 Current running loop: ProactorEventLoop
```

If you see `SelectorEventLoop` instead, the fix hasn't taken effect and you may need to use one of the alternative solutions.

## Related Files

- `backend.py` - Event loop policy setup and uvicorn configuration
- `routes/chat.py` - Loop type detection and Claude SDK client initialization
- `docs/WINDOWS_CLAUDE_ENCODING_FIX.md` - Related encoding issues
- `docs/CLAUDE_SDK_FIX.md` - General Claude SDK integration fixes


