"""
Claude Agent SDK Integration for Obby
======================================

Provides agentic AI capabilities using Anthropic's Claude Agent SDK.
Complements OpenAIClient with tool-calling and interactive conversation features.
"""

import os
import logging
import asyncio
from typing import Optional, List, Dict, Any, AsyncIterator
from pathlib import Path

try:
    from claude_agent_sdk import (
        query,
        ClaudeSDKClient,
        ClaudeAgentOptions,
        tool,
        create_sdk_mcp_server,
        AssistantMessage,
        TextBlock,
        CLINotFoundError,
        CLIConnectionError,
        ProcessError,
        ClaudeSDKError,
    )
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.warning("claude-agent-sdk not installed. Run: pip install claude-agent-sdk")

logger = logging.getLogger(__name__)


class ClaudeAgentClient:
    """
    Wrapper for Claude Agent SDK tailored for Obby's code analysis needs.
    
    Features:
    - Simple queries for code analysis
    - Custom tools for file operations
    - Interactive conversations for complex tasks
    - Hooks for validation and security
    """
    
    def __init__(self, api_key: Optional[str] = None, working_dir: Optional[Path] = None):
        """
        Initialize Claude Agent Client.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            working_dir: Working directory for file operations (defaults to current dir)
        """
        if not CLAUDE_SDK_AVAILABLE:
            raise ImportError(
                "claude-agent-sdk is required. Install with: pip install claude-agent-sdk\n"
                "Also requires: npm install -g @anthropic-ai/claude-code"
            )
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.working_dir = working_dir or Path.cwd()
        
        if not self.api_key:
            logger.warning("No ANTHROPIC_API_KEY found. Set it via environment variable.")
        
        # Create default options
        self.default_options = ClaudeAgentOptions(
            cwd=str(self.working_dir),
            allowed_tools=["Read"],  # Safe default: only allow reading files
            max_turns=10,
        )
        
        logger.info(f"Claude Agent Client initialized (working_dir={self.working_dir})")
    
    async def analyze_diff(self, diff_content: str, context: Optional[str] = None) -> str:
        """
        Analyze a code diff using Claude Agent SDK.
        
        Args:
            diff_content: The diff content to analyze
            context: Optional additional context (e.g., recent changes)
        
        Returns:
            AI-generated analysis of the diff
        """
        try:
            prompt = f"Analyze this code diff and provide a concise summary:\n\n{diff_content}"
            
            if context:
                prompt += f"\n\nAdditional context:\n{context}"
            
            options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                allowed_tools=["Read"],
                max_turns=3,
                system_prompt="You are a code analysis assistant. Provide concise, technical summaries."
            )
            
            result = []
            async for message in query(prompt=prompt, options=options):
                message_type = message.__class__.__name__
                
                if message_type == "AssistantMessage":
                    # Extract text from message content
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                result.append(block.text)
            
            return "\n".join(result) if result else "No analysis generated."
        
        except CLINotFoundError:
            logger.error("Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code")
            return "Error: Claude Code CLI not installed"
        except Exception as e:
            logger.error(f"Error analyzing diff: {e}", exc_info=True)
            return f"Error analyzing diff: {str(e)}"
    
    async def summarize_changes(
        self, 
        changes: List[Dict[str, Any]], 
        max_length: str = "moderate"
    ) -> str:
        """
        Summarize multiple file changes in batch.
        
        Args:
            changes: List of change dicts with 'path', 'type', 'content' keys
            max_length: 'brief', 'moderate', or 'detailed'
        
        Returns:
            Consolidated summary of all changes
        """
        try:
            # Build context from changes
            context_parts = []
            for change in changes[:10]:  # Limit to 10 changes to avoid token limits
                path = change.get('path', 'unknown')
                change_type = change.get('type', 'modified')
                content = change.get('content', '')[:500]  # Truncate long content
                
                context_parts.append(f"File: {path} ({change_type})\n{content}\n")
            
            context = "\n---\n".join(context_parts)
            
            length_instructions = {
                'brief': "Provide 1-3 bullet points.",
                'moderate': "Provide 3-5 bullet points with key details.",
                'detailed': "Provide a comprehensive analysis with multiple sections."
            }
            
            prompt = (
                f"Summarize these code changes. {length_instructions.get(max_length, '')}:\n\n"
                f"{context}"
            )
            
            options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                allowed_tools=["Read"],
                max_turns=2,
            )
            
            result = []
            async for message in query(prompt=prompt, options=options):
                message_type = message.__class__.__name__
                
                if message_type == "AssistantMessage":
                    # Extract text from message content
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                result.append(block.text)
            
            return "\n".join(result) if result else "No summary generated."
        
        except Exception as e:
            logger.error(f"Error summarizing changes: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def interactive_analysis(
        self,
        initial_prompt: str,
        allow_file_edits: bool = False
    ) -> AsyncIterator[str]:
        """
        Start an interactive analysis session with Claude.
        
        Args:
            initial_prompt: The initial query/task
            allow_file_edits: Whether to allow Claude to edit files
        
        Yields:
            Messages from Claude as they arrive
        """
        try:
            tools = ["Read", "Bash"]
            if allow_file_edits:
                tools.append("Write")
            
            options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                allowed_tools=tools,
                permission_mode='acceptEdits' if allow_file_edits else 'ask',
                max_turns=20,
            )
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(initial_prompt)
                
                async for message in client.receive_response():
                    message_type = message.__class__.__name__
                    
                    if message_type == "AssistantMessage":
                        # Extract text from message content
                        if hasattr(message, 'content'):
                            for block in message.content:
                                if hasattr(block, 'text'):
                                    yield block.text
        
        except Exception as e:
            logger.error(f"Error in interactive analysis: {e}", exc_info=True)
            yield f"Error: {str(e)}"
    
    async def ask_question(self, question: str, context: Optional[str] = None) -> str:
        """
        Ask a simple question about the codebase.
        
        Args:
            question: The question to ask
            context: Optional context to provide
        
        Returns:
            Claude's response
        """
        try:
            prompt = question
            if context:
                prompt = f"Context:\n{context}\n\nQuestion: {question}"
            
            options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                allowed_tools=["Read"],
                max_turns=3,
            )
            
            result = []
            async for message in query(prompt=prompt, options=options):
                message_type = message.__class__.__name__
                
                if message_type == "AssistantMessage":
                    # Extract text from message content
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                result.append(block.text)
            
            return "\n".join(result) if result else "No response generated."
        
        except Exception as e:
            logger.error(f"Error asking question: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Claude Agent SDK is available and configured."""
        return CLAUDE_SDK_AVAILABLE and bool(self.api_key)


# Custom tools for Obby-specific operations using the @tool decorator
# These must return {"content": [{"type": "text", "text": "..."}]} format
@tool("get_file_history", "Get the change history for a specific file", {"file_path": str})
async def get_file_history(args):
    """Tool to retrieve file change history from Obby database."""
    import json

    try:
        from database.connection import DatabaseConnection

        file_path = args.get('file_path')
        if not file_path:
            return {"content": [{"type": "text", "text": "Error: file_path is required"}]}

        # Query last 10 changes for this file using direct SQL
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

        if not changes:
            text = f"No change history found for {file_path}"
            return {"content": [{"type": "text", "text": text}]}

        # Format as readable text
        lines = [f"Change history for {file_path}:\n"]
        for timestamp, event_type, path in changes:
            lines.append(f"- {timestamp}: {event_type}")

        text = "\n".join(lines)
        return {"content": [{"type": "text", "text": text}]}

    except Exception as e:
        logger.error(f"Error in get_file_history tool: {e}", exc_info=True)
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool("get_recent_changes", "Get recent file changes across the project", {"limit": int})
async def get_recent_changes(args):
    """Tool to retrieve recent changes from Obby database."""
    import json

    try:
        from database.connection import DatabaseConnection

        limit = args.get('limit', 10)
        # Ensure limit is reasonable
        limit = max(1, min(int(limit), 50))  # Between 1 and 50

        # Query recent changes using direct SQL
        db = DatabaseConnection()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, event_type, file_path
                FROM file_changes
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            changes = cursor.fetchall()

        if not changes:
            return {"content": [{"type": "text", "text": "No recent changes found"}]}

        # Format as readable text
        lines = [f"Recent {len(changes)} changes:\n"]
        for timestamp, event_type, path in changes:
            lines.append(f"- {path}: {event_type} at {timestamp}")

        text = "\n".join(lines)
        return {"content": [{"type": "text", "text": text}]}

    except Exception as e:
        logger.error(f"Error in get_recent_changes tool: {e}", exc_info=True)
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


def create_obby_mcp_server():
    """
    Create an MCP server with Obby-specific tools.

    Returns:
        MCP server configuration for Claude SDK
    """
    if not CLAUDE_SDK_AVAILABLE:
        raise ImportError("claude-agent-sdk required")

    # Create SDK MCP server with the decorated tools
    return create_sdk_mcp_server(
        name="obby-tools",
        version="1.0.0",
        tools=[get_file_history, get_recent_changes]
    )


# Example usage function
async def example_usage():
    """Example demonstrating Claude Agent SDK integration with Obby."""
    
    # Initialize client
    client = ClaudeAgentClient(working_dir=Path.cwd())
    
    if not client.is_available():
        print("Claude Agent SDK not available. Check API key and installation.")
        return
    
    # Example 1: Simple diff analysis
    print("=== Example 1: Diff Analysis ===")
    sample_diff = """
    + def new_feature(self):
    +     return "Hello World"
    - def old_feature(self):
    -     return "Goodbye"
    """
    
    analysis = await client.analyze_diff(sample_diff)
    print(f"Analysis: {analysis}\n")
    
    # Example 2: Batch change summary
    print("=== Example 2: Batch Summary ===")
    changes = [
        {"path": "core/monitor.py", "type": "modified", "content": "Added new monitoring feature"},
        {"path": "api/routes.py", "type": "modified", "content": "Updated API endpoints"},
    ]
    
    summary = await client.summarize_changes(changes, max_length="brief")
    print(f"Summary: {summary}\n")
    
    # Example 3: Ask a question
    print("=== Example 3: Q&A ===")
    answer = await client.ask_question(
        "What are the main components of this project?",
        context="This is the Obby project - a file monitoring and AI analysis system."
    )
    print(f"Answer: {answer}\n")


if __name__ == "__main__":
    # Run examples
    asyncio.run(example_usage())
