#!/usr/bin/env python3
"""Test the fixed _parse_log_row directly."""

import sys
sys.path.insert(0, '.')

# Force reimport
if 'services.agent_logging_service' in sys.modules:
    del sys.modules['services.agent_logging_service']

from services.agent_logging_service import get_agent_logging_service
from database.models import db

# Get a real log row from database
rows = db.execute_query(
    "SELECT * FROM agent_action_logs ORDER BY timestamp DESC LIMIT 1"
)

if rows:
    row = rows[0]
    print(f"Raw row type: {type(row)}")
    print(f"Raw row: {dict(row)}")
    
    # Try parsing it
    service = get_agent_logging_service()
    parsed = service._parse_log_row(row)
    
    print(f"\nParsed successfully!")
    print(f"Session ID: {parsed.get('session_id', 'N/A')[:8]}...")
    print(f"Phase: {parsed.get('phase', 'N/A')}")
    print(f"Operation: {parsed.get('operation', 'N/A')}")
else:
    print("No logs found in database")
