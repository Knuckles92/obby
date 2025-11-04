#!/usr/bin/env python3
"""Test if agent logging service is actually enabled."""

import sys
sys.path.insert(0, '.')

from services.agent_logging_service import get_agent_logging_service

# Get service
service = get_agent_logging_service()
print(f"Service enabled: {service.enabled}")
print(f"Service verbosity: {service.verbosity}")

# Try logging
import uuid
test_session = str(uuid.uuid4())
result = service.log_operation(
    session_id=test_session,
    phase='data_collection',
    operation='Test Operation',
    details={'test': 'data'}
)

print(f"Log operation returned: {result}")

# Check if it was logged
from database.models import db
logs = db.execute_query(
    "SELECT * FROM agent_action_logs WHERE session_id = ?",
    (test_session,)
)
print(f"Found {len(logs)} logs for test session")
if logs:
    print("SUCCESS: Logging is working!")
else:
    print("FAILED: Log not found in database")
