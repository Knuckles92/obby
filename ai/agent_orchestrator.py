"""
Agent orchestrator for managing tool execution and agentic loops in chat.

This module provides the core logic for:
1. Managing tool definitions and registration
2. Executing tools based on AI model requests
3. Implementing basic agentic loops with tool feedback
4. Coordinating between the chat interface and available tools
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass

from ai.ai_tooling import NotesSearchTool, ToolResult, get_default_tools
from ai.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call request from the AI model."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCallResult:
    """Represents the result of executing a tool call."""
    tool_call_id: str
    name: str
    content: str
    success: bool
    error: Optional[str] = None


class AgentOrchestrator:
    """
    Orchestrates tool execution and agentic loops for the chat system.
    
    Manages:
    - Tool registration and discovery
    - Tool call parsing and execution
    - Multi-turn conversations with tool feedback
    - Error handling and graceful degradation
    """
    
    def __init__(self):
        self.tools = {}
        self.tool_schemas = []
        self._register_default_tools()
        
    def _register_default_tools(self):
        """Register all available tools and their schemas."""
        # Register NotesSearchTool
        notes_tool = NotesSearchTool()
        self.tools[notes_tool.name] = notes_tool
        
        # Define OpenAI function schema for notes search
        self.tool_schemas.append({
            "type": "function",
            "function": {
                "name": "notes_search",
                "description": "Search through local notes and documentation files using grep/ripgrep. Returns structured results with file paths, line numbers, and content snippets.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string. Can be literal text, regex patterns, or keywords to find in the notes."
                        },
                        "max_matches": {
                            "type": "integer", 
                            "description": "Maximum number of search results to return. Defaults to 20.",
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                }
            }
        })
        
        logger.info(f"Registered {len(self.tools)} tools: {list(self.tools.keys())}")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return the OpenAI function schemas for all registered tools."""
        return self.tool_schemas.copy()

    def execute_tool_call(self, tool_call: ToolCall) -> ToolCallResult:
        """
        Execute a single tool call and return the result.
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            ToolCallResult with the execution result
        """
        try:
            if tool_call.name not in self.tools:
                return ToolCallResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=f"Unknown tool: {tool_call.name}",
                    success=False,
                    error=f"Tool '{tool_call.name}' not found"
                )
            
            tool = self.tools[tool_call.name]
            
            # Execute tool based on its type
            if tool_call.name == "notes_search":
                result = self._execute_notes_search(tool, tool_call.arguments)
            else:
                return ToolCallResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=f"Tool execution not implemented for: {tool_call.name}",
                    success=False,
                    error="Tool execution not implemented"
                )
            
            return ToolCallResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=result,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_call.name}: {e}")
            return ToolCallResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=f"Tool execution failed: {str(e)}",
                success=False,
                error=str(e)
            )

    def _execute_notes_search(self, tool: NotesSearchTool, arguments: Dict[str, Any]) -> str:
        """Execute the notes search tool with the provided arguments."""
        query = arguments.get("query", "")
        max_matches = arguments.get("max_matches", None)
        
        if not query:
            return "Error: query parameter is required for notes search"
        
        try:
            result = tool.run(query, max_matches=max_matches)
            if result and hasattr(result, 'format_for_agent'):
                return result.format_for_agent()
            else:
                logger.error("Notes search returned invalid result")
                return "Error: Notes search returned an invalid result"
        except Exception as e:
            logger.error(f"Notes search failed: {e}", exc_info=True)
            return f"Notes search failed: {str(e)}"

    def parse_tool_calls(self, message) -> List[ToolCall]:
        """
        Parse tool calls from an OpenAI message response.
        
        Args:
            message: The message object from OpenAI API response
            
        Returns:
            List of ToolCall objects to execute
        """
        tool_calls = []
        
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=arguments
                    ))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool call arguments: {e}")
                    # Create a tool call result with error for this malformed call
                    continue
                    
        return tool_calls

    def execute_chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        max_iterations: int = 5,
        on_agent_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Execute a complete agentic loop with tool calling.
        
        Args:
            messages: Conversation messages in OpenAI format
            max_iterations: Maximum number of tool call iterations
            
        Returns:
            Tuple of (final_response, conversation_history)
        """
        client = OpenAIClient.get_instance()
        if not client.is_available():
            return "Error: OpenAI client not available. Please set OPENAI_API_KEY.", messages
        
        # Ensure client is warmed up
        if not getattr(OpenAIClient, '_warmed_up', False):
            try:
                client.warm_up()
            except Exception as e:
                logger.warning(f"Client warm-up failed: {e}")
        
        conversation = messages.copy()
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            try:
                # Make API call with tools
                response = client._retry_with_backoff(
                    client._invoke_model_with_tools,
                    model=client.model,
                    messages=conversation,
                    tools=self.get_tool_schemas(),
                    tool_choice="auto",
                    max_completion_tokens=2000,
                    temperature=client._get_temperature(0.7)
                )
                
                message = response.choices[0].message
                
                # Add assistant message to conversation
                assistant_message = {
                    "role": "assistant",
                    "content": message.content or ""
                }
                
                # Check if there are tool calls
                tool_calls = self.parse_tool_calls(message)
                
                if tool_calls:
                    # Record intermediate assistant reasoning if present
                    if on_agent_event and (message.content or "").strip():
                        on_agent_event("assistant_thinking", {
                            "content": message.content,
                            "tool_count": len(tool_calls)
                        })
                    
                    # Add tool calls to the assistant message
                    assistant_message["tool_calls"] = []
                    for tc in tool_calls:
                        assistant_message["tool_calls"].append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        })
                        if on_agent_event:
                            on_agent_event("tool_call", {
                                "tool_call_id": tc.id,
                                "name": tc.name,
                                "arguments": tc.arguments
                            })
                    
                    conversation.append(assistant_message)
                    
                    # Execute tool calls
                    for tool_call in tool_calls:
                        result = self.execute_tool_call(tool_call)
                        
                        # Add tool result to conversation
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": result.tool_call_id,
                            "name": result.name,
                            "content": result.content
                        }
                        conversation.append(tool_message)

                        if on_agent_event:
                            on_agent_event("tool_result", {
                                "tool_call_id": result.tool_call_id,
                                "name": result.name,
                                "content": result.content,
                                "success": result.success,
                                "error": result.error,
                            })
                    
                    # Continue the loop to get AI's response to tool results
                    continue
                else:
                    # No tool calls, we have the final response
                    conversation.append(assistant_message)
                    if on_agent_event and (message.content or "").strip():
                        on_agent_event("assistant_response", {
                            "content": message.content,
                            "tool_calls": assistant_message.get("tool_calls", [])
                        })
                    return message.content or "No response generated.", conversation
                    
            except Exception as e:
                logger.error(f"Chat with tools iteration {iterations} failed: {e}")
                error_msg = f"Error in tool execution loop: {str(e)}"
                conversation.append({"role": "assistant", "content": error_msg})
                if on_agent_event:
                    on_agent_event("error", {
                        "error": error_msg,
                        "exception_type": type(e).__name__
                    })
                return error_msg, conversation
        
        # Max iterations reached
        final_msg = "Maximum tool iterations reached. Please try rephrasing your request."
        conversation.append({"role": "assistant", "content": final_msg})
        if on_agent_event:
            on_agent_event("warning", {
                "message": final_msg,
                "iterations": iterations
            })
        return final_msg, conversation


# Global instance for easy access
_orchestrator_instance = None

def get_orchestrator() -> AgentOrchestrator:
    """Get the global agent orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
