"""
Claude Agent SDK Integration for Obby
======================================

Provides agentic AI capabilities using Anthropic's Claude Agent SDK.

IMPORTANT: File access is restricted to watch directories configured in .obbywatch.
The agent will only operate within these boundaries for security and focus.
"""

import os
import logging
import asyncio
import uuid
from typing import Optional, List, Dict, Any, AsyncIterator, Callable, TYPE_CHECKING
from pathlib import Path
from datetime import datetime
import json

# Type hint for WatchHandler without circular import
if TYPE_CHECKING:
    from utils.watch_handler import WatchHandler

# Import agent logging service (deferred to avoid circular imports)
_agent_logging_service = None

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
    - Progress tracking and real-time event emission
    """

    def __init__(self, api_key: Optional[str] = None, working_dir: Optional[Path] = None,
                 progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                 session_id: Optional[str] = None,
                 watch_handler: Optional['WatchHandler'] = None):
        """
        Initialize Claude Agent Client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            working_dir: Working directory for file operations (defaults to current dir)
            progress_callback: Optional callback for progress events during AI operations
            session_id: Optional session ID for tracking agent actions (auto-generated if not provided)
            watch_handler: Optional WatchHandler to restrict file access to watch directories
        """
        if not CLAUDE_SDK_AVAILABLE:
            raise ImportError(
                "claude-agent-sdk is required. Install with: pip install claude-agent-sdk"
            )

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.working_dir = working_dir or Path.cwd()
        self.progress_callback = progress_callback
        
        # Store watch handler for directory restrictions
        self.watch_handler = watch_handler
        self.watch_directories: List[str] = []
        self._initialize_watch_directories()

        # Generate session ID for agent transparency tracking
        self.session_id = session_id or (str(uuid.uuid4()) if progress_callback else None)
        self.store_agent_logs = bool(progress_callback)  # Only store logs if progress callback is provided

        # Initialize agent logging service for database logging
        self.logging_service = None
        if self.session_id:
            try:
                from services.agent_logging_service import get_agent_logging_service
                self.logging_service = get_agent_logging_service()
                if self.logging_service.enabled:
                    logger.debug(f"Agent logging service initialized for session {self.session_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize agent logging service: {e}")

        if not self.api_key:
            logger.warning("No ANTHROPIC_API_KEY found. Set it via environment variable.")

        # Import model setting from config
        try:
            from config.settings import CLAUDE_MODEL
            self.model = CLAUDE_MODEL.lower()  # "haiku", "sonnet", or "opus"
        except ImportError:
            logger.warning("CLAUDE_MODEL setting not found. Using default.")
            self.model = None

        # Create default options with specified model and restricted cwd
        self.default_options = ClaudeAgentOptions(
            cwd=str(self._get_restricted_cwd()),
            allowed_tools=["Read"],  # Safe default: only allow reading files
            max_turns=10,
            model=self.model,  # Use model from settings
        )

        logger.info(f"Claude Agent Client initialized (working_dir={self.working_dir}, restricted_cwd={self._get_restricted_cwd()}, watch_dirs={self.watch_directories}, model={self.model or 'default'}, session_id={self.session_id})")
    
    def _initialize_watch_directories(self) -> None:
        """Initialize the list of allowed watch directories from WatchHandler."""
        if self.watch_handler is None:
            # Try to create a WatchHandler if not provided
            try:
                from utils.watch_handler import WatchHandler
                self.watch_handler = WatchHandler(self.working_dir)
                logger.info(f"Auto-initialized WatchHandler for directory restrictions")
            except Exception as e:
                logger.warning(f"Could not initialize WatchHandler: {e}. File access will not be restricted.")
                return
        
        # Get watch directories from handler
        try:
            watch_dirs = self.watch_handler.get_watch_directories(self.working_dir)
            # Convert to relative paths for clarity
            self.watch_directories = []
            for wd in watch_dirs:
                try:
                    rel_path = wd.relative_to(self.working_dir)
                    self.watch_directories.append(str(rel_path))
                except ValueError:
                    # If not relative to working_dir, use absolute path
                    self.watch_directories.append(str(wd))
            
            if not self.watch_directories:
                # Fallback to watch patterns if no directories resolved
                self.watch_directories = list(self.watch_handler.watch_patterns)
            
            logger.info(f"Watch directories configured: {self.watch_directories}")
        except Exception as e:
            logger.warning(f"Failed to get watch directories: {e}")
    
    def _get_restricted_cwd(self) -> Path:
        """
        Get the restricted working directory for Claude operations.
        
        Returns the first watch directory if available, otherwise falls back
        to the configured working directory.
        """
        if self.watch_directories:
            # Use the first watch directory as the restricted cwd
            first_watch_dir = self.watch_directories[0].rstrip('/')
            restricted_path = self.working_dir / first_watch_dir
            if restricted_path.exists() and restricted_path.is_dir():
                return restricted_path
        
        # Fallback to configured working directory
        return self.working_dir
    
    def _get_watch_restriction_prompt(self) -> str:
        """
        Generate the file access restriction instruction for system prompts.
        
        Returns a string to be included in system prompts that instructs Claude
        to only access files within the configured watch directories.
        """
        if not self.watch_directories:
            return ""
        
        dirs_list = ', '.join([f'`{d}`' for d in self.watch_directories])
        
        return f"""
IMPORTANT FILE ACCESS RESTRICTION:
You may ONLY access files within these directories: {dirs_list}
Do NOT read, search, or modify files outside these boundaries.
If asked to access files outside these directories, politely explain that you can only work within the configured watch directories.
"""
    
    def has_watch_restrictions(self) -> bool:
        """Check if watch directory restrictions are configured."""
        return bool(self.watch_directories)

    def _emit_progress_event(self, phase: str, operation: str, details: Dict[str, Any] = None,
                           files_processed: int = 0, total_files: int = None,
                           current_file: str = None, timing: Dict[str, Any] = None):
        """Emit a progress event during AI operations and log to database."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'phase': phase,  # 'data_collection', 'file_exploration', 'analysis', 'generation'
            'operation': operation,  # Current specific operation
            'details': details or {},
            'files_processed': files_processed,
            'total_files': total_files,
            'current_file': current_file,
            'timing': timing or {},
            'session_id': self.session_id  # Include session ID in event
        }

        # Log to database via agent logging service
        if self.logging_service and self.session_id:
            try:
                self.logging_service.log_operation(
                    session_id=self.session_id,
                    phase=phase,
                    operation=operation,
                    details=details,
                    files_processed=files_processed,
                    total_files=total_files,
                    current_file=current_file,
                    timing=timing
                )
            except Exception as e:
                logger.warning(f"Failed to log agent operation to database: {e}")

        # Emit to callback for real-time updates (if callback provided)
        if self.progress_callback:
            try:
                self.progress_callback(event)
            except Exception as e:
                logger.error(f"Error emitting progress event: {e}")

    def _track_operation_start(self, operation_name: str, details: Dict[str, Any] = None):
        """Track the start of an AI operation."""
        self._emit_progress_event(
            phase='analysis',
            operation=f"Starting {operation_name}",
            details=details,
            timing={'start_time': datetime.utcnow().isoformat()}
        )

    def _track_file_exploration(self, file_path: str, operation: str,
                              files_processed: int = 0, total_files: int = None):
        """Track file exploration activities."""
        self._emit_progress_event(
            phase='file_exploration',
            operation=operation,
            current_file=file_path,
            files_processed=files_processed,
            total_files=total_files,
            details={'file_path': file_path, 'operation': operation}
        )

    def _track_analysis_phase(self, phase_name: str, details: Dict[str, Any] = None):
        """Track different phases of analysis."""
        self._emit_progress_event(
            phase='analysis',
            operation=phase_name,
            details=details
        )

    def _track_generation_complete(self, results_summary: Dict[str, Any]):
        """Track completion of generation with results summary."""
        self._emit_progress_event(
            phase='generation',
            operation='Generation complete',
            details=results_summary,
            timing={'end_time': datetime.utcnow().isoformat()}
        )
    
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
            
            # Build system prompt with watch restrictions
            system_prompt = "You are a code analysis assistant. Provide concise, technical summaries."
            system_prompt += self._get_watch_restriction_prompt()
            
            options = ClaudeAgentOptions(
                cwd=str(self._get_restricted_cwd()),
                allowed_tools=["Read"],
                max_turns=3,
                model=self.model,
                system_prompt=system_prompt
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
            logger.error("Claude Agent SDK not available")
            return "Error: Claude Agent SDK not available"
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
            
            # Build system prompt with watch restrictions
            system_prompt = self._get_watch_restriction_prompt() if self.has_watch_restrictions() else None
            
            options = ClaudeAgentOptions(
                cwd=str(self._get_restricted_cwd()),
                allowed_tools=["Read"],
                max_turns=2,
                model=self.model,
                system_prompt=system_prompt,
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
            
            # Build system prompt with watch restrictions
            system_prompt = self._get_watch_restriction_prompt() if self.has_watch_restrictions() else None
            
            options = ClaudeAgentOptions(
                cwd=str(self._get_restricted_cwd()),
                allowed_tools=tools,
                permission_mode='acceptEdits' if allow_file_edits else 'ask',
                max_turns=20,
                model=self.model,
                system_prompt=system_prompt,
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
            
            # Build system prompt with watch restrictions
            system_prompt = self._get_watch_restriction_prompt() if self.has_watch_restrictions() else None
            
            options = ClaudeAgentOptions(
                cwd=str(self._get_restricted_cwd()),
                allowed_tools=["Read"],
                max_turns=3,
                model=self.model,
                system_prompt=system_prompt,
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

    async def _execute_summary_query_with_progress(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        expected_files: List[str]
    ) -> str:
        """Execute a Claude query with detailed progress tracking."""
        result: List[str] = []
        turn_count = 0
        files_examined = set()
        tool_calls_made = []

        self._track_analysis_phase(
            "Initializing AI Conversation",
            details={'expected_files_count': len(expected_files)}
        )

        async for message in query(prompt=prompt, options=options):
            turn_count += 1
            message_type = message.__class__.__name__
            logger.debug("Claude session summary stream with progress: %s (turn %d)", message_type, turn_count)

            # Track progress for each turn
            if turn_count % 2 == 1:  # Every other turn is typically a user/tool interaction
                self._track_analysis_phase(
                    f"AI Analysis Turn {turn_count}",
                    details={
                        'files_examined': len(files_examined),
                        'tool_calls': len(tool_calls_made),
                        'expected_files': len(expected_files)
                    }
                )

            content = getattr(message, "content", None)
            if not content:
                continue

            for block in content:
                block_text = getattr(block, "text", None)
                if block_text:
                    result.append(block_text)

                # Track tool usage for transparency
                block_type = getattr(block, "__class__.__name__", "Unknown")
                if block_type in ["ToolUse", "ToolResult"]:
                    tool_name = getattr(block, "name", "unknown")
                    tool_calls_made.append({
                        'turn': turn_count,
                        'tool': tool_name,
                        'type': block_type
                    })

                    # Track file exploration specifically
                    if tool_name in ["Read", "Grep", "Glob"]:
                        tool_input = getattr(block, "input", {})
                        file_path = tool_input.get("path") or tool_input.get("pattern")

                        if file_path:
                            files_examined.add(str(file_path))
                            self._track_file_exploration(
                                file_path=str(file_path),
                                operation=f"Using {tool_name} tool",
                                files_processed=len(files_examined),
                                total_files=len(expected_files)
                            )

        # Final progress update
        self._track_analysis_phase(
            "AI Analysis Complete",
            details={
                'total_turns': turn_count,
                'files_examined': len(files_examined),
                'tool_calls_made': len(tool_calls_made),
                'files_list': list(files_examined)[:10],  # First 10 for display
                'tools_used': list(set([call['tool'] for call in tool_calls_made]))
            }
        )

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
Analyze the provided context and return a structured summary immediately.
Do not describe analysis steps, planned actions, or use phrases like \"I'll analyze\" or \"Let me check\".

	Follow this exact format:
**Summary**: {length_instruction} Focus on what changed and why it matters, using the highlights below.
**Key Topics**: comma-separated high-level themes (3-5 items)
**Key Keywords**: comma-separated technical terms (up to 6 items)
**Overall Impact**: one word (brief, moderate, or significant)

Context provided:
Files overview ({len(file_summaries)} total):
{files_section}

Diff excerpts:
{diff_context}

Analyze the highlights to describe substantive modifications, naming new sections, behaviors, or documentation themes rather than just counting files.
	"""

            # Build system prompt with watch restrictions
            system_prompt = "You are a technical code analyst who delivers concise, structured summaries. Analyze the provided context and respond immediately in the requested format without planning language or describing your process."
            system_prompt += self._get_watch_restriction_prompt()

            base_options = ClaudeAgentOptions(
                cwd=str(self._get_restricted_cwd()),
                allowed_tools=[],  # No tools needed - all context is provided
                max_turns=1,  # Direct response expected, no tool calls
                model=self.model,
                system_prompt=system_prompt
            )

            response_text = await self._execute_summary_query(prompt, base_options)
            return response_text

        except Exception as e:
            logger.error(f"Error generating comprehensive summary: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Check if Claude Agent SDK is available and configured."""
        return CLAUDE_SDK_AVAILABLE and bool(self.api_key)

    # ========================================================================
    # SESSION SUMMARY METHODS
    # ========================================================================

    async def summarize_session(
        self,
        changed_files: List[str],
        time_range: str,
        working_dir: Optional[Path] = None,
        context_metadata: Optional[Dict] = None,
        previous_summaries: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive session summary by autonomously exploring changed files.

        Claude explores the files autonomously using Read, Grep, and Glob tools.
        Progress events are emitted to show real-time status of the analysis.

        Args:
            changed_files: List of file paths that changed
            time_range: Human-readable time range (e.g., "last 4 hours", "since 2pm")
            working_dir: Optional working directory override
            context_metadata: Optional dict with generation context information:
                - time_window_description: Human-readable time window (e.g., "last 6 hours")
                - filters_applied: List of active filters (e.g., ["*.md", "exclude test files"])
                - scope_controls: Dict with max_files, detail_level, focus_areas
                - change_stats: Optional dict with file counts, line changes, etc.
            previous_summaries: Optional string containing previous summary content to provide context

        Returns:
            Structured markdown summary following CLAUDE_OUTPUT_FORMAT.md specification
        """
        try:
            if not changed_files:
                return "## No Changes\n\n**Summary**: No file changes detected in this session.\n\n### Sources\n\n- None"

            # Track operation start
            self._track_operation_start(
                "Session Summary Generation",
                details={
                    'files_count': len(changed_files),
                    'time_range': time_range,
                    'model': self.model or 'default'
                }
            )

            # Track data collection phase
            self._track_analysis_phase(
                "Data Collection",
                details={
                    'total_files': len(changed_files),
                    'files': changed_files[:10]  # First 10 files for display
                }
            )

            # Convert absolute paths to relative paths for readability
            relative_files = [self._make_relative(f, working_dir) for f in changed_files]
            files_list = "\n".join([f"- `{f}`" for f in relative_files])

            # Track file exploration setup
            self._track_analysis_phase(
                "Preparing File Exploration",
                details={
                    'files_to_examine': len(relative_files),
                    'working_directory': str(working_dir or self.working_dir)
                }
            )

            # Build system prompt with optional context metadata section
            system_prompt_parts = [
                "You are a technical code analyst for the Obby file monitoring system. Your role is to investigate file changes and produce structured summaries.",
                ""
            ]
            
            # Add watch directory restrictions if configured
            if self.has_watch_restrictions():
                system_prompt_parts.append(self._get_watch_restriction_prompt())
                system_prompt_parts.append("")
            
            system_prompt_parts.extend([
                "IMPORTANT INSTRUCTIONS:",
                "1. Use the Read, Grep, and Glob tools to explore files autonomously",
                "2. Focus on understanding WHAT changed and WHY it matters",
                "3. Always follow the exact output format specified below",
                "4. Include a Sources section listing every file you examined",
                "5. Be concise but insightful in your analysis"
            ])

            # Add context metadata instructions if provided
            if context_metadata:
                system_prompt_parts.extend([
                    "6. Reference the Generation Context in your Sources section to explain what filters/scope were applied",
                    ""
                ])

            system_prompt_parts.extend([
                "",
                "OUTPUT FORMAT:",
                "## [Session Title]",
                "",
                "**Summary**: [1-3 concise sentences describing the key changes and their significance]",
                "",
                "**Change Pattern**: [Pattern description - e.g., \"Incremental feature development\", \"Refactoring\", \"Bug fixes\"]",
                "",
                "**Impact Assessment**:",
                "- **Scope**: [local | moderate | widespread]",
                "- **Complexity**: [simple | moderate | complex]",
                "- **Risk Level**: [low | medium | high]",
                "",
                "**Topics**: [comma-separated high-level themes, 3-7 items]",
                "",
                "**Technical Keywords**: [comma-separated technical terms, 5-10 items]",
                "",
                "**Relationships**: [Brief description of how changed files relate to each other, if applicable]"
            ])

            # Add Generation Context section if metadata provided
            if context_metadata:
                system_prompt_parts.extend([
                    "",
                    "### Generation Context",
                    "",
                    "[Brief note about what time window/filters were applied - reference the context provided in the user prompt]"
                ])

            system_prompt_parts.extend([
                "",
                "### Sources",
                "",
                "- `path/to/file.ext` — [One sentence explaining why this file was examined and what role it played]",
                "",
                "### Proposed Questions",
                "",
                "- [Specific, actionable question about the changes]",
                "- [Another question helping user explore implications]",
                "",
                "CRITICAL:",
                "- Do not describe your analysis process (no \"I'll analyze\", \"Let me check\", etc.)",
                "- Respond directly with the formatted summary",
                "- Always include the Sources section",
                "- Only list files you actually examined in Sources"
            ])

            system_prompt = "\n".join(system_prompt_parts)

            # Build user prompt with optional context metadata
            user_prompt_parts = [
                f"Analyze the following file changes from the past {time_range}:",
                "",
                "CHANGED FILES:",
                files_list,
                "",
                f"TIME PERIOD: {time_range}"
            ]

            # Add context metadata if provided
            if context_metadata:
                user_prompt_parts.extend(["", "GENERATION CONTEXT:"])

                # Time window description
                time_desc = context_metadata.get('time_window_description')
                if time_desc:
                    user_prompt_parts.append(f"- Time window: {time_desc}")

                # Filters applied
                filters = context_metadata.get('filters_applied', [])
                if filters:
                    filters_str = ', '.join(filters)
                    user_prompt_parts.append(f"- Filters applied: {filters_str}")

                # Scope controls
                scope = context_metadata.get('scope_controls', {})
                if scope:
                    if 'max_files' in scope:
                        user_prompt_parts.append(f"- Maximum files analyzed: {scope['max_files']}")
                    if 'detail_level' in scope:
                        user_prompt_parts.append(f"- Detail level: {scope['detail_level']}")
                    if 'focus_areas' in scope and scope['focus_areas']:
                        focus = ', '.join(scope['focus_areas'])
                        user_prompt_parts.append(f"- Focus areas: {focus}")

                # Change statistics (if provided)
                stats = context_metadata.get('change_stats', {})
                if stats:
                    if 'total_files' in stats:
                        user_prompt_parts.append(f"- Total files in scope: {stats['total_files']}")
                    if 'files_analyzed' in stats:
                        user_prompt_parts.append(f"- Files analyzed: {stats['files_analyzed']}")

            # Add previous summaries if provided
            if previous_summaries:
                user_prompt_parts.extend([
                    "",
                    "PREVIOUS SUMMARIES:",
                    "The following are previous summaries from earlier sessions. Use these to understand the context and evolution of the project. Build upon the insights from these summaries when analyzing the current changes.",
                    "",
                    "---",
                    "",
                    previous_summaries,
                    "",
                    "---",
                    "",
                    "IMPORTANT: When writing your summary, reference relevant points from previous summaries where appropriate, but focus primarily on the current changes. Show how the current changes relate to or build upon previous work."
                ])

            user_prompt_parts.extend([
                "",
                "TASK: Investigate these files using your Read, Grep, and Glob tools to understand what changed and why. Then produce a session summary following the exact format specified in your system prompt.",
                "",
                "Focus on substantive modifications and their implications. Explore the files to build understanding, then provide the structured summary."
            ])

            user_prompt = "\n".join(user_prompt_parts)

            # Track starting AI analysis
            self._track_analysis_phase(
                "AI Analysis Starting",
                details={
                    'model': self.model or 'default',
                    'max_turns': 15,
                    'tools_allowed': ['Read', 'Grep', 'Glob']
                }
            )

            # Use restricted cwd if no working_dir override provided
            effective_cwd = working_dir if working_dir else self._get_restricted_cwd()
            
            options = ClaudeAgentOptions(
                cwd=str(effective_cwd),
                allowed_tools=["Read", "Grep", "Glob"],  # Allow autonomous exploration
                max_turns=15,  # Allow enough turns for exploration
                model=self.model,  # Use configured model
                system_prompt=system_prompt
            )

            # Execute with progress tracking
            self._track_analysis_phase("Executing AI Analysis")
            result = await self._execute_summary_query_with_progress(user_prompt, options, changed_files)

            # Track completion
            self._track_generation_complete({
                'analysis_type': 'session_summary',
                'files_analyzed': len(changed_files),
                'result_length': len(result) if result else 0,
                'model_used': self.model or 'default'
            })

            return result

        except Exception as e:
            logger.error(f"Error in summarize_session: {e}", exc_info=True)

            # Track error occurrence
            self._emit_progress_event(
                phase='error',
                operation='Session Summary Failed',
                details={
                    'error': str(e),
                    'files_count': len(changed_files),
                    'time_range': time_range
                }
            )

            return self._build_session_summary_fallback(changed_files, time_range, error=str(e))

    async def summarize_file_change(
        self,
        file_path: str,
        change_type: str,
        working_dir: Optional[Path] = None
    ) -> str:
        """
        Generate a summary for a single file change by examining the file.

        Claude autonomously analyzes the file using appropriate tools.

        Args:
            file_path: Path to the changed file
            change_type: Type of change ("created", "modified", "deleted", "moved", "renamed")
            working_dir: Optional working directory override

        Returns:
            Structured markdown summary for individual file change
        """
        try:
            relative_path = self._make_relative(file_path, working_dir)

            # Build system prompt with watch restrictions
            system_prompt_parts = []
            
            if self.has_watch_restrictions():
                system_prompt_parts.append(self._get_watch_restriction_prompt())
                system_prompt_parts.append("")
            
            system_prompt_parts.append("""You are a technical code analyst. Analyze a single file change and produce a structured summary.

OUTPUT FORMAT:
**File Change Summary**

**File**: `path/to/file.ext`

**Change Type**: [created | modified | deleted | moved | renamed]

**Summary**: [1-2 sentences describing the change]

**Topics**: [comma-separated themes]

**Keywords**: [comma-separated technical terms]

**Impact**: [brief | moderate | significant]

**Related Files**: [comma-separated paths of files that likely interact with this change]

INSTRUCTIONS:
- Use Read tool to examine the file (if it exists)
- Use Grep to search for references to this file
- Be specific about what changed and why it matters
- Do not describe your analysis process""")

            system_prompt = "\n".join(system_prompt_parts)

            user_prompt = f"""Analyze this file change:

FILE: `{relative_path}`
CHANGE TYPE: {change_type}

Use your tools to investigate the file and understand the change. Then provide the structured summary."""

            # Use restricted cwd if no working_dir override provided
            effective_cwd = working_dir if working_dir else self._get_restricted_cwd()

            options = ClaudeAgentOptions(
                cwd=str(effective_cwd),
                allowed_tools=[],  # No tools needed - all context is provided
                max_turns=1,  # Direct response expected, no tool calls
                model=self.model,
                system_prompt=system_prompt
            )

            result = await self._execute_summary_query(user_prompt, options)
            return result

        except Exception as e:
            logger.error(f"Error in summarize_file_change: {e}", exc_info=True)
            return f"**File Change Summary**\n\n**File**: `{file_path}`\n\n**Change Type**: {change_type}\n\n**Summary**: Error analyzing file: {str(e)}\n\n**Impact**: brief"

    async def generate_session_title(
        self,
        changed_files: List[str],
        context_summary: Optional[str] = None
    ) -> str:
        """
        Generate a concise, punchy title for a session.

        Claude generates an appropriate title based on the file changes.

        Args:
            changed_files: List of files that changed
            context_summary: Optional summary text to inform title generation

        Returns:
            Title string (3-7 words, Title Case, optional emoji prefix)
        """
        try:
            files_context = "\n".join([f"- {self._make_relative(f)}" for f in changed_files[:10]])

            # Build system prompt (no watch restrictions needed for title generation - no file access)
            system_prompt = """You create concise, punchy titles for development session summaries.

RULES:
- Return ONLY the title (nothing else)
- 3-7 words, Title Case
- No trailing punctuation
- Optionally start with ONE relevant emoji if it clearly fits
- Capture the main theme concisely

EXAMPLES:
- 🔒 Authentication System Refactoring
- Bug Fixes and Performance Tuning
- Database Migration Setup
- 📝 Documentation Updates
- API Endpoint Expansion"""

            user_prompt = f"""Create a concise title for a development session with these changes:

FILES:
{files_context}"""

            if context_summary:
                user_prompt += f"\n\nCONTEXT:\n{context_summary[:500]}"

            user_prompt += "\n\nProvide only the title (3-7 words, Title Case)."

            options = ClaudeAgentOptions(
                cwd=str(self._get_restricted_cwd()),
                allowed_tools=[],  # No tools needed for title generation
                max_turns=1,
                model=self.model,
                system_prompt=system_prompt
            )

            result = await self._execute_summary_query(user_prompt, options)

            # Clean up the title
            title = result.strip().strip('"\'`').replace('\n', ' ')

            # If title is too long or looks wrong, use fallback
            if not title or len(title) > 60 or len(title.split()) > 10:
                return "Code Changes"

            return title

        except Exception as e:
            logger.error(f"Error in generate_session_title: {e}", exc_info=True)
            return "Code Changes"

    async def generate_follow_up_questions(
        self,
        changed_files: List[str],
        summary_context: str,
        working_dir: Optional[Path] = None
    ) -> List[str]:
        """
        Generate 2-4 actionable follow-up questions about the changes.

        Claude generates relevant questions based on the changes.

        Args:
            changed_files: List of files that changed
            summary_context: Summary of changes for context
            working_dir: Optional working directory override

        Returns:
            List of question strings (2-4 items)
        """
        try:
            files_list = "\n".join([f"- `{self._make_relative(f, working_dir)}`" for f in changed_files[:10]])

            # Build system prompt (no watch restrictions needed - no file access)
            system_prompt = """You propose thoughtful follow-up questions to help a user reflect on changes.

RULES:
- Generate 2-4 concise questions
- Each question should start with '- '
- Be specific and actionable
- Avoid generic questions
- Focus on implications, testing, or next steps
- If changes are trivial, return empty response

EXAMPLES:
- How should the frontend handle the transition to refresh tokens for existing users?
- What monitoring should be added to track token refresh patterns?
- Should we add rate limiting to the token refresh endpoint to prevent abuse?"""

            user_prompt = f"""Given these changes, propose 2-4 questions the user could explore next:

FILES:
{files_list}

SUMMARY:
{summary_context[:800]}

Provide 2-4 specific, actionable questions (each starting with '- ')."""

            # Use restricted cwd if no working_dir override provided
            effective_cwd = working_dir if working_dir else self._get_restricted_cwd()

            options = ClaudeAgentOptions(
                cwd=str(effective_cwd),
                allowed_tools=[],  # No tools needed
                max_turns=1,
                model=self.model,
                system_prompt=system_prompt
            )

            result = await self._execute_summary_query(user_prompt, options)

            # Parse questions from result
            questions = []
            for line in result.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    questions.append(line[2:].strip())  # Remove '- ' prefix

            # Return 2-4 questions
            return questions[:4] if len(questions) >= 2 else []

        except Exception as e:
            logger.error(f"Error in generate_follow_up_questions: {e}", exc_info=True)
            return []

    # ========================================================================
    # HELPER METHODS FOR SUMMARY GENERATION
    # ========================================================================

    def _make_relative(self, file_path: str, working_dir: Optional[Path] = None) -> str:
        """Convert absolute path to relative path from working directory."""
        try:
            wd = working_dir or self.working_dir
            abs_path = Path(file_path)
            if abs_path.is_absolute():
                return str(abs_path.relative_to(wd))
            return file_path
        except (ValueError, Exception):
            return file_path

    def _build_session_summary_fallback(
        self,
        changed_files: List[str],
        time_range: str,
        error: Optional[str] = None
    ) -> str:
        """Build a deterministic fallback summary if Claude fails to comply."""
        file_count = len(changed_files)

        if file_count == 0:
            summary_text = f"No file changes detected during the {time_range} period."
            topics = "None"
            keywords = "None"
        else:
            relative_files = [self._make_relative(f) for f in changed_files]
            first_files = ", ".join([f"`{f}`" for f in relative_files[:3]])
            if file_count > 3:
                first_files += f", and {file_count - 3} more"

            summary_text = f"{file_count} files changed during the {time_range} period. Notable files: {first_files}."
            topics = "Code Changes, File Modifications"
            keywords = ", ".join(relative_files[:5])

        error_note = f"\n\n**Note**: Generated as fallback due to error: {error}" if error else ""

        return f"""## Code Changes

**Summary**: {summary_text}

**Change Pattern**: Code modifications

**Impact Assessment**:
- **Scope**: moderate
- **Complexity**: moderate
- **Risk Level**: low

**Topics**: {topics}

**Technical Keywords**: {keywords}

**Relationships**: Multiple files modified in the {time_range} period.

### Sources

{chr(10).join([f"- `{self._make_relative(f)}` — File modified in this session" for f in changed_files[:10]])}

### Proposed Questions

- What were the main goals of these changes?
- Are there any related files that should be reviewed?{error_note}"""


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
