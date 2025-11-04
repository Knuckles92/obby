#!/usr/bin/env python3
"""Quick script to check if agent_action_logs table exists."""

import sys
sys.path.insert(0, '.')

from database.models import db

# Check if table exists
result = db.execute_query(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_action_logs'"
)

print(f"Table exists: {bool(result)}")

if result:
    print("Table found!")
    # Check structure
    cols = db.execute_query("PRAGMA table_info(agent_action_logs)")
    print(f"\nColumns ({len(cols)}):")
    for col in cols:
        print(f"  - {col['name']} ({col['type']})")
else:
    print("Table NOT found - migration needs to be run!")
