#!/usr/bin/env python3
"""
Test script to verify both real-time and periodic monitoring work together.
"""

import time
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_monitoring():
    print("[TEST] Testing Obby Monitoring System")
    print("=" * 50)
    
    # 1. Check initial status
    print("\n1. Checking initial status...")
    response = requests.get(f"{BASE_URL}/api/status")
    status = response.json()
    print(f"   Monitoring active: {status['isActive']}")
    
    # 2. Update configuration to enable periodic checking with 10s interval
    print("\n2. Updating configuration...")
    config_data = {
        "checkInterval": 10,
        "periodicCheckEnabled": True
    }
    response = requests.put(f"{BASE_URL}/api/config", json=config_data)
    print(f"   Config update: {response.json()['message']}")
    
    # 3. Start monitoring
    print("\n3. Starting monitoring...")
    response = requests.post(f"{BASE_URL}/api/monitor/start")
    print(f"   Start result: {response.json()['message']}")
    
    # 4. Create a test file
    test_file = Path("notes/test_both_modes.md")
    print(f"\n4. Creating test file: {test_file}")
    test_file.write_text("# Test File\n\nInitial content for testing both monitoring modes.")
    
    # 5. Wait for real-time detection
    print("\n5. Waiting 2 seconds for real-time detection...")
    time.sleep(2)
    
    # Check events
    response = requests.get(f"{BASE_URL}/api/events?limit=10")
    events = response.json()
    real_time_events = [e for e in events if 'test_both_modes' in e['path']]
    print(f"   Real-time events detected: {len(real_time_events)}")
    if real_time_events:
        print(f"   Latest event: {real_time_events[-1]['type']} at {real_time_events[-1]['timestamp']}")
    
    # 6. Modify the file (small change that might be missed by real-time)
    print("\n6. Making a subtle modification...")
    content = test_file.read_text()
    test_file.write_text(content + "\n\nSubtle change for periodic detection.")
    
    # 7. Wait for periodic check
    print("\n7. Waiting 12 seconds for periodic check to run...")
    time.sleep(12)
    
    # Check events again
    response = requests.get(f"{BASE_URL}/api/events?limit=10")
    events = response.json()
    all_events = [e for e in events if 'test_both_modes' in e['path']]
    print(f"   Total events detected: {len(all_events)}")
    
    # 8. Check living note
    print("\n8. Checking living note updates...")
    response = requests.get(f"{BASE_URL}/api/living-note")
    living_note = response.json()
    print(f"   Living note word count: {living_note['wordCount']}")
    print(f"   Last updated: {living_note['lastUpdated']}")
    
    # 9. Stop monitoring
    print("\n9. Stopping monitoring...")
    response = requests.post(f"{BASE_URL}/api/monitor/stop")
    print(f"   Stop result: {response.json()['message']}")
    
    # 10. Clean up
    print("\n10. Cleaning up test file...")
    if test_file.exists():
        test_file.unlink()
    
    print("\n[SUCCESS] Test completed!")
    print("\nSummary:")
    print(f"- Real-time detection: {'[YES]' if real_time_events else '[NO]'}")
    print(f"- Periodic detection: {'[YES]' if len(all_events) > len(real_time_events) else '[NO]'}")
    print(f"- Both modes working: {'[YES]' if real_time_events and all_events else '[NO]'}")

if __name__ == "__main__":
    try:
        test_monitoring()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Obby API server.")
        print("   Make sure the server is running: python api_server.py")
    except Exception as e:
        print(f"[ERROR] {e}")