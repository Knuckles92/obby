#!/usr/bin/env python3
"""Test if ClaudeAgentClient initializes logging service."""

import sys
sys.path.insert(0, '.')

from ai.claude_agent_client import ClaudeAgentClient
from pathlib import Path
import uuid

# Create client with session_id but no progress_callback (like session_summary_service does)
session_id = str(uuid.uuid4())
print(f"Creating ClaudeAgentClient with session_id={session_id}")

client = ClaudeAgentClient(
    working_dir=Path.cwd(),
    session_id=session_id
)

print(f"Client session_id: {client.session_id}")
print(f"Client logging_service: {client.logging_service}")
print(f"Client progress_callback: {client.progress_callback}")
print(f"Client store_agent_logs: {client.store_agent_logs}")

if client.logging_service:
    print(f"Logging service enabled: {client.logging_service.enabled}")
    
    # Try emitting a progress event
    print("\nTrying to emit a progress event...")
    client._emit_progress_event(
        phase='data_collection',
        operation='Test Operation',
        details={'test': 'data'}
    )
    
    # Check database
    from database.models import db
    logs = db.execute_query(
        "SELECT * FROM agent_action_logs WHERE session_id = ?",
        (session_id,)
    )
    print(f"\nFound {len(logs)} logs in database for this session")
    if logs:
        print("SUCCESS: Event was logged!")
        for log in logs:
            print(f"  - {log['phase']}: {log['operation']}")
    else:
        print("FAILED: Event was not logged to database")
else:
    print("ERROR: Logging service is None!")
