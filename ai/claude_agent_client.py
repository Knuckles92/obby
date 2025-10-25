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

    @staticmethod
    def _is_structured_summary(text: str) -> bool:
        """Check if Claude's response matches the structured summary format."""
        if not text:
            return False

        required_markers = [
            "**Summary**:",
            "**Key Topics**:",
            "**Key Keywords**:",
            "**Overall Impact**:"
        ]

        if any(marker not in text for marker in required_markers):
            return False

        plan_indicators = [
            "i'll analyze",
            "i will analyze",
            "let me check",
            "let me start",
            "first, i will",
            "i'll start by",
            "i'll begin"
        ]

        lowered = text.lower()
        return not any(indicator in lowered for indicator in plan_indicators)

    @staticmethod
    def _build_fallback_summary(file_summaries: List[Dict], time_span: str) -> str:
        """Construct a deterministic fallback summary if the model fails to comply."""
        if not file_summaries:
            summary_line = f"No tracked file changes were detected in the monitored window ({time_span})."
            topics = "None"
            keywords = "None"
            impact = "brief"
        else:
            first_files = ", ".join(fs["file_path"] for fs in file_summaries[:3])
            if len(file_summaries) > 3:
                first_files += f", … {len(file_summaries) - 3} more"
            summary_line = (
                f"{len(file_summaries)} files changed during the {time_span} window. "
                f"Notable files: {first_files}."
            )

            highlight_snippets = [
                fs.get("highlights") for fs in file_summaries if fs.get("highlights")
            ]
            if highlight_snippets:
                key_updates = "; ".join(highlight_snippets[:2])
                summary_line += f" Key updates: {key_updates}."

            inferred_topics = ["Code Changes"]
            if highlight_snippets and any(
                term in snippet.lower()
                for snippet in highlight_snippets
                for term in ("doc", "readme", "guide", "note")
            ):
                inferred_topics.insert(0, "Documentation")
            topics = ", ".join(dict.fromkeys(inferred_topics)) if inferred_topics else "Code Changes"

            def _trim_snippet(snippet: str) -> str:
                snippet = snippet.strip().replace("\n", " ")
                return snippet if len(snippet) <= 60 else snippet[:57] + "..."

            keywords_list = [_trim_snippet(snippet) for snippet in highlight_snippets[:3]]
            keywords = ", ".join(keywords_list) if keywords_list else "code-change"
            impact = "moderate"

        return (
            f"**Summary**: {summary_line}\n\n"
            f"**Key Topics**: {topics}\n\n"
            f"**Key Keywords**: {keywords}\n\n"
            f"**Overall Impact**: {impact}"
        )

    async def _execute_summary_query(
        self,
        prompt: str,
        options: ClaudeAgentOptions
    ) -> str:
        """Execute a Claude query and collect all assistant/tool text blocks."""
        result: List[str] = []

        async for message in query(prompt=prompt, options=options):
            message_type = message.__class__.__name__
            logger.debug("Claude comprehensive summary stream: %s", message_type)

            content = getattr(message, "content", None)
            if not content:
                continue

            for block in content:
                block_text = getattr(block, "text", None)
                if block_text:
                    result.append(block_text)

        return "\n".join(result).strip()

    async def generate_comprehensive_summary(
        self,
        changes_context: str,
        file_summaries: List[Dict],
        time_span: str,
        summary_length: str = "brief"
    ) -> str:
        """
        Generate a comprehensive summary of file changes.

        Specialized method for comprehensive summary generation with
        structured output format.

        Args:
            changes_context: Combined diff and change context
            file_summaries: List of dicts with file-level summaries
            time_span: Human-readable time span (e.g., "2 days")
            summary_length: 'brief', 'moderate', or 'detailed'

        Returns:
            Structured summary text with topics, keywords, and impact
        """
        try:
            # Convert absolute paths to relative paths for Claude's Read tool
            def make_relative(path: str) -> str:
                """Convert absolute path to relative path from working directory."""
                try:
                    abs_path = Path(path)
                    if abs_path.is_absolute():
                        return str(abs_path.relative_to(self.working_dir))
                    return path
                except (ValueError, Exception):
                    # If path is not relative to working_dir, return as-is
                    return path
            
            # Build a concise file overview for the model to reference
            overview_entries: List[str] = []
            for fs in file_summaries[:20]:  # Allow up to 20 files
                relative_path = make_relative(fs['file_path'])
                highlight = (fs.get('highlights') or '').replace('\n', ' ').strip()
                highlight_segment = f" | Highlights: {highlight}" if highlight else ''
                overview_entries.append(f"- {relative_path}: {fs['summary']}{highlight_segment}")

            files_section = "\n".join(overview_entries)

            if len(file_summaries) > 20:
                files_section += f"\n- ... and {len(file_summaries) - 20} more files"

            if not files_section:
                files_section = "- None"

            # Trim diff context to keep prompt size manageable
            diff_context = changes_context or "(No diff context provided.)"
            if len(diff_context) > 3500:
                diff_context = diff_context[:3500] + "\n... (diff truncated for brevity)"

            # Determine length instruction to set expectations on summary depth
            length_instruction = {
                'brief': 'Write 1-2 tightly written sentences focusing on the most important themes.',
                'moderate': 'Write 2-3 sentences that capture the major themes, intent, and impact.',
                'detailed': 'Write 3-4 sentences covering themes, intent, impact, and follow-ups.'
            }.get(summary_length, 'Write 2-3 sentences that capture the major themes, intent, and impact.')

            # Build comprehensive prompt that encourages direct, structured output
            prompt = f"""You are a technical code analyst summarizing repository activity over the past {time_span}.
You must rely solely on the provided context; you cannot run commands, inspect the repository, or use external tools.
Return the final summary only—do not describe analysis steps or planned actions.
Do not preface your response with phrases like \"I'll analyze\" or \"Let me check\"; respond with the finished summary immediately.

	Follow this exact format:
	**Summary**: {length_instruction} Focus on what changed and why it matters, using the highlights below.
**Key Topics**: comma-separated high-level themes (3-5 items)
**Key Keywords**: comma-separated technical terms (up to 6 items)
**Overall Impact**: one word (brief, moderate, or significant)

Context to use:
	Files overview ({len(file_summaries)} total):
	{files_section}

	Diff excerpts:
	{diff_context}

	Use the highlights to describe the substantive modifications, naming new sections, behaviors, or documentation themes rather than just counting files.
	"""

            base_options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                allowed_tools=[],
                max_turns=1,
                system_prompt="You are a technical code analyst who delivers concise, structured summaries without planning narratives or tool usage. Always respond directly in the requested format."
            )

            response_text = await self._execute_summary_query(prompt, base_options)

            def _retry_prompt(base_prompt: str) -> str:
                return (
                    f"{base_prompt}\n\n"
                    "IMPORTANT: Previous reply did not comply. Provide the final structured summary now.\n"
                    "- Begin immediately with \"**Summary**:\" followed by the completed summary sentence(s).\n"
                    "- Do not include phrases like \"I'll analyze\" or describe planned actions.\n"
                    "- Fill in every required section.\n"
                )

            if not self._is_structured_summary(response_text):
                logger.warning("Claude summary response missing structure; retrying with stricter instructions.")
                strict_prompt = _retry_prompt(prompt)
                strict_options = ClaudeAgentOptions(
                    cwd=str(self.working_dir),
                    allowed_tools=[],
                    max_turns=1,
                    system_prompt="You must comply exactly with the requested output format. Do not mention planned actions. Respond only with the summary fields."
                )
                response_text = await self._execute_summary_query(strict_prompt, strict_options)

            if not self._is_structured_summary(response_text):
                logger.warning("Retry still missing structure; requesting final summary with direct instructions.")
                final_prompt = (
                    "**Summary**: (provide final summary sentence here)\n\n"
                    "**Key Topics**: (comma-separated topics)\n\n"
                    "**Key Keywords**: (comma-separated keywords)\n\n"
                    "**Overall Impact**: brief|moderate|significant\n\n"
                    "Fill in every placeholder using only the provided context. Do not include planning language."
                )
                final_options = ClaudeAgentOptions(
                    cwd=str(self.working_dir),
                    allowed_tools=[],
                    max_turns=1,
                    system_prompt="Respond exactly in the template supplied. Do not add explanatory text or planning statements."
                )
                response_text = await self._execute_summary_query(final_prompt, final_options)

            if not self._is_structured_summary(response_text):
                logger.error("Claude summary failed to comply after retry; using fallback summary.")
                response_text = self._build_fallback_summary(file_summaries, time_span)

            return response_text

        except Exception as e:
            logger.error(f"Error generating comprehensive summary: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Check if Claude Agent SDK is available and configured."""
        return CLAUDE_SDK_AVAILABLE and bool(self.api_key)


# Note: Custom MCP tools have been removed in favor of using Claude's built-in tools.
# Claude SDK comes with powerful built-in tools that can handle most operations:
#   - Read: Read file contents
#   - Write: Write to files
#   - Bash: Execute shell commands (can query SQLite databases directly)
#   - Grep: Search files
#   - Glob: File pattern matching
#   - Edit: Edit files
#
# For database queries, Claude can use the Bash tool to run sqlite3 commands directly.
# Example: Bash("sqlite3 obby.db 'SELECT * FROM file_changes LIMIT 10'")


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
