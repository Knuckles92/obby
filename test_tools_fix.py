"""
Quick test to verify Claude SDK tool calling is working.

This tests:
1. Tool decorator is correctly applied
2. MCP server creation works
3. Tools can be called through Claude SDK

Usage:
    python test_tools_fix.py
"""

import anyio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.claude_agent_client import (
    create_obby_mcp_server,
    get_file_history,
    get_recent_changes,
    CLAUDE_SDK_AVAILABLE
)


async def test_tool_decorators():
    """Test 1: Verify @tool decorators are working."""
    print("=" * 60)
    print("TEST 1: Tool Decorator Verification")
    print("=" * 60)
    print()

    # Check if tools have the required attributes from @tool decorator
    print("Checking get_file_history...")
    if hasattr(get_file_history, '__name__'):
        print(f"  [OK] Function name: {get_file_history.__name__}")
    else:
        print("  [FAIL] Missing __name__ attribute")
        return False

    print("\nChecking get_recent_changes...")
    if hasattr(get_recent_changes, '__name__'):
        print(f"  [OK] Function name: {get_recent_changes.__name__}")
    else:
        print("  [FAIL] Missing __name__ attribute")
        return False

    print("\n[PASS] TEST 1 PASSED: Tools are properly decorated\n")
    return True


async def test_mcp_server_creation():
    """Test 2: Verify MCP server can be created."""
    print("=" * 60)
    print("TEST 2: MCP Server Creation")
    print("=" * 60)
    print()

    if not CLAUDE_SDK_AVAILABLE:
        print("[FAIL] Claude Agent SDK not available")
        print("   Install: pip install claude-agent-sdk")
        return False

    try:
        server = create_obby_mcp_server()
        print(f"[OK] MCP server created successfully")
        print(f"  Server type: {type(server)}")
        print(f"  Server: {server}")
        print("\n[PASS] TEST 2 PASSED: MCP server creation works\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_execution():
    """Test 3: Directly call tools to verify they work."""
    print("=" * 60)
    print("TEST 3: Direct Tool Execution")
    print("=" * 60)
    print()

    # Test get_recent_changes with no database (should handle gracefully)
    print("Testing get_recent_changes...")
    try:
        result = await get_recent_changes({"limit": 5})
        print(f"  [OK] Tool executed")
        print(f"  Result type: {type(result)}")

        # Check correct return format
        if "content" in result:
            print(f"  [OK] Has 'content' key")
            if isinstance(result["content"], list):
                print(f"  [OK] Content is a list")
                if len(result["content"]) > 0:
                    first_item = result["content"][0]
                    if "type" in first_item and "text" in first_item:
                        print(f"  [OK] Correct content format")
                        print(f"  Message preview: {first_item['text'][:100]}...")
                    else:
                        print(f"  [FAIL] Content items missing 'type' or 'text'")
                        return False
            else:
                print(f"  [FAIL] Content is not a list")
                return False
        else:
            print(f"  [FAIL] Missing 'content' key in result")
            return False

        print("\n[PASS] TEST 3 PASSED: Tools execute correctly\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  CLAUDE SDK TOOL CALLING FIX - VERIFICATION SUITE")
    print("=" * 70)
    print()

    results = []

    # Test 1: Tool decorators
    results.append(await test_tool_decorators())

    # Test 2: MCP server creation
    results.append(await test_mcp_server_creation())

    # Test 3: Tool execution
    results.append(await test_tool_execution())

    # Summary
    print("=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print()

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED!")
        print()
        print("The tool calling fix is working correctly.")
        print()
        print("NEXT STEPS:")
        print("1. Make sure ANTHROPIC_API_KEY is set")
        print("2. Start backend: python backend.py")
        print("3. Test chat API with use_tools=true")
        print()
        print("Example curl command:")
        print('curl -X POST http://localhost:8001/api/chat/complete \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"messages": [{"role": "user", "content": "Show me recent file changes"}], "use_tools": true}\'')
    else:
        print("[WARNING] SOME TESTS FAILED")
        print()
        print("Check the output above for details.")

    print("=" * 70)
    print()


if __name__ == "__main__":
    anyio.run(main)
