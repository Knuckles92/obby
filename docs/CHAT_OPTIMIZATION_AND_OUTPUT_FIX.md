# Chat Optimization and Output Fix

## Overview
This document describes the optimizations made to the chat system to improve efficiency and fix the multi-tool output display issue.

## Problems Addressed

### 1. Generic System Prompt
**Issue:** The chat system prompt was too generic and didn't provide context about Obby or guide efficient tool usage.

**Solution:** Updated the system prompt in `frontend/src/pages/Chat.tsx` to:
- Provide context about Obby (file monitoring, SQLite database, semantic search)
- List available tools explicitly
- Set clear guidelines for concise, direct responses
- Instruct the AI to avoid announcing tool actions
- Focus on synthesizing results efficiently

### 2. Multi-Tool Output Display
**Issue:** When the agent made 7-8 tool calls, every intermediate assistant message was displayed in the chat window, cluttering the conversation with messages like "Let me search...", "Now checking...", etc.

**Solution:** Implemented a clean separation between chat display and agent activity:

#### Backend Changes (`routes/chat.py`)
- Modified `sanitized_conversation` logic to only include:
  - All user messages
  - All system messages
  - **Only the FINAL assistant response**
- Intermediate assistant messages are now tracked separately in `agent_actions`
- Added new event type `assistant_thinking` to capture intermediate assistant reasoning

#### Agent Orchestrator Changes (`ai/agent_orchestrator.py`)
- Added emission of `assistant_thinking` event when the agent has tool calls with content
- This captures the agent's reasoning before executing tools
- Removed redundant `assistant_content` field from tool_call events

#### Frontend Changes (`frontend/src/pages/Chat.tsx`)
- Added `assistant_thinking` as a new `AgentActionType`
- Styled assistant thinking events with purple color scheme
- Label displayed as "reasoning" or "Agent planning (N tools)" in activity panel
- All intermediate messages now appear only in the "Agent Activity" panel

## Results

### Before
**Chat Window:**
```
User: What files mention authentication?
Assistant: Let me search for authentication mentions...
Assistant: Now let me check the configuration files...
Assistant: I found several mentions, let me analyze them...
Assistant: Based on my search, I found authentication mentioned in...
```
(4 messages cluttering the chat)

**Agent Activity:**
- Tool calls and results visible
- Intermediate messages duplicated in chat

### After
**Chat Window:**
```
User: What files mention authentication?
Assistant: Based on my search, I found authentication mentioned in...
```
(Clean, single response)

**Agent Activity:**
- "Agent planning (1 tool)" - Shows reasoning with content
- "Calling notes_search" - Tool execution
- "notes_search result" - Tool result
- All intermediate steps visible here only

## Technical Details

### System Prompt Update
Location: `frontend/src/pages/Chat.tsx`, `useEffect` hook

```typescript
content: `You are an AI assistant for Obby, a file monitoring and note management system.

Context: Obby tracks file changes in a local repository, stores content in SQLite (obby.db), 
and provides semantic search through AI-analyzed notes. The notes directory contains 
documentation and tracked files.

Tools available:
- notes_search: Search through notes and documentation with grep/ripgrep

Guidelines:
- Be concise and direct in responses
- When using tools, proceed without announcing your actions
- Synthesize results rather than listing raw data
- Focus on answering the user's question efficiently`
```

### Conversation Sanitization Logic
Location: `routes/chat.py`, `_chat_with_openai_tools` function

```python
# Only include user/system messages and the FINAL assistant response in chat
sanitized_conversation: List[Dict[str, Any]] = []
for message in full_conversation:
    role = message.get('role')
    
    # Skip tool messages - they're in agent_actions
    if role == 'tool':
        continue
    
    # Include user and system messages
    if role in ('user', 'system'):
        sanitized_conversation.append(dict(message))

# Add only the FINAL assistant response
if reply:
    sanitized_conversation.append({
        'role': 'assistant',
        'content': reply
    })
```

### Agent Event Recording
Location: `routes/chat.py`, `record_agent_event` function

Added handling for `assistant_thinking` event type:

```python
if event_type == "assistant_thinking":
    # Capture intermediate assistant messages that introduce tool calls
    content = payload.get("content", "")
    if content.strip():
        action["label"] = "Agent reasoning"
        action["detail"] = content[:500]  # Truncate long messages
        tool_count = payload.get("tool_count", 0)
        if tool_count:
            action["label"] = f"Agent planning ({tool_count} tool{'s' if tool_count > 1 else ''})"
```

### Event Emission in Orchestrator
Location: `ai/agent_orchestrator.py`, `execute_chat_with_tools` function

```python
if tool_calls:
    # Record intermediate assistant reasoning if present
    if on_agent_event and (message.content or "").strip():
        on_agent_event("assistant_thinking", {
            "content": message.content,
            "tool_count": len(tool_calls)
        })
```

## Benefits

1. **Cleaner Chat Interface**
   - Users see only the conversation flow (user questions + final answers)
   - No clutter from intermediate tool-calling messages
   - Professional, focused user experience

2. **Comprehensive Agent Activity Panel**
   - Developers and power users can see all internal operations
   - Reasoning steps are preserved and visible
   - Tool calls and results are tracked separately
   - Purple-colored "reasoning" entries distinguish assistant thinking from tool operations

3. **Better Prompt Engineering**
   - Context-aware system prompt reduces unnecessary explanations
   - Guidelines encourage concise, direct responses
   - AI understands it doesn't need to announce tool usage
   - Faster, more efficient conversations

4. **Maintained Transparency**
   - Full conversation history preserved in `raw_conversation`
   - Agent activity shows all steps taken
   - Debugging and monitoring capabilities retained

## Files Modified

1. `frontend/src/pages/Chat.tsx`
   - Updated system prompt
   - Added `assistant_thinking` event type
   - Added styling for reasoning events
   - Updated event type handling

2. `routes/chat.py`
   - Modified sanitized_conversation logic
   - Added assistant_thinking event type handling
   - Enhanced record_agent_event function

3. `ai/agent_orchestrator.py`
   - Added emission of assistant_thinking events
   - Cleaned up tool_call event payload

## Testing Recommendations

1. **Single Tool Call Test**
   - Ask: "Search for 'database' in the notes"
   - Verify chat shows only final response
   - Verify agent activity shows: reasoning → tool call → tool result

2. **Multiple Tool Calls Test**
   - Ask a complex query that triggers multiple searches
   - Verify chat doesn't show intermediate "Let me search..." messages
   - Verify all tool operations appear in agent activity panel

3. **No Tool Call Test**
   - Ask: "What is Obby?"
   - Verify direct response without tool usage
   - Verify response is concise and contextual

4. **Error Handling Test**
   - Trigger a tool error
   - Verify error appears in agent activity
   - Verify chat shows appropriate error message

## Future Enhancements

1. **Collapsible Reasoning Entries**
   - Allow users to collapse/expand assistant thinking details
   - Reduce visual clutter while maintaining transparency

2. **Token Usage Tracking**
   - Track tokens saved by optimized prompt
   - Display efficiency metrics in agent activity

3. **Customizable System Prompt**
   - Allow users to customize the system prompt
   - Provide templates for different use cases

4. **Activity Export**
   - Export agent activity logs for analysis
   - Generate performance reports

## Conclusion

These changes significantly improve the chat user experience by separating user-facing conversation from internal agent operations. The optimized system prompt reduces unnecessary verbosity, while the enhanced agent activity panel maintains full transparency for debugging and monitoring.

The result is a more professional, efficient chat interface that's easier to use while still providing complete visibility into agent operations when needed.
