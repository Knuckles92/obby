#!/usr/bin/env python3
"""Trigger a summary update to generate agent logs."""

import requests
import time

BASE_URL = "http://localhost:8001"

print("Triggering session summary update to generate agent logs...\n")

# Trigger summary update
response = requests.post(
    f"{BASE_URL}/api/session-summary/update",
    json={"force": True}
)

print(f"Update trigger status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Response: {data.get('message', 'N/A')}")
else:
    print(f"Error: {response.text}")

print("\nWaiting 3 seconds for processing...")
time.sleep(3)

# Now check if logs were created
print("\nChecking for new agent logs...")
response = requests.get(f"{BASE_URL}/api/admin/agent-logs?limit=10")
if response.status_code == 200:
    data = response.json()
    print(f"Total logs: {data.get('total', 0)}")
    if data.get('logs'):
        print(f"\nRecent logs:")
        for log in data['logs'][:5]:
            print(f"  - {log.get('phase', 'N/A')}: {log.get('operation', 'N/A')}")
    else:
        print("No logs returned from API (but they might be in database)")
else:
    print(f"Error getting logs: {response.text}")
