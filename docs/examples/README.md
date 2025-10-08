# Claude Agent SDK Examples

This directory contains educational examples demonstrating how to use the Claude Agent SDK. These are **learning examples** and are **not used by the production code**.

## Examples

- `01_basic_query.py` - Simple query example showing basic Claude SDK usage
- `02_streaming_response.py` - Demonstrates streaming responses from Claude
- `03_custom_tools.py` - Shows how to create custom tools for Claude
- `04_hooks.py` - Demonstrates validation and security hooks
- `05_error_handling.py` - Error handling patterns for Claude SDK
- `06_mcp_server.py` - MCP server integration example

## Purpose

These examples are kept for reference and learning purposes. They demonstrate patterns and techniques that can be useful when extending Obby's Claude integration, but they are not executed by the application.

## Production Code

For the actual Claude integration used in Obby, see:
- `ai/claude_agent_client.py` - Production Claude client wrapper
- `routes/chat.py` - Chat API with Claude integration

## Installation

These examples require the Claude Agent SDK:
```bash
pip install claude-agent-sdk
npm install -g @anthropic-ai/claude-code
```

Set your API key:
```bash
export ANTHROPIC_API_KEY=your_key_here  # Linux/Mac
set ANTHROPIC_API_KEY=your_key_here     # Windows
```

## Running Examples

```bash
python docs/examples/01_basic_query.py
```

