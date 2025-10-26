# Hybrid Chat Strategy: OpenAI + Claude

> **Legacy Warning:** Production now uses a Claude-only endpoint (`/api/chat/agent_query`). The notes below capture the original hybrid approach for archival purposes.

## Architecture Decision

**Use OpenAI for simple chat, Claude for tool-based chat**

### Reasoning

| Scenario | Best Choice | Why |
|----------|-------------|-----|
| Simple Q&A | OpenAI | Fast, cheap, good quality |
| Chat with tools | Claude | Automatic orchestration, no manual loops |

## Current vs Proposed

### Current (All OpenAI)
```
Simple Chat (use_tools=false):
  OpenAI → Response ✅ (Keep this)

Tool Chat (use_tools=true):
  OpenAI → Parse tool_calls → Execute → Add to messages → OpenAI again → ...
  ❌ 294 lines of orchestration code
  ❌ Manual parsing and execution
  ❌ Complex error handling
```

### Proposed (Hybrid)
```
Simple Chat (use_tools=false):
  OpenAI → Response ✅ (Keep this - no change)

Tool Chat (use_tools=true):
  Claude MCP → Automatic tool orchestration → Response ✅
  ✅ No orchestration code needed
  ✅ Automatic tool execution
  ✅ Built-in error handling
```

## Benefits

1. **Simplicity**: Remove 294 lines of orchestrator code
2. **Best of both**: Fast OpenAI for simple chat, powerful Claude for tools
3. **Cost-effective**: Only use Claude when tools are needed
4. **Better UX**: Claude's tool handling is more robust

## Implementation

### Step 1: Update chat endpoint

```python
# routes/chat.py

@chat_bp.post('/complete')
async def chat_with_history(request: Request):
    """Chat with messages history and optional tool calling."""
    try:
        data = await request.json()
        messages = data.get('messages')
        use_tools = data.get('use_tools', False)  # Default to false for backward compat
        
        if not isinstance(messages, list) or not messages:
            return JSONResponse({'error': 'messages must be a non-empty list'}, status_code=400)
        
        # Route based on tool usage
        if use_tools:
            # Use Claude for tool-based chat
            return await chat_with_claude_tools(messages, data)
        else:
            # Use OpenAI for simple chat (existing code)
            return await chat_with_openai(messages, data)
    
    except Exception as e:
        logger.error(f"/api/chat/agent_query failed: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


async def chat_with_openai(messages: List[Dict], data: Dict):
    """Simple chat with OpenAI (no tools)."""
    # Keep your existing code from lines 93-168
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
        return JSONResponse({'error': 'OpenAI client not configured'}, status_code=400)
    
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
        'tools_used': False
    }


async def chat_with_claude_tools(messages: List[Dict], data: Dict):
    """Tool-based chat with Claude Agent SDK."""
    from ai.claude_agent_client import create_obby_mcp_server
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
    
    # Get last user message
    user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
    if not user_message:
        return JSONResponse({'error': 'No user message found'}, status_code=400)
    
    # Build context from previous messages
    context_messages = [m for m in messages[:-1] if m['role'] in ('user', 'assistant')]
    if context_messages:
        context = "Previous conversation:\n"
        for msg in context_messages[-3:]:  # Last 3 messages for context
            context += f"{msg['role']}: {msg['content']}\n"
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
        system_prompt="You are a helpful assistant for the Obby file monitoring system. Use tools when needed to answer questions about files and changes."
    )
    
    try:
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
            'tools_used': True
        }
    
    except Exception as e:
        logger.error(f"Claude tool chat failed: {e}")
        # Fallback to OpenAI without tools
        logger.info("Falling back to OpenAI without tools")
        return await chat_with_openai(messages, data)
```

### Step 2: Remove AgentOrchestrator (Optional)

Once Claude is working, you can:
1. Keep `agent_orchestrator.py` as fallback
2. Or remove it entirely (294 lines deleted!)

### Step 3: Update frontend (if needed)

If your frontend explicitly sets `use_tools`, no changes needed.
If not, add a toggle or auto-detect when tools are needed.

## Cost Comparison

### Scenario 1: 100 chat messages/day

**Current (All OpenAI with orchestrator):**
- Simple chat: 50 messages × 1K tokens = 50K tokens = $1.50/day
- Tool chat: 50 messages × 3K tokens (multiple calls) = 150K tokens = $4.50/day
- **Total: $6/day = $180/month**

**Proposed (Hybrid):**
- Simple chat (OpenAI): 50 messages × 1K tokens = 50K tokens = $1.50/day
- Tool chat (Claude): 50 messages × 2K tokens = 100K tokens = $8/day
- **Total: $9.50/day = $285/month**

**Difference: +$105/month (+58%)**

**BUT:**
- ✅ 294 lines of code removed
- ✅ Better tool execution
- ✅ Less maintenance
- ✅ More reliable

### Cost Optimization

If cost is a concern, you can:
1. Default `use_tools=false` (most chat doesn't need tools)
2. Only enable tools when user explicitly requests file/change info
3. Add a "Use Tools" toggle in UI

## Migration Checklist

- [ ] Install Claude SDK: `pip install claude-agent-sdk`
- [ ] Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- [ ] Set `ANTHROPIC_API_KEY` environment variable
- [ ] Add `chat_with_claude_tools()` function to `routes/chat.py`
- [ ] Update `chat_with_history()` to route based on `use_tools`
- [ ] Test with tools enabled
- [ ] Test with tools disabled (should use OpenAI)
- [ ] Monitor costs and performance
- [ ] (Optional) Remove `agent_orchestrator.py`

## Testing

```bash
# Legacy hybrid test - simple chat (OpenAI path removed in production)
curl -X POST http://localhost:8000/api/chat/agent_query \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "use_tools": false
  }'

# Legacy hybrid test - tool chat (Claude)
curl -X POST http://localhost:8000/api/chat/agent_query \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What files changed recently?"}],
    "use_tools": true
  }'
```

## Rollback Plan

If Claude doesn't work well:
1. Keep the `if use_tools` check
2. Fall back to OpenAI + AgentOrchestrator
3. No data loss, just code revert

## Decision

✅ **Recommended: Implement hybrid approach**
- Simple chat → OpenAI (fast, cheap)
- Tool chat → Claude (automatic orchestration)
- Remove AgentOrchestrator once stable

This gives you the best of both worlds!
