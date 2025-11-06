#!/usr/bin/env python3
"""
Comprehensive test to verify the full logging flow during summary generation.
"""

import sys
import asyncio
sys.path.insert(0, '.')

from pathlib import Path
from ai.claude_agent_client import ClaudeAgentClient
from database.models import db
import uuid

async def test_summary_generation():
    """Test that logging works during actual summary generation."""
    
    print("=" * 60)
    print("Testing Claude Agent Client Summary Generation with Logging")
    print("=" * 60)
    
    # Create test files
    test_file = Path("test_file.md")
    test_file.write_text("# Test\n\nThis is a test file for summary generation.")
    
    try:
        # Create client with session_id (mimicking session_summary_service)
        session_id = str(uuid.uuid4())
        print(f"\n1. Creating ClaudeAgentClient with session_id: {session_id}")
        
        client = ClaudeAgentClient(
            working_dir=Path.cwd(),
            session_id=session_id
        )
        
        print(f"   - Logging service initialized: {client.logging_service is not None}")
        print(f"   - Logging service enabled: {client.logging_service.enabled if client.logging_service else 'N/A'}")
        print(f"   - Session ID: {client.session_id}")
        
        # Check initial log count
        initial_logs = db.execute_query(
            "SELECT COUNT(*) as count FROM agent_action_logs WHERE session_id = ?",
            (session_id,)
        )
        print(f"\n2. Initial log count: {initial_logs[0]['count']}")
        
        # Generate summary (this should log multiple operations)
        print(f"\n3. Generating summary for test file...")
        print("   (This should create multiple log entries)")
        
        try:
            summary = await client.summarize_session(
                changed_files=[str(test_file)],
                time_range="test period",
                working_dir=Path.cwd()
            )
            
            print(f"\n4. Summary generated successfully!")
            print(f"   Length: {len(summary)} characters")
            
        except Exception as e:
            print(f"\n4. Summary generation failed: {e}")
            print("   (This is expected if ANTHROPIC_API_KEY is not set)")
        
        # Check final log count
        final_logs = db.execute_query(
            "SELECT * FROM agent_action_logs WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        
        print(f"\n5. Final log count: {len(final_logs)}")
        
        if len(final_logs) > 0:
            print("\n6. Log entries created:")
            for i, log in enumerate(final_logs, 1):
                print(f"   {i}. [{log['phase']}] {log['operation']}")
                if log['current_file']:
                    print(f"      File: {log['current_file']}")
            print("\n✅ SUCCESS: Logging is working during summary generation!")
        else:
            print("\n❌ FAILURE: No logs were created during summary generation!")
            print("   This suggests the logging calls are not being executed.")
        
        # Test the service's query methods
        print(f"\n7. Testing AgentLoggingService.get_session_logs()...")
        from services.agent_logging_service import get_agent_logging_service
        service = get_agent_logging_service()
        service_logs = service.get_session_logs(session_id)
        print(f"   Retrieved {len(service_logs)} logs via service")
        
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        print(f"\n8. Cleanup complete")

if __name__ == "__main__":
    asyncio.run(test_summary_generation())
