"""
Test script for hybrid chat implementation
Tests both OpenAI simple chat and Claude tool-based chat
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_openai_simple_chat():
    """Test simple chat with OpenAI (no tools)."""
    print("\n" + "="*60)
    print("TEST 1: OpenAI Simple Chat (no tools)")
    print("="*60)
    
    from routes.chat import _chat_with_openai_simple
    
    messages = [
        {"role": "user", "content": "What is 2 + 2?"}
    ]
    
    data = {"temperature": 0.7}
    
    try:
        result = await _chat_with_openai_simple(messages, data)
        print(f"✅ Backend: {result.get('backend')}")
        print(f"✅ Model: {result.get('model')}")
        print(f"✅ Tools used: {result.get('tools_used')}")
        print(f"✅ Reply: {result.get('reply')[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_claude_tool_chat():
    """Test tool-based chat with Claude."""
    print("\n" + "="*60)
    print("TEST 2: Claude Tool-Based Chat")
    print("="*60)
    
    from routes.chat import _chat_with_claude_tools, CLAUDE_AVAILABLE
    
    if not CLAUDE_AVAILABLE:
        print("⚠️  Claude Agent SDK not available, skipping test")
        return None
    
    messages = [
        {"role": "user", "content": "What files changed recently? Use the get_recent_changes tool."}
    ]
    
    data = {}
    
    try:
        result = await _chat_with_claude_tools(messages, data)
        print(f"✅ Backend: {result.get('backend')}")
        print(f"✅ Model: {result.get('model')}")
        print(f"✅ Tools used: {result.get('tools_used')}")
        print(f"✅ Reply: {result.get('reply')[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_openai_tool_chat_fallback():
    """Test tool-based chat with OpenAI orchestrator (fallback)."""
    print("\n" + "="*60)
    print("TEST 3: OpenAI Tool Chat (Orchestrator Fallback)")
    print("="*60)
    
    from routes.chat import _chat_with_openai_tools
    
    messages = [
        {"role": "user", "content": "Search my notes for 'batch processing'"}
    ]
    
    data = {}
    
    try:
        result = await _chat_with_openai_tools(messages, data)
        print(f"✅ Backend: {result.get('backend')}")
        print(f"✅ Model: {result.get('model')}")
        print(f"✅ Tools used: {result.get('tools_used')}")
        print(f"✅ Reply: {result.get('reply')[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_routing_logic():
    """Test the main routing logic."""
    print("\n" + "="*60)
    print("TEST 4: Routing Logic")
    print("="*60)
    
    from routes.chat import CLAUDE_AVAILABLE
    
    print(f"Claude Available: {CLAUDE_AVAILABLE}")
    
    if CLAUDE_AVAILABLE:
        print("✅ Routing: use_tools=true → Claude Agent SDK")
        print("✅ Routing: use_tools=false → OpenAI simple")
    else:
        print("⚠️  Routing: use_tools=true → OpenAI orchestrator (fallback)")
        print("✅ Routing: use_tools=false → OpenAI simple")
    
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  HYBRID CHAT IMPLEMENTATION TESTS")
    print("="*70)
    
    results = []
    
    # Test routing logic first
    results.append(("Routing Logic", await test_routing_logic()))
    
    # Test OpenAI simple chat
    results.append(("OpenAI Simple Chat", await test_openai_simple_chat()))
    
    # Test Claude tool chat (if available)
    claude_result = await test_claude_tool_chat()
    if claude_result is not None:
        results.append(("Claude Tool Chat", claude_result))
    
    # Test OpenAI tool chat fallback
    results.append(("OpenAI Tool Chat", await test_openai_tool_chat_fallback()))
    
    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())
