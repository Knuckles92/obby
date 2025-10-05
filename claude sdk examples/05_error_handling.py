"""
Example 5: Error Handling

This example demonstrates proper error handling when working with Claude Agent SDK.
Learn how to handle:
- Network errors
- API errors
- Invalid inputs
- Timeouts
- Rate limiting

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable
- Install dependencies: pip install -r requirements.txt

Usage:
    python examples/05_error_handling.py
"""

import anyio
from claude_agent_sdk import query, ClaudeSDKClient
from typing import Optional
import asyncio


async def basic_error_handling():
    """
    Demonstrate basic try-catch error handling.
    """
    print("=" * 60)
    print("🛡️  DEMO 1: BASIC ERROR HANDLING")
    print("=" * 60)
    print()

    try:
        print("🚀 Sending query to Claude...")
        print("-" * 60)

        # Track message number
        message_num = 0
        
        async for message in query(prompt="What is Python?"):
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
        print("✅ QUERY COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR OCCURRED")
        print("=" * 60)
        print(f"   • Error Type: {type(e).__name__}")
        print(f"   • Message: {str(e)}")
        print("   • Please check your API key and network connection.")
        print("=" * 60)


async def handle_missing_api_key():
    """
    Demonstrate handling missing API key error.
    """
    print("\n\n" + "=" * 60)
    print("🔑 DEMO 2: HANDLING MISSING API KEY")
    print("=" * 60)
    print()

    # This would typically raise an error if API key is not set
    try:
        # Attempt to create client without API key
        print("🔍 Checking for API key...")
        print("-" * 60)

        # In a real scenario, you might check environment variable first
        import os
        api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        print("✅ API key found!")
        print("=" * 60)

    except ValueError as e:
        print("\n" + "=" * 60)
        print("❌ CONFIGURATION ERROR")
        print("=" * 60)
        print(f"   • Error: {e}")
        print("\n🔧 TO FIX THIS:")
        print("   1. Get your API key from https://console.anthropic.com/")
        print("   2. Set it in your environment:")
        print("      export ANTHROPIC_API_KEY='your-api-key-here'")
        print("=" * 60)
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print(f"   • Error: {e}")
        print("=" * 60)


async def handle_network_errors():
    """
    Demonstrate handling network-related errors.
    """
    print("\n\nDemo 3: Handling Network Errors")
    print("=" * 50)

    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1}/{max_retries}...")

            async for message in query(prompt="Hello, Claude!"):
                print(message, end='', flush=True)

            print("\n✅ Success!")
            break  # Exit loop on success

        except ConnectionError as e:
            print(f"\n❌ Connection Error: {e}")

            if attempt < max_retries - 1:
                print(f"   Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print("   Max retries reached. Please check your network connection.")

        except TimeoutError as e:
            print(f"\n❌ Timeout Error: {e}")
            print("   The request took too long to complete.")

            if attempt < max_retries - 1:
                print(f"   Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)

        except Exception as e:
            print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
            break


async def handle_rate_limiting():
    """
    Demonstrate handling rate limiting errors.
    """
    print("\n\nDemo 4: Handling Rate Limiting")
    print("=" * 50)

    try:
        # Simulate multiple rapid requests
        queries = [
            "What is 1+1?",
            "What is 2+2?",
            "What is 3+3?",
        ]

        for i, prompt in enumerate(queries, 1):
            print(f"\nQuery {i}: {prompt}")

            async for message in query(prompt=prompt):
                print(message, end='', flush=True)

            # Add a small delay between requests to avoid rate limiting
            await asyncio.sleep(0.5)

        print("\n\n✅ All queries completed!")

    except Exception as e:
        if "rate limit" in str(e).lower():
            print(f"\n❌ Rate Limit Error: {e}")
            print("   Too many requests. Please wait before trying again.")
            print("   Consider implementing exponential backoff.")
        else:
            print(f"\n❌ Error: {e}")


async def graceful_degradation():
    """
    Demonstrate graceful degradation when Claude is unavailable.
    """
    print("\n\nDemo 5: Graceful Degradation")
    print("=" * 50)

    def fallback_response(prompt: str) -> str:
        """Provide a fallback when Claude is unavailable."""
        return (
            f"Claude is currently unavailable. "
            f"Your question '{prompt}' has been logged and will be answered later."
        )

    prompt = "What is machine learning?"

    try:
        print(f"Query: {prompt}\n")

        async for message in query(prompt=prompt):
            print(message, end='', flush=True)

        print("\n✅ Response from Claude")

    except Exception as e:
        print(f"❌ Claude unavailable: {e}")
        print("\n📝 Fallback response:")
        print(fallback_response(prompt))


async def safe_query(prompt: str, timeout: int = 30) -> Optional[str]:
    """
    A wrapper function that safely queries Claude with timeout and error handling.

    Args:
        prompt: The query to send to Claude
        timeout: Maximum time to wait for response in seconds

    Returns:
        Claude's response or None if error occurred
    """
    try:
        response_parts = []

        # Use asyncio.wait_for to implement timeout
        async def collect_response():
            async for message in query(prompt=prompt):
                response_parts.append(message)

        await asyncio.wait_for(collect_response(), timeout=timeout)

        return ''.join(response_parts)

    except asyncio.TimeoutError:
        print(f"⏱️  Query timed out after {timeout} seconds")
        return None
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return None


async def demo_safe_query():
    """
    Demonstrate using the safe query wrapper.
    """
    print("\n\nDemo 6: Safe Query Wrapper")
    print("=" * 50)

    result = await safe_query("What is Python?", timeout=30)

    if result:
        print(f"\n✅ Response received:")
        print(result)
    else:
        print("\n❌ Failed to get response")


async def main():
    """
    Run all error handling demonstrations.
    """
    print("=" * 60)
    print("🛡️  ERROR HANDLING DEMONSTRATION")
    print("=" * 60)
    print("Learn how to handle errors gracefully with Claude Agent SDK")
    print("=" * 60)
    print()

    await basic_error_handling()
    await handle_missing_api_key()
    # Uncomment others as needed
    # await handle_network_errors()
    # await handle_rate_limiting()
    # await graceful_degradation()
    # await demo_safe_query()

    print("\n" + "=" * 60)
    print("✨ ERROR HANDLING DEMONSTRATION COMPLETED!")
    print("=" * 60)
    print("\n📋 BEST PRACTICES:")
    print("   1. Always wrap SDK calls in try-except blocks")
    print("   2. Implement retry logic for transient failures")
    print("   3. Provide informative error messages to users")
    print("   4. Have fallback strategies when Claude is unavailable")
    print("   5. Respect rate limits and implement backoff strategies")
    print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
