# Claude Agent SDK Setup Guide

## Overview
The Obby chat system supports two backends for tool-based chat:
- **OpenAI Orchestrator** (default fallback): Uses OpenAI with manual tool orchestration
- **Claude Agent SDK** (preferred when configured): Uses Claude with automatic tool orchestration

## Requirements for Claude

### 1. Install Claude Code CLI
```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Install Python SDK
```bash
pip install claude-agent-sdk
```

### 3. Set API Key

**Recommended: Use .env file (easiest)**

Create a `.env` file in the project root (or copy from `.env.example`):
```bash
# Obby Environment Configuration

# OpenAI API Key
OPENAI_API_KEY=your-openai-key-here

# Anthropic API Key (for Claude)
ANTHROPIC_API_KEY=your-anthropic-key-here
```

The backend will automatically load this file on startup.

**Alternative: System Environment Variables**

If you prefer system-wide configuration:

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "your-api-key-here"
```

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```

**Linux/macOS:**
```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

**Note:** System environment variables require terminal restart to take effect.

## Getting an API Key
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy and set it as described above

## Fallback Behavior
If Claude is not configured or fails:
- The system automatically falls back to the OpenAI orchestrator
- You'll see a warning in the logs: `"ANTHROPIC_API_KEY not set. Falling back to OpenAI orchestrator."`
- Chat functionality continues to work with OpenAI tools

## Troubleshooting

### Error: "Claude CLI not found"
- Install the CLI: `npm install -g @anthropic-ai/claude-code`
- Verify installation: `npm list -g @anthropic-ai/claude-code`

### Error: "Failed to start Claude Code:"
- **Most common cause**: `ANTHROPIC_API_KEY` not set
- Check if key is set: `echo $env:ANTHROPIC_API_KEY` (PowerShell) or `echo $ANTHROPIC_API_KEY` (bash)
- Make sure to restart your terminal/backend after setting the key

### Claude SDK Import Errors
- Install the SDK: `pip install claude-agent-sdk`
- Check installation: `pip show claude-agent-sdk`

## Verifying Setup
After setting up, restart the backend and check the logs:
- ✅ Success: No errors related to Claude
- ⚠️ Warning: `"ANTHROPIC_API_KEY not set. Falling back to OpenAI orchestrator."`
- ❌ Error: Check the specific error message and follow troubleshooting steps above

## Current Status Check
You can check if Claude is available by calling:
```bash
curl http://localhost:8001/api/chat/tools
```

This will show:
- `claude_available: true/false` - Whether Claude SDK is installed and configured
- Available backends and their tools

