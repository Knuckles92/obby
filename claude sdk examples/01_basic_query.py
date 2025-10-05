"""
Example 1: Basic Query (Hello World) - Clean Formatted Output

This is the simplest example of using the Claude Agent SDK.
It demonstrates how to:
- Import the SDK
- Make a basic query to Claude
- Receive and display the response with clean formatting

The output now clearly shows:
- Message types (SystemMessage, AssistantMessage, ResultMessage)
- Claude's actual response text
- Performance metrics (cost, timing, tokens)

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable
- Install dependencies: pip install -r requirements.txt

Usage:
    python examples/01_basic_query.py
"""

import anyio
from claude_agent_sdk import query


async def main():
    """
    Send a query to Claude and display responses with clean formatting.
    
    The query() function returns an async iterator that yields different
    message types:
    - SystemMessage: Session initialization info
    - AssistantMessage: Claude's actual response
    - ResultMessage: Performance summary (cost, timing, tokens)
    """
    print("=" * 60)
    print("🚀 SENDING QUERY TO CLAUDE")
    print("=" * 60)
    print()

    # Track message number
    message_num = 0
    
    async for message in query(prompt="What is 2 + 2? Please explain briefly."):
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
    print("✨ EXAMPLE COMPLETED!")
    print("=" * 60)


if __name__ == "__main__":
    # anyio.run() handles the async execution
    anyio.run(main)
