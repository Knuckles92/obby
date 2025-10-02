# Claude Agent SDK Integration Guide for Obby

## Overview

This guide teaches you how to use the **Anthropic Claude Agent SDK** within your Obby project. The SDK provides agentic AI capabilities that complement your existing OpenAI integration.

## Installation

### Prerequisites

1. **Python 3.10+** (already satisfied by Obby)
2. **Node.js** (for Claude Code CLI)
3. **Claude Code CLI**:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

### Install the SDK

```bash
pip install claude-agent-sdk
```

### Set API Key

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Windows CMD
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

## Quick Start

### 1. Simple Query

```python
import asyncio
from claude_agent_sdk import query

async def main():
    async for message in query(prompt="What is 2 + 2?"):
        print(message)

asyncio.run(main())
```

### 2. Using Obby's ClaudeAgentClient

```python
import asyncio
from ai.claude_agent_client import ClaudeAgentClient

async def main():
    client = ClaudeAgentClient()
    
    # Analyze a diff
    diff = """
    + def new_feature(self):
    +     return "Hello"
    """
    
    analysis = await client.analyze_diff(diff)
    print(analysis)

asyncio.run(main())
```

## Key Features

### 1. **Diff Analysis**

Analyze code changes with context:

```python
client = ClaudeAgentClient()

analysis = await client.analyze_diff(
    diff_content="+ new code\n- old code",
    context="Added feature X to improve performance"
)
```

### 2. **Batch Change Summaries**

Summarize multiple file changes:

```python
changes = [
    {"path": "core/monitor.py", "type": "modified", "content": "Added monitoring"},
    {"path": "api/routes.py", "type": "modified", "content": "New endpoints"},
]

summary = await client.summarize_changes(changes, max_length="moderate")
```

### 3. **Interactive Sessions**

Multi-turn conversations with file access:

```python
async for response in client.interactive_analysis(
    initial_prompt="Review the batch_processor.py file",
    allow_file_edits=False
):
    print(response)
```

### 4. **Custom Tools (MCP Servers)**

Create tools that Claude can use:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("get_stats", "Get project statistics", {})
async def get_stats(args):
    return {
        "content": [{
            "type": "text",
            "text": "Project has 50 files, 10,000 lines"
        }]
    }

server = create_sdk_mcp_server(
    name="obby-stats",
    version="1.0.0",
    tools=[get_stats]
)
```

### 5. **Security Hooks**

Validate operations before execution:

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

async def validate_command(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    
    if "rm -rf" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked",
            }
        }
    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[validate_command]),
        ],
    }
)
```

## Integration with Obby

### Hybrid AI Workflow

Combine OpenAI's speed with Claude's agentic capabilities:

```python
from ai.openai_client import OpenAIClient
from ai.claude_agent_client import ClaudeAgentClient

# Step 1: Quick summary with OpenAI
openai_client = OpenAIClient()
quick_summary = openai_client.summarize_minimal(context)

# Step 2: Deep analysis with Claude
claude_client = ClaudeAgentClient()
deep_analysis = await claude_client.ask_question(
    f"Analyze these changes in detail: {quick_summary}"
)
```

### Custom Obby Tools

The SDK includes pre-built tools for Obby:

```python
from ai.claude_agent_client import create_obby_mcp_server
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

# Create MCP server with Obby tools
obby_server = create_obby_mcp_server()

options = ClaudeAgentOptions(
    mcp_servers={"obby": obby_server},
    allowed_tools=[
        "mcp__obby__get_file_history",
        "mcp__obby__get_recent_changes"
    ]
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Show me recent changes and their history")
    async for msg in client.receive_response():
        print(msg)
```

## Examples

Run the comprehensive examples:

```bash
cd "d:\Python Projects\obby"
python examples/claude_integration_example.py
```

This demonstrates:
1. ✅ Simple diff analysis
2. ✅ OpenAI vs Claude comparison
3. ✅ Interactive code review
4. ✅ Custom MCP tools
5. ✅ Hybrid AI workflows
6. ✅ Security hooks

## Configuration Options

### ClaudeAgentOptions

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    cwd="/path/to/project",              # Working directory
    allowed_tools=["Read", "Write"],     # Tools Claude can use
    permission_mode='acceptEdits',       # 'ask' or 'acceptEdits'
    max_turns=10,                        # Max conversation turns
    system_prompt="Custom instructions", # System prompt
)
```

### Available Built-in Tools

- **Read**: Read files from disk
- **Write**: Write/edit files
- **Bash**: Execute bash commands
- **List**: List directory contents

## Error Handling

```python
from claude_agent_sdk import (
    CLINotFoundError,
    CLIConnectionError,
    ProcessError,
    ClaudeSDKError,
)

try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print("Install Claude Code: npm install -g @anthropic-ai/claude-code")
except ProcessError as e:
    print(f"Process failed: {e.exit_code}")
except ClaudeSDKError as e:
    print(f"SDK error: {e}")
```

## Best Practices

### 1. **Use for Complex Tasks**
- Multi-step analysis
- Interactive debugging
- Code generation with validation

### 2. **Use OpenAI for Simple Tasks**
- Quick summaries
- Structured output
- High-volume batch processing

### 3. **Security First**
- Always use hooks for bash commands
- Limit allowed tools to minimum needed
- Use `permission_mode='ask'` for file edits

### 4. **Performance**
- Cache client instances
- Use appropriate `max_turns` limits
- Consider async batch processing

## Comparison: OpenAI vs Claude Agent SDK

| Feature | OpenAI Client | Claude Agent SDK |
|---------|---------------|------------------|
| **Speed** | ⚡ Fast | 🐢 Slower (agentic) |
| **Tool Use** | ❌ Manual | ✅ Automatic |
| **File Access** | ❌ No | ✅ Yes |
| **Interactive** | ❌ No | ✅ Yes |
| **Batch Processing** | ✅ Excellent | ⚠️ Limited |
| **Structured Output** | ✅ Excellent | ⚠️ Variable |
| **Cost** | 💰 Lower | 💰💰 Higher |

## Troubleshooting

### "Claude Code CLI not found"
```bash
npm install -g @anthropic-ai/claude-code
```

### "No ANTHROPIC_API_KEY"
```bash
# Set environment variable
export ANTHROPIC_API_KEY="your-key"
```

### "Module not found: claude_agent_sdk"
```bash
pip install claude-agent-sdk
```

### Timeout Issues
```python
# Increase max_turns if Claude needs more steps
options = ClaudeAgentOptions(max_turns=20)
```

## Advanced Topics

### Custom Tool Development

Create domain-specific tools:

```python
@tool("analyze_performance", "Analyze code performance", {"file_path": str})
async def analyze_performance(args):
    # Your custom logic here
    file_path = args['file_path']
    # ... analyze file ...
    return {
        "content": [{
            "type": "text",
            "text": f"Performance analysis for {file_path}: ..."
        }]
    }
```

### Multi-Agent Systems

Combine multiple AI clients:

```python
# Orchestrator pattern
async def orchestrate_analysis(changes):
    # Use OpenAI for categorization
    categories = openai_client.categorize(changes)
    
    # Use Claude for deep dive on each category
    for category in categories:
        analysis = await claude_client.analyze_category(category)
        yield analysis
```

## Resources

- **Official Docs**: https://docs.anthropic.com/en/docs/claude-code
- **SDK GitHub**: https://github.com/anthropics/claude-agent-sdk-python
- **Obby Examples**: `examples/claude_integration_example.py`
- **API Reference**: `ai/claude_agent_client.py`

## Next Steps

1. ✅ Install prerequisites
2. ✅ Set API key
3. ✅ Run examples
4. ✅ Integrate into BatchAIProcessor
5. ✅ Create custom tools for your workflow
6. ✅ Add security hooks
7. ✅ Monitor performance and costs

---

**Happy Coding with Claude! 🤖**
