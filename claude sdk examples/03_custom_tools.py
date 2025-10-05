"""
Example 3: Custom Tools

This example demonstrates how to create custom tools that Claude can use.
Custom tools extend Claude's capabilities by allowing it to:
- Perform calculations
- Access external data
- Execute custom business logic
- Interact with APIs

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable
- Install dependencies: pip install -r requirements.txt

Usage:
    python examples/03_custom_tools.py
"""

import anyio
from claude_agent_sdk import ClaudeSDKClient
from typing import Any


# Define a simple calculator tool
def calculator(operation: str, a: float, b: float) -> dict[str, Any]:
    """
    A simple calculator tool that Claude can use.

    Args:
        operation: The operation to perform (+, -, *, /)
        a: First number
        b: Second number

    Returns:
        Dictionary with the result or error
    """
    operations = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y if y != 0 else "Error: Division by zero"
    }

    if operation not in operations:
        return {"error": f"Unknown operation: {operation}"}

    result = operations[operation](a, b)
    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result
    }


# Define a weather tool (simulated)
def get_weather(city: str) -> dict[str, Any]:
    """
    A simulated weather tool.

    In a real application, this would call a weather API.

    Args:
        city: Name of the city

    Returns:
        Dictionary with weather information
    """
    # Simulated weather data
    weather_data = {
        "new york": {"temperature": 72, "condition": "Sunny", "humidity": 45},
        "london": {"temperature": 59, "condition": "Cloudy", "humidity": 70},
        "tokyo": {"temperature": 68, "condition": "Rainy", "humidity": 80},
        "paris": {"temperature": 65, "condition": "Partly Cloudy", "humidity": 55}
    }

    city_lower = city.lower()
    if city_lower in weather_data:
        data = weather_data[city_lower]
        return {
            "city": city,
            "temperature_f": data["temperature"],
            "condition": data["condition"],
            "humidity": data["humidity"]
        }
    else:
        return {"error": f"Weather data not available for {city}"}


async def main():
    """
    Demonstrate using custom tools with Claude.
    
    The query() function returns an async iterator that yields different
    message types:
    - SystemMessage: Session initialization info
    - AssistantMessage: Claude's actual response
    - ResultMessage: Performance summary (cost, timing, tokens)
    """
    print("=" * 60)
    print("🛠️  CUSTOM TOOLS DEMO")
    print("=" * 60)
    print()

    # Create a client with custom tools
    # Note: The actual API for registering tools may vary
    # This is a conceptual example based on typical SDK patterns

    client = ClaudeSDKClient()

    # Register custom tools (this API may vary in actual implementation)
    # In practice, you might need to use MCP servers or other mechanisms
    print("📝 EXAMPLE 1: Using Calculator Tool")
    print("-" * 60)
    
    # Track message number
    message_num = 0
    
    async for message in client.query(
        prompt="Can you calculate 125 * 48 for me using the calculator tool?"
    ):
        message_num += 1
        message_type = message.__class__.__name__
        
        print(f"📦 MESSAGE {message_num}: {message_type}")
        print("-" * 60)
        
        # Handle different message types using match-case
        match message_type:
            case "SystemMessage":
                print("🔧 SESSION INITIALIZATION")
                if hasattr(message, 'data'):
                    print(f"   • Session ID: {message.data.get('session_id', 'N/A')[:8]}...")
                    print(f"   • Model: {message.data.get('model', 'N/A')}")
                    print(f"   • Working Directory: {message.data.get('cwd', 'N/A')}")
                    print(f"   • Available Tools: {len(message.data.get('tools', []))} tools")
            
            case "AssistantMessage":
                print("💬 CLAUDE'S RESPONSE:")
                print()
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            # Print the actual answer with nice formatting
                            print("   ", block.text.replace("\n", "\n    "))
                print()
            
            case "ResultMessage":
                print("📊 PERFORMANCE SUMMARY:")
                if hasattr(message, 'duration_ms'):
                    print(f"   • Total Time: {message.duration_ms / 1000:.2f} seconds")
                if hasattr(message, 'total_cost_usd'):
                    print(f"   • Cost: ${message.total_cost_usd:.4f}")
                if hasattr(message, 'usage'):
                    usage = message.usage
                    print(f"   • Input Tokens: {usage.get('input_tokens', 0)}")
                    print(f"   • Output Tokens: {usage.get('output_tokens', 0)}")
                if hasattr(message, 'is_error'):
                    status = "✅ Success" if not message.is_error else "❌ Error"
                    print(f"   • Status: {status}")
            
            case _:
                print(f"ℹ️  Unknown message type: {message_type}")
                print(f"   {message}")
        
        print()

    print("=" * 60)
    print("📝 EXAMPLE 2: Using Weather Tool")
    print("=" * 60)
    print()
    
    # Reset message counter
    message_num = 0
    
    async for message in client.query(
        prompt="What's the weather like in Tokyo?"
    ):
        message_num += 1
        message_type = message.__class__.__name__
        
        print(f"📦 MESSAGE {message_num}: {message_type}")
        print("-" * 60)
        
        # Handle different message types using match-case
        match message_type:
            case "SystemMessage":
                print("🔧 SESSION INITIALIZATION")
                if hasattr(message, 'data'):
                    print(f"   • Session ID: {message.data.get('session_id', 'N/A')[:8]}...")
                    print(f"   • Model: {message.data.get('model', 'N/A')}")
                    print(f"   • Working Directory: {message.data.get('cwd', 'N/A')}")
                    print(f"   • Available Tools: {len(message.data.get('tools', []))} tools")
            
            case "AssistantMessage":
                print("💬 CLAUDE'S RESPONSE:")
                print()
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            # Print the actual answer with nice formatting
                            print("   ", block.text.replace("\n", "\n    "))
                print()
            
            case "ResultMessage":
                print("📊 PERFORMANCE SUMMARY:")
                if hasattr(message, 'duration_ms'):
                    print(f"   • Total Time: {message.duration_ms / 1000:.2f} seconds")
                if hasattr(message, 'total_cost_usd'):
                    print(f"   • Cost: ${message.total_cost_usd:.4f}")
                if hasattr(message, 'usage'):
                    usage = message.usage
                    print(f"   • Input Tokens: {usage.get('input_tokens', 0)}")
                    print(f"   • Output Tokens: {usage.get('output_tokens', 0)}")
                if hasattr(message, 'is_error'):
                    status = "✅ Success" if not message.is_error else "❌ Error"
                    print(f"   • Status: {status}")
            
            case _:
                print(f"ℹ️  Unknown message type: {message_type}")
                print(f"   {message}")
        
        print()

    print("=" * 60)
    print("📝 EXAMPLE 3: Combining Multiple Tools")
    print("=" * 60)
    print()
    
    # Reset message counter
    message_num = 0
    
    async for message in client.query(
        prompt="What's the weather in New York, and if the temperature is above 70F, multiply it by 1.8 and add 32 to convert to Celsius. Wait, that's backwards. Just tell me the temperature."
    ):
        message_num += 1
        message_type = message.__class__.__name__
        
        print(f"📦 MESSAGE {message_num}: {message_type}")
        print("-" * 60)
        
        # Handle different message types using match-case
        match message_type:
            case "SystemMessage":
                print("🔧 SESSION INITIALIZATION")
                if hasattr(message, 'data'):
                    print(f"   • Session ID: {message.data.get('session_id', 'N/A')[:8]}...")
                    print(f"   • Model: {message.data.get('model', 'N/A')}")
                    print(f"   • Working Directory: {message.data.get('cwd', 'N/A')}")
                    print(f"   • Available Tools: {len(message.data.get('tools', []))} tools")
            
            case "AssistantMessage":
                print("💬 CLAUDE'S RESPONSE:")
                print()
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            # Print the actual answer with nice formatting
                            print("   ", block.text.replace("\n", "\n    "))
                print()
            
            case "ResultMessage":
                print("📊 PERFORMANCE SUMMARY:")
                if hasattr(message, 'duration_ms'):
                    print(f"   • Total Time: {message.duration_ms / 1000:.2f} seconds")
                if hasattr(message, 'total_cost_usd'):
                    print(f"   • Cost: ${message.total_cost_usd:.4f}")
                if hasattr(message, 'usage'):
                    usage = message.usage
                    print(f"   • Input Tokens: {usage.get('input_tokens', 0)}")
                    print(f"   • Output Tokens: {usage.get('output_tokens', 0)}")
                if hasattr(message, 'is_error'):
                    status = "✅ Success" if not message.is_error else "❌ Error"
                    print(f"   • Status: {status}")
            
            case _:
                print(f"ℹ️  Unknown message type: {message_type}")
                print(f"   {message}")
        
        print()
    
    print("=" * 60)
    print("✨ CUSTOM TOOLS DEMO COMPLETED!")
    print("=" * 60)


# Standalone tool demonstration
def demonstrate_tools():
    """
    Show how the tools work independently.
    """
    print("\n\n" + "=" * 60)
    print("🔧 STANDALONE TOOL DEMONSTRATION")
    print("=" * 60)
    print()

    print("📊 CALCULATOR EXAMPLES:")
    print("-" * 60)
    print("   ", calculator('+', 10, 5))
    print("   ", calculator('*', 7, 8))
    print("   ", calculator('/', 100, 4))

    print("\n🌤️  WEATHER EXAMPLES:")
    print("-" * 60)
    print("   ", get_weather("New York"))
    print("   ", get_weather("London"))
    print("   ", get_weather("Sydney"))  # Not in our data


if __name__ == "__main__":
    # First show how tools work independently
    demonstrate_tools()

    # Then show how Claude can use them
    # Note: Uncomment when you have proper tool registration set up
    # anyio.run(main)

    print("\n" + "=" * 60)
    print("ℹ️  NOTE: Full integration with Claude requires proper MCP server setup.")
    print("ℹ️  See example 06_mcp_server.py for complete tool integration.")
    print("=" * 60)
