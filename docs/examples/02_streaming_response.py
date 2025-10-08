"""
Example 2: Streaming Responses

This example demonstrates how to handle streaming responses from Claude.
Unlike the basic query, this shows you how to process responses in real-time
as they arrive, which is useful for:
- Providing immediate feedback to users
- Handling long responses
- Creating interactive experiences

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable
- Install dependencies: pip install -r requirements.txt

Usage:
    python examples/02_streaming_response.py
"""

import anyio
from claude_agent_sdk import query


async def main():
    """
    Demonstrate streaming responses from Claude.

    The query() function returns an async iterator that yields different
    message types:
    - SystemMessage: Session initialization info
    - AssistantMessage: Claude's actual response
    - ResultMessage: Performance summary (cost, timing, tokens)
    """
    print("=" * 60)
    print("🚀 STREAMING RESPONSE FROM CLAUDE")
    print("=" * 60)
    print()

    # Track message number
    message_num = 0
    
    async for message in query(prompt="Write a short 4-line poem about Python programming"):
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
    print("✨ STREAMING COMPLETED!")
    print("=" * 60)


async def multi_query_demo():
    """
    Demonstrate multiple streaming queries in sequence.
    """
    print("\n\n" + "=" * 60)
    print("🔄 MULTIPLE QUERY DEMO")
    print("=" * 60)
    print()

    queries = [
        "What is Python?",
        "Name three popular Python frameworks.",
        "What is async/await in Python?"
    ]

    for i, prompt in enumerate(queries, 1):
        print(f"📝 QUERY {i}: {prompt}")
        print("-" * 60)
        
        # Track message number for this query
        message_num = 0
        
        async for message in query(prompt=prompt):
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
        print(f"✨ QUERY {i} COMPLETED!")
        print("=" * 60)
        print()


if __name__ == "__main__":
    # Run both demos
    anyio.run(main)
    anyio.run(multi_query_demo)
