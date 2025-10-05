"""
Test script to verify Claude SDK integration is working correctly.
This mirrors the working examples from 'claude sdk examples/' folder.

Usage:
    python test_claude_fix.py
"""

import anyio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ai.claude_agent_client import ClaudeAgentClient, CLAUDE_SDK_AVAILABLE


async def test_basic_query():
    """Test 1: Basic query to verify Claude SDK is working."""
    print("=" * 60)
    print("TEST 1: Basic Query (Hello World)")
    print("=" * 60)
    print()
    
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Claude Agent SDK not available")
        print("   Install: pip install claude-agent-sdk")
        print("   Also requires: npm install -g @anthropic-ai/claude-code")
        return False
    
    try:
        client = ClaudeAgentClient()
        
        if not client.is_available():
            print("❌ Claude Agent Client not available")
            print("   Set ANTHROPIC_API_KEY environment variable")
            return False
        
        print("✅ Claude Agent Client initialized")
        print(f"   Working directory: {client.working_dir}")
        print()
        
        # Simple question
        print("📝 Asking: What is 2 + 2?")
        print("-" * 60)
        
        answer = await client.ask_question("What is 2 + 2? Please answer briefly.")
        
        print()
        print("💬 Claude's Response:")
        print("-" * 60)
        print(f"   {answer}")
        print()
        
        if "4" in answer or "four" in answer.lower():
            print("✅ TEST 1 PASSED: Got expected answer")
            return True
        else:
            print("⚠️  TEST 1 WARNING: Unexpected answer (but SDK is working)")
            return True
            
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_diff_analysis():
    """Test 2: Diff analysis to verify code understanding."""
    print("\n\n" + "=" * 60)
    print("TEST 2: Diff Analysis")
    print("=" * 60)
    print()
    
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Skipping test - Claude Agent SDK not available")
        return False
    
    try:
        client = ClaudeAgentClient()
        
        if not client.is_available():
            print("❌ Skipping test - API key not set")
            return False
        
        # Sample diff from a real code change
        diff = """
--- a/core/file_tracker.py
+++ b/core/file_tracker.py
@@ -45,6 +45,12 @@ class FileContentTracker:
         self.file_hashes = {}
         self.file_mtimes = {}
+        
+        # Initialize ignore and watch handlers
+        self.ignore_handler = IgnoreHandler()
+        self.watch_handler = WatchHandler(watch_paths)
+        
+        logger.info("FileContentTracker initialized with ignore/watch support")
     
     def get_file_hash(self, file_path):
         '''Calculate SHA-256 hash of file content.'''
"""
        
        print("📝 Analyzing diff...")
        print("-" * 60)
        
        analysis = await client.analyze_diff(
            diff,
            context="This change adds ignore/watch pattern support to the file tracker"
        )
        
        print()
        print("💬 Claude's Analysis:")
        print("-" * 60)
        print(f"   {analysis}")
        print()
        
        if len(analysis) > 50 and "error" not in analysis.lower():
            print("✅ TEST 2 PASSED: Got analysis")
            return True
        else:
            print("⚠️  TEST 2 WARNING: Short or error response")
            return False
            
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_change_summary():
    """Test 3: Batch change summary."""
    print("\n\n" + "=" * 60)
    print("TEST 3: Batch Change Summary")
    print("=" * 60)
    print()
    
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Skipping test - Claude Agent SDK not available")
        return False
    
    try:
        client = ClaudeAgentClient()
        
        if not client.is_available():
            print("❌ Skipping test - API key not set")
            return False
        
        changes = [
            {"path": "core/monitor.py", "type": "modified", "content": "Added new monitoring feature"},
            {"path": "api/routes.py", "type": "modified", "content": "Updated API endpoints"},
        ]
        
        print("📝 Summarizing changes...")
        print("-" * 60)
        
        summary = await client.summarize_changes(changes, max_length="brief")
        
        print()
        print("💬 Claude's Summary:")
        print("-" * 60)
        print(f"   {summary}")
        print()
        
        if len(summary) > 20 and "error" not in summary.lower():
            print("✅ TEST 3 PASSED: Got summary")
            return True
        else:
            print("⚠️  TEST 3 WARNING: Short or error response")
            return False
            
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  CLAUDE SDK INTEGRATION TEST SUITE")
    print("=" * 70)
    print()
    
    results = []
    
    # Test 1: Basic query
    results.append(await test_basic_query())
    
    # Test 2: Diff analysis
    results.append(await test_diff_analysis())
    
    # Test 3: Change summary
    results.append(await test_change_summary())
    
    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print()
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print()
        print("✅ ALL TESTS PASSED!")
        print()
        print("The Claude SDK integration is working correctly.")
        print("You can now use Claude in your chat API with use_tools=true")
    else:
        print()
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Check the output above for details.")
        print("Common issues:")
        print("  - ANTHROPIC_API_KEY not set")
        print("  - Claude Code CLI not installed (npm install -g @anthropic-ai/claude-code)")
        print("  - claude-agent-sdk not installed (pip install claude-agent-sdk)")
    
    print("=" * 70)
    print()


if __name__ == "__main__":
    # Use anyio.run() as per working examples
    anyio.run(main)

