#!/usr/bin/env python3
"""Check if agent logs are being written."""

import sys
sys.path.insert(0, '.')

from database.models import db

# Count all logs
result = db.execute_query("SELECT COUNT(*) as count FROM agent_action_logs")
print(f"Total logs in database: {result[0]['count']}")

# Get recent logs
recent = db.execute_query("""
    SELECT session_id, phase, operation, timestamp 
    FROM agent_action_logs 
    ORDER BY timestamp DESC 
    LIMIT 10
""")

if recent:
    print("\nRecent logs:")
    for log in recent:
        print(f"  {log['timestamp']} - {log['phase']}: {log['operation']} (session: {log['session_id'][:8]}...)")
else:
    print("\nNo logs found in database!")
