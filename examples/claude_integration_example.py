"""
Claude Agent SDK Integration Example
=====================================

Demonstrates how to use Claude Agent SDK alongside OpenAI in Obby's batch processing.
Shows both simple queries and advanced agentic workflows.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.claude_agent_client import ClaudeAgentClient, create_obby_mcp_server, CLAUDE_SDK_AVAILABLE
from ai.openai_client import OpenAIClient

if CLAUDE_SDK_AVAILABLE:
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions


async def example_1_simple_diff_analysis():
    """Example 1: Simple diff analysis with Claude."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Simple Diff Analysis")
    print("="*60)
    
    client = ClaudeAgentClient()
    
    if not client.is_available():
        print("❌ Claude Agent SDK not available")
        return
    
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
    
    print("\n📝 Analyzing diff...")
    analysis = await client.analyze_diff(
        diff,
        context="This change adds ignore/watch pattern support to the file tracker"
    )
    
    print(f"\n✅ Claude's Analysis:\n{analysis}")


async def example_2_batch_changes_comparison():
    """Example 2: Compare OpenAI vs Claude for batch summaries."""
    print("\n" + "="*60)
    print("EXAMPLE 2: OpenAI vs Claude Batch Summary Comparison")
    print("="*60)
    
    # Sample changes
    changes = [
        {
            "path": "core/monitor.py",
            "type": "modified",
            "content": "Added periodic_check method for scheduled file scanning"
        },
        {
            "path": "core/file_tracker.py",
            "type": "modified",
            "content": "Integrated IgnoreHandler and WatchHandler for pattern filtering"
        },
        {
            "path": "api/routes.py",
            "type": "modified",
            "content": "Added new endpoint for batch AI trigger with async support"
        },
    ]
    
    # OpenAI summary
    print("\n🤖 OpenAI Summary:")
    openai_client = OpenAIClient()
    if openai_client.is_available():
        context = "\n".join([f"- {c['path']}: {c['content']}" for c in changes])
        openai_summary = openai_client.summarize_minimal(context)
        print(openai_summary)
    else:
        print("OpenAI not available")
    
    # Claude summary
    print("\n🧠 Claude Summary:")
    claude_client = ClaudeAgentClient()
    if claude_client.is_available():
        claude_summary = await claude_client.summarize_changes(changes, max_length="moderate")
        print(claude_summary)
    else:
        print("Claude not available")


async def example_3_interactive_code_review():
    """Example 3: Interactive code review session with Claude."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Interactive Code Review")
    print("="*60)
    
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Claude Agent SDK not available")
        return
    
    client = ClaudeAgentClient()
    
    if not client.is_available():
        print("❌ Claude not configured")
        return
    
    print("\n🔍 Starting interactive code review session...")
    print("Claude will analyze the file and provide insights.\n")
    
    prompt = """
    Review the file 'ai/batch_processor.py' and provide:
    1. A brief overview of what it does
    2. Key design patterns used
    3. Potential improvements or concerns
    
    Keep it concise and technical.
    """
    
    async for response in client.interactive_analysis(prompt, allow_file_edits=False):
        print(response)


async def example_4_custom_tools_with_mcp():
    """Example 4: Using custom Obby tools via MCP server."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Custom Obby Tools with MCP Server")
    print("="*60)
    
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Claude Agent SDK not available")
        return
    
    try:
        # Create MCP server with Obby tools
        obby_server = create_obby_mcp_server()
        
        # Configure Claude to use Obby tools
        options = ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            mcp_servers={"obby": obby_server},
            allowed_tools=[
                "Read",
                "mcp__obby__get_file_history",
                "mcp__obby__get_recent_changes"
            ],
            max_turns=5,
        )
        
        print("\n🔧 Claude now has access to Obby-specific tools:")
        print("  - get_file_history: Query file change history")
        print("  - get_recent_changes: Get recent project changes")
        
        async with ClaudeSDKClient(options=options) as client:
            # Ask Claude to use the custom tools
            await client.query(
                "Use the get_recent_changes tool to show me the last 5 changes, "
                "then summarize what's been happening in the project."
            )
            
            print("\n💬 Claude's response:\n")
            async for message in client.receive_response():
                print(message)
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_5_hybrid_ai_workflow():
    """Example 5: Hybrid workflow using both OpenAI and Claude."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Hybrid AI Workflow (OpenAI + Claude)")
    print("="*60)
    
    openai_client = OpenAIClient()
    claude_client = ClaudeAgentClient()
    
    # Step 1: Use OpenAI for quick structured summary
    print("\n📊 Step 1: OpenAI generates structured summary...")
    context = """
    Recent changes:
    - Added async batch processing with timeout controls
    - Integrated ignore/watch pattern handlers
    - Updated API endpoints for batch triggers
    """
    
    if openai_client.is_available():
        openai_summary = openai_client.summarize_minimal(context)
        print(f"OpenAI Summary:\n{openai_summary}")
    else:
        openai_summary = context
        print("OpenAI not available, using raw context")
    
    # Step 2: Use Claude for deeper analysis and questions
    print("\n🧠 Step 2: Claude provides deeper analysis...")
    
    if claude_client.is_available():
        analysis_prompt = f"""
        Based on this summary of recent changes:
        
        {openai_summary}
        
        Provide:
        1. Potential architectural implications
        2. Suggested next steps or improvements
        3. Any concerns about the changes
        """
        
        claude_analysis = await claude_client.ask_question(analysis_prompt)
        print(f"Claude Analysis:\n{claude_analysis}")
    else:
        print("Claude not available")
    
    print("\n✅ Hybrid workflow complete!")
    print("💡 This approach combines OpenAI's speed with Claude's agentic capabilities")


async def example_6_safe_bash_hooks():
    """Example 6: Using hooks to validate bash commands (security)."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Security Hooks for Bash Commands")
    print("="*60)
    
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Claude Agent SDK not available")
        return
    
    from claude_agent_sdk import HookMatcher
    
    # Define a security hook
    async def validate_bash_command(input_data, tool_use_id, context):
        """Hook to validate bash commands before execution."""
        tool_name = input_data.get("tool_name")
        tool_input = input_data.get("tool_input", {})
        
        if tool_name != "Bash":
            return {}
        
        command = tool_input.get("command", "")
        
        # Block dangerous patterns
        dangerous_patterns = ["rm -rf", "sudo", "chmod 777", "curl", "wget"]
        
        for pattern in dangerous_patterns:
            if pattern in command:
                print(f"🚫 BLOCKED: Command contains dangerous pattern '{pattern}'")
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Blocked dangerous pattern: {pattern}",
                    }
                }
        
        print(f"✅ ALLOWED: {command}")
        return {}
    
    # Configure Claude with security hooks
    options = ClaudeAgentOptions(
        cwd=str(Path.cwd()),
        allowed_tools=["Bash", "Read"],
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[validate_bash_command]),
            ],
        },
    )
    
    print("\n🔒 Testing security hooks...\n")
    
    async with ClaudeSDKClient(options=options) as client:
        # Test 1: Safe command
        print("Test 1: Safe command")
        await client.query("Run: echo 'Hello from Obby'")
        async for msg in client.receive_response():
            pass
        
        print("\nTest 2: Dangerous command (should be blocked)")
        await client.query("Run: rm -rf /tmp/test")
        async for msg in client.receive_response():
            pass


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("  CLAUDE AGENT SDK INTEGRATION EXAMPLES FOR OBBY")
    print("="*70)
    
    examples = [
        ("Simple Diff Analysis", example_1_simple_diff_analysis),
        ("OpenAI vs Claude Comparison", example_2_batch_changes_comparison),
        ("Interactive Code Review", example_3_interactive_code_review),
        ("Custom MCP Tools", example_4_custom_tools_with_mcp),
        ("Hybrid AI Workflow", example_5_hybrid_ai_workflow),
        ("Security Hooks", example_6_safe_bash_hooks),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\n" + "-"*70)
    
    # Run all examples
    for name, example_func in examples:
        try:
            await example_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
    
    print("\n" + "="*70)
    print("  EXAMPLES COMPLETE")
    print("="*70)
    print("\n💡 Key Takeaways:")
    print("  • Claude Agent SDK provides agentic capabilities")
    print("  • Custom MCP tools integrate with your database")
    print("  • Hooks enable security and validation")
    print("  • Hybrid workflows combine OpenAI speed + Claude depth")
    print("  • Interactive sessions enable complex multi-step tasks")
    print("\n📚 Next Steps:")
    print("  • Install: pip install claude-agent-sdk")
    print("  • Install: npm install -g @anthropic-ai/claude-code")
    print("  • Set ANTHROPIC_API_KEY environment variable")
    print("  • Integrate into BatchAIProcessor for production use")


if __name__ == "__main__":
    asyncio.run(main())
