#!/usr/bin/env python3
"""Test if agent logs are accessible via API."""

import requests
import json

BASE_URL = "http://localhost:8001"

print("Testing agent logging API endpoints...\n")

# Test 1: Get recent logs
print("1. Testing GET /api/admin/agent-logs")
response = requests.get(f"{BASE_URL}/api/admin/agent-logs")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Total logs: {data.get('total', 0)}")
    print(f"   Logs returned: {len(data.get('logs', []))}")
    if data.get('logs'):
        print(f"   First log: {data['logs'][0].get('operation', 'N/A')}")
else:
    print(f"   Error: {response.text}")

print()

# Test 2: Get sessions
print("2. Testing GET /api/admin/agent-logs/sessions")
response = requests.get(f"{BASE_URL}/api/admin/agent-logs/sessions")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Total sessions: {data.get('total', 0)}")
    print(f"   Sessions returned: {len(data.get('sessions', []))}")
    if data.get('sessions'):
        print(f"   First session ID: {data['sessions'][0].get('session_id', 'N/A')[:8]}...")
        print(f"   First session logs: {data['sessions'][0].get('log_count', 0)}")
else:
    print(f"   Error: {response.text}")

print()

# Test 3: Get stats
print("3. Testing GET /api/admin/agent-logs/stats")
response = requests.get(f"{BASE_URL}/api/admin/agent-logs/stats")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    stats = data.get('stats', {})
    print(f"   Total operations: {stats.get('total_operations', 0)}")
    print(f"   Unique sessions: {stats.get('unique_sessions', 0)}")
else:
    print(f"   Error: {response.text}")
