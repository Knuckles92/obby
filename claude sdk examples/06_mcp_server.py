"""
Example 6: MCP Server Integration

MCP (Model Context Protocol) servers allow you to create custom tools that
Claude can use. This example demonstrates how to:
- Create a simple MCP server
- Register custom tools
- Use those tools with Claude

MCP servers are the recommended way to extend Claude's capabilities with
custom functionality.

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable
- Install dependencies: pip install -r requirements.txt
- Node.js installed (required for Claude Code CLI)

Usage:
    python examples/06_mcp_server.py

Learn more about MCP:
    https://modelcontextprotocol.io/
"""

import anyio
from claude_agent_sdk import ClaudeSDKClient
import json
from typing import Any, Dict


class SimpleMCPServer:
    """
    A simple in-process MCP server implementation.

    This demonstrates the concept of MCP servers.
    For production use, refer to the official MCP documentation.
    """

    def __init__(self):
        self.tools = {}

    def register_tool(self, name: str, description: str, parameters: Dict, handler):
        """
        Register a tool with the MCP server.

        Args:
            name: Tool name
            description: Tool description for Claude
            parameters: JSON schema for tool parameters
            handler: Function to execute when tool is called
        """
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }

    def get_tools_schema(self) -> list:
        """
        Get the schema for all registered tools.

        Returns:
            List of tool schemas for Claude
        """
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for tool in self.tools.values()
        ]

    async def call_tool(self, name: str, arguments: Dict) -> Any:
        """
        Call a registered tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")

        handler = self.tools[name]["handler"]

        # Call the handler (sync or async)
        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        else:
            return handler(**arguments)


# Example Tool 1: Calculator
def calculator_tool(operation: str, x: float, y: float) -> Dict[str, Any]:
    """
    Perform basic arithmetic operations.

    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        x: First number
        y: Second number

    Returns:
        Calculation result
    """
    operations = {
        'add': lambda a, b: a + b,
        'subtract': lambda a, b: a - b,
        'multiply': lambda a, b: a * b,
        'divide': lambda a, b: a / b if b != 0 else None
    }

    if operation not in operations:
        return {"error": f"Unknown operation: {operation}"}

    result = operations[operation](x, y)

    if result is None:
        return {"error": "Division by zero"}

    return {
        "operation": operation,
        "x": x,
        "y": y,
        "result": result
    }


# Example Tool 2: Text Analyzer
def text_analyzer_tool(text: str, analysis_type: str) -> Dict[str, Any]:
    """
    Analyze text in various ways.

    Args:
        text: Text to analyze
        analysis_type: Type of analysis ('word_count', 'char_count', 'uppercase')

    Returns:
        Analysis result
    """
    analyses = {
        'word_count': lambda t: {"word_count": len(t.split())},
        'char_count': lambda t: {"char_count": len(t)},
        'uppercase': lambda t: {"uppercase_text": t.upper()},
        'lowercase': lambda t: {"lowercase_text": t.lower()},
    }

    if analysis_type not in analyses:
        return {"error": f"Unknown analysis type: {analysis_type}"}

    result = analyses[analysis_type](text)
    result["original_text"] = text
    result["analysis_type"] = analysis_type

    return result


# Example Tool 3: Data Storage (In-memory)
class DataStore:
    """Simple in-memory data store for demonstration."""

    def __init__(self):
        self.store = {}

    def save(self, key: str, value: str) -> Dict[str, Any]:
        """Save a key-value pair."""
        self.store[key] = value
        return {"success": True, "key": key, "message": "Data saved"}

    def retrieve(self, key: str) -> Dict[str, Any]:
        """Retrieve a value by key."""
        if key in self.store:
            return {"success": True, "key": key, "value": self.store[key]}
        return {"success": False, "error": f"Key '{key}' not found"}

    def list_keys(self) -> Dict[str, Any]:
        """List all keys in the store."""
        return {"keys": list(self.store.keys()), "count": len(self.store)}


async def demo_mcp_server():
    """
    Demonstrate creating and using an MCP server.
    """
    print("=" * 60)
    print("🔧 MCP SERVER INTEGRATION DEMO")
    print("=" * 60)
    print()

    # Create MCP server
    mcp = SimpleMCPServer()

    # Register calculator tool
    mcp.register_tool(
        name="calculator",
        description="Perform arithmetic operations (add, subtract, multiply, divide)",
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "x": {"type": "number"},
                "y": {"type": "number"}
            },
            "required": ["operation", "x", "y"]
        },
        handler=calculator_tool
    )

    # Register text analyzer tool
    mcp.register_tool(
        name="text_analyzer",
        description="Analyze text (word_count, char_count, uppercase, lowercase)",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["word_count", "char_count", "uppercase", "lowercase"]
                }
            },
            "required": ["text", "analysis_type"]
        },
        handler=text_analyzer_tool
    )

    # Register data store tools
    data_store = DataStore()

    mcp.register_tool(
        name="data_store_save",
        description="Save data to the in-memory store",
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"}
            },
            "required": ["key", "value"]
        },
        handler=data_store.save
    )

    mcp.register_tool(
        name="data_store_retrieve",
        description="Retrieve data from the in-memory store",
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string"}
            },
            "required": ["key"]
        },
        handler=data_store.retrieve
    )

    # Display registered tools
    print("📋 REGISTERED TOOLS:")
    print("-" * 60)
    for tool in mcp.get_tools_schema():
        print(f"   • {tool['name']}: {tool['description']}")

    # Test tools directly
    print("\n🧪 DIRECT TOOL TESTING:")
    print("-" * 60)

    print("\n📊 1. CALCULATOR: 25 + 17")
    print("-" * 60)
    result = await mcp.call_tool("calculator", {
        "operation": "add",
        "x": 25,
        "y": 17
    })
    print(f"   Result: {json.dumps(result, indent=2)}")

    print("\n📝 2. TEXT ANALYZER: Word count")
    print("-" * 60)
    result = await mcp.call_tool("text_analyzer", {
        "text": "Hello Claude Agent SDK",
        "analysis_type": "word_count"
    })
    print(f"   Result: {json.dumps(result, indent=2)}")

    print("\n💾 3. DATA STORE: Save and retrieve")
    print("-" * 60)
    save_result = await mcp.call_tool("data_store_save", {
        "key": "user_name",
        "value": "Alice"
    })
    print(f"   Save: {json.dumps(save_result, indent=2)}")

    retrieve_result = await mcp.call_tool("data_store_retrieve", {
        "key": "user_name"
    })
    print(f"   Retrieve: {json.dumps(retrieve_result, indent=2)}")


async def demo_mcp_with_claude():
    """
    Demonstrate using MCP server with Claude.

    Note: This requires proper MCP server setup as per official documentation.
    """
    print("\n\n" + "=" * 60)
    print("🤖 USING MCP SERVER WITH CLAUDE")
    print("=" * 60)
    print()

    print("🔧 TO INTEGRATE MCP SERVERS WITH CLAUDE:")
    print("-" * 60)
    print("   1. Set up MCP server following official documentation")
    print("   2. Configure Claude Agent SDK to use the MCP server")
    print("   3. Claude will automatically use available tools")
    
    print("\n💡 EXAMPLE QUERIES CLAUDE COULD HANDLE WITH THESE TOOLS:")
    print("-" * 60)
    print("   • 'Calculate 123 * 456 for me'")
    print("   • 'How many words are in this sentence?'")
    print("   • 'Save my name as John to the data store'")
    
    print("\n📚 REFER TO OFFICIAL MCP DOCUMENTATION FOR FULL SETUP:")
    print("-" * 60)
    print("   https://modelcontextprotocol.io/")
    print("=" * 60)


async def main():
    """
    Run all MCP server demonstrations.
    """
    print("=" * 60)
    print("🔧 MCP SERVER INTEGRATION EXAMPLE")
    print("=" * 60)
    print("Model Context Protocol (MCP) allows you to create")
    print("custom tools that extend Claude's capabilities")
    print("=" * 60)
    print()

    await demo_mcp_server()
    await demo_mcp_with_claude()

    print("\n" + "=" * 60)
    print("✨ MCP SERVER DEMO COMPLETED!")
    print("=" * 60)
    print("\n🚀 NEXT STEPS:")
    print("   1. Study the official MCP documentation")
    print("   2. Create your own custom tools")
    print("   3. Build a production MCP server")
    print("   4. Integrate with Claude Agent SDK")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    anyio.run(main)
