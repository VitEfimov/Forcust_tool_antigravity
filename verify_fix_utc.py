
import sys
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.monitoring import monitor

API_URL = "http://localhost:8000"

def verify_fix():
    print("--- Verifying Lock Logic Fix ---")
    
    # 1. Unlocked Check
    print("1. Checking access to busy-protected endpoint (train)...")
    try:
        # Should now be free or return normal error, not 423
        res = requests.post(f"{API_URL}/models/train", json={"symbol": "TEST", "indices": []})
        if res.status_code == 423:
            print("❌ FAILURE: System still locked (423)!")
            return
        else:
            print(f"✅ Success: Endpoint accessible (Status {res.status_code} != 423)")
    except Exception as e:
        print(f"Error accessing API: {e}")
        return

    # 2. Mock Stale Lock (UTC)
    print("\n2. Mocking STALE lock (15 mins ago)...")
    past_ts = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    # Manually inject into file/monitoring to bypass the 'log_heartbeat' valid ts
    # We use the monitor instance to log it, but we need to trick it?
    # Actually log_heartbeat uses 'now' by default. We can pass 'details' but not timestamp directly.
    # Wait, monitoring.py:61 'now_ts = ...'. We can't easily override timestamp via log_heartbeat method.
    # We have to write to the file manually.
    
    hb_file = monitor.log_file
    stale_event = {
        "task": "TestStaleTask",
        "status": "running",
        "timestamp": past_ts,
        "details": {}
    }
    with open(hb_file, "a") as f:
        f.write(json.dumps(stale_event) + "\n")
        
    # Check if API ignores it (it should, > 10 mins)
    # We need to trigger check_busy. But check_busy checks SPECIFIC task names.
    # 'monitor.get_latest_heartbeats' will pick up TestStaleTask.
    # But check_busy only checks: "DailyAutomation", "WeeklyTraining", "MLTraining", "WalkForward", "AdvancedSimulation"
    # So we must mock one of THOSE.
    
    print("   Injecting stale 'DailyAutomation' lock...")
    stale_event["task"] = "DailyAutomation"
    with open(hb_file, "a") as f:
        f.write(json.dumps(stale_event) + "\n")
        
    print("   Querying API (should pass)...")
    res = requests.post(f"{API_URL}/models/train", json={"symbol": "TEST", "indices": []})
    if res.status_code == 423:
        print("❌ FAILURE: Stale lock blocked the system!")
    else:
        print("✅ Success: Stale lock ignored.")

    # 3. Mock Active Lock (UTC)
    print("\n3. Mocking ACTIVE lock (1 min ago)...")
    recent_ts = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    active_event = {
        "task": "DailyAutomation",
        "status": "running",
        "timestamp": recent_ts,
        "details": {}
    }
    with open(hb_file, "a") as f:
        f.write(json.dumps(active_event) + "\n")
        
    print("   Querying API (should BLOCK)...")
    res = requests.post(f"{API_URL}/models/train", json={"symbol": "TEST", "indices": []})
    if res.status_code == 423:
        print("✅ Success: Active lock blocked system correctly.")
    else:
        print(f"❌ FAILURE: expected 423, got {res.status_code}")
        
    # 4. Cleanup
    print("\n4. Cleaning up locks...")
    requests.post(f"{API_URL}/system/unlock")

if __name__ == "__main__":
    verify_fix()
