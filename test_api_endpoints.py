#!/usr/bin/env python3
"""Test if the agent logs API endpoints return data correctly."""

import sys
import requests
import json

sys.path.insert(0, '.')

print("Testing Agent Logs API Endpoints")
print("=" * 60)

# Make sure backend is running
BASE_URL = "http://localhost:8001"

try:
    # Test sessions endpoint
    print("\n1. Testing /api/admin/agent-logs/sessions")
    response = requests.get(f"{BASE_URL}/api/admin/agent-logs/sessions?page=1&page_size=10")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Status: {response.status_code}")
        print(f"   Sessions found: {len(data.get('sessions', []))}")
        
        if data.get('sessions'):
            print(f"\n   Recent sessions:")
            for session in data['sessions'][:3]:
                print(f"   - Session: {session['session_id'][:8]}...")
                print(f"     Operations: {session['operation_count']}")
                print(f"     Files: {session['files_processed']}")
                print(f"     Start: {session['start_time']}")
        else:
            print("   ⚠ No sessions found!")
    else:
        print(f"   ✗ Error: {response.status_code}")
        print(f"   {response.text}")

    # Test stats endpoint
    print("\n2. Testing /api/admin/agent-logs/stats")
    response = requests.get(f"{BASE_URL}/api/admin/agent-logs/stats")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Status: {response.status_code}")
        print(f"   Total logs: {data.get('total_logs', 0)}")
        
        if 'last_24_hours' in data:
            print(f"   Last 24h operations: {data['last_24_hours'].get('operations', 0)}")
    else:
        print(f"   ✗ Error: {response.status_code}")
        print(f"   {response.text}")

except requests.exceptions.ConnectionError:
    print("\n✗ ERROR: Could not connect to backend server")
    print("  Make sure the backend is running: python backend.py")
except Exception as e:
    print(f"\n✗ ERROR: {e}")

print("\n" + "=" * 60)
