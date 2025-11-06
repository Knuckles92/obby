#!/usr/bin/env python3
"""Test script to verify agent logging functionality."""

import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from services.agent_logging_service import get_agent_logging_service

def test_logging():
    """Test basic logging functionality."""
    print("Testing agent logging service...")

    # Get service
    service = get_agent_logging_service()
    print(f"Service enabled: {service.enabled}")
    print(f"Service verbosity: {service.verbosity}")

    # Create test session
    test_session_id = str(uuid.uuid4())
    print(f"\nTest session ID: {test_session_id}")

    # Log a test operation
    print("\nLogging test operation...")
    success = service.log_operation(
        session_id=test_session_id,
        phase='analysis',
        operation='Test Operation',
        details={'test': 'data'},
        files_processed=1,
        total_files=5,
        current_file='test.md',
        timing={'start': datetime.now().isoformat()}
    )

    print(f"Log operation result: {success}")

    # Retrieve the log
    print("\nRetrieving logged operations...")
    logs = service.get_session_logs(test_session_id)
    print(f"Found {len(logs)} logs for session")

    if logs:
        log = logs[0]
        print(f"\nLog entry:")
        print(f"  ID: {log['id']}")
        print(f"  Session: {log['session_id']}")
        print(f"  Phase: {log['phase']}")
        print(f"  Operation: {log['operation']}")
        print(f"  Files processed: {log['files_processed']}")
        print(f"  Current file: {log['current_file']}")

    # Get overall count
    total_logs = service.count_logs()
    print(f"\nTotal logs in database: {total_logs}")

    # Cleanup test log
    print(f"\nCleaning up test session...")
    service.delete_session_logs(test_session_id)
    print("Test complete!")

if __name__ == '__main__':
    try:
        test_logging()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
