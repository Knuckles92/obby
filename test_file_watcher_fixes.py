#!/usr/bin/env python3
"""
Test script to verify file watcher reliability fixes.
Run this after starting the backend server to test the fixes.
"""

import time
import requests
from pathlib import Path

def test_monitor_status():
    """Test the new diagnostic endpoint"""
    try:
        response = requests.get('http://localhost:8001/api/monitor/status')
        if response.status_code == 200:
            status = response.json()
            print("🔍 Monitor Status:")
            print(f"  Monitoring Active: {status.get('monitoring_active')}")
            print(f"  File Watcher Running: {status.get('file_watcher_running')}")
            print(f"  Periodic Check Enabled: {status.get('periodic_check_enabled')}")
            print(f"  Check Interval: {status.get('check_interval')}s")
            print(f"  Watched Directories: {status.get('watched_directories', [])}")
            print(f"  Recent Events: {status.get('recent_events_count')}")
            return True
        else:
            print(f"❌ Failed to get monitor status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing monitor status: {e}")
        return False

def test_file_change():
    """Test file change detection by modifying test.md"""
    test_file = Path("notes/test.md")
    
    if not test_file.exists():
        print(f"❌ Test file {test_file} does not exist")
        return False
    
    print(f"📝 Testing file change detection with {test_file.name}")
    
    # Add a timestamp to the file
    timestamp = int(time.time())
    test_content = f"- File watcher test at timestamp: {timestamp}\n"
    
    with open(test_file, 'a') as f:
        f.write(test_content)
    
    print(f"✅ Added test content with timestamp {timestamp}")
    print("📍 Check the server logs for file watcher activity...")
    
    # Wait a moment for processing
    time.sleep(2)
    
    return True

def main():
    print("🧪 Testing File Watcher Reliability Fixes")
    print("=" * 50)
    
    # Test 1: Check monitor status
    print("\n1. Testing Monitor Status Endpoint")
    status_ok = test_monitor_status()
    
    # Test 2: Test file change detection  
    print("\n2. Testing File Change Detection")
    if status_ok:
        change_ok = test_file_change()
        
        if change_ok:
            print("\n✅ File watcher tests completed!")
            print("Check the backend server logs for detailed processing information.")
        else:
            print("\n❌ File change test failed")
    else:
        print("\n⚠️ Skipping file change test due to monitor status issues")
    
    print("\n💡 Tips:")
    print("- Make sure the backend server is running (python backend.py)")
    print("- Check obby.log for detailed file watcher activity")
    print("- Monitor status should show monitoring_active: true")

if __name__ == "__main__":
    main()