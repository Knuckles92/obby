# Claude Agent SDK Simplification

## What Changed (October 2025)

We simplified the Claude Agent SDK integration by removing custom MCP tools in favor of using Claude's powerful built-in tools.

## Before: Custom MCP Server ❌

Previously, we created custom MCP tools:
- `get_file_history` - Custom tool to query database
- `get_recent_changes` - Custom tool to query database
- `create_obby_mcp_server()` - Custom MCP server setup

**Problems:**
- Duplicate functionality (Grep vs NotesSearchTool)
- Extra complexity maintaining custom tools
- Limited to what we explicitly programmed

## After: Built-in Tools Only ✅

Now we just use Claude's built-in tools:
- **`Read`** - Read any file
- **`Write`** - Write to files
- **`Bash`** - Execute shell commands (including SQLite queries!)
- **`Grep`** - Search files (replaces our custom search)
- **`Glob`** - File pattern matching
- **`Edit`** - Edit files

**Benefits:**
- Much simpler configuration
- More powerful (Bash can do anything)
- No custom code to maintain
- Claude automatically decides which tools to use

## How Claude Queries the Database Now

Instead of custom tools, Claude uses the **Bash** tool:

```python
# Old way (custom tool):
mcp__obby__get_file_history(file_path="notes/example.md")

# New way (built-in Bash tool):
Bash("sqlite3 obby.db \"SELECT * FROM file_changes WHERE file_path='notes/example.md' ORDER BY timestamp DESC LIMIT 10\"")
```

Claude is smart enough to:
1. Understand you want database info
2. Use the Bash tool
3. Run sqlite3 commands
4. Parse and present the results

## Example Chat Interactions

### Query Recent Changes
```
User: "What are the 10 most recent file changes?"

Claude automatically:
1. Uses Bash: sqlite3 obby.db "SELECT * FROM file_changes ORDER BY timestamp DESC LIMIT 10"
2. Parses results
3. Presents formatted output
```

### Search Notes
```
User: "Find all mentions of 'potato' in my notes"

Claude automatically:
1. Uses Grep: grep -r "potato" notes/
2. Formats results
3. Can even Read specific files for more context
```

### Complex Multi-Tool Tasks
```
User: "Show me what changed in the last hour and read the most recent file"

Claude automatically:
1. Uses Bash to query database for recent changes
2. Uses Read to get file contents
3. Combines information into coherent response
```

## Code Changes

### routes/chat.py
- Removed `create_obby_mcp_server()` import
- Removed `mcp_servers` from `ClaudeAgentOptions`
- Changed `allowed_tools` to only built-in tools
- Updated system prompt to mention database location

### ai/claude_agent_client.py
- Removed `@tool` decorator imports
- Removed `get_file_history()` function
- Removed `get_recent_changes()` function
- Removed `create_obby_mcp_server()` function
- Added comment explaining built-in tools

## When to Use Custom Tools

You should only create custom MCP tools when:
1. You need complex Python logic that can't be done in bash
2. You need authentication/security wrappers
3. You need to integrate with external APIs
4. You want to abstract complex operations

For file operations, database queries, and system commands, **built-in tools are always better**.

## Configuration

```python
# Current Claude configuration (routes/chat.py)
options = ClaudeAgentOptions(
    cwd=str(Path.cwd()),
    allowed_tools=[
        "Read",      # Read file contents
        "Write",     # Write to files
        "Bash",      # Execute bash/shell commands
        "Grep",      # Search files (like ripgrep)
        "Glob",      # File pattern matching
        "Edit",      # Edit files
    ],
    max_turns=10,
    system_prompt="You are a helpful assistant for the Obby file monitoring system. You have access to the file system and can read files, search for content, run commands, and explore the project structure. The database is at obby.db (SQLite)."
)
```

## Future Considerations

If you ever need custom tools again, ask yourself:
1. Can the Bash tool do this?
2. Can I combine Read/Write/Grep to achieve this?
3. Is this truly unique logic that requires a custom tool?

In most cases, the answer is: **Claude's built-in tools can handle it!**

