
import sys
import threading
import time
import requests

API_URL = "http://localhost:8000"

def trigger_task(name, endpoint):
    try:
        print(f"[{name}] Requesting {endpoint}...")
        res = requests.post(f"{API_URL}{endpoint}", json={"symbol": "SPY", "horizon": 10}, timeout=5)
        print(f"[{name}] Response: {res.status_code} - {res.text[:100]}")
        return res.status_code
    except requests.exceptions.Timeout:
        print(f"[{name}] Timed out (expected if running long task)")
        return 200 # Assuming it started
    except Exception as e:
        print(f"[{name}] Error: {e}")
        return 500

def test_locking():
    print("--- Starting Concurrency Lock Verification ---")
    
    # 1. Start a "Fake" Heavy Task? 
    # We don't have a fake API endpoint, so we have to use a real one but maybe fail it fast?
    # Or rely on the fact that 'DailyAutomation' or 'MLTraining' sets the lock *before* doing work.
    # But those endpoints might take time to return (sync blocking?).
    # The `train_model` endpoint is likely sync/blocking or async?
    # It is defined as `async def train_model_endpoint`. It awaits `train_model`.
    # So it returns only when done.
    # This makes testing hard without a background task.
    # BUT, `check_busy` is a dependency.
    
    # We can use /system/run/daily which runs in BackgroundTasks?
    # Let's check routes.py.
    # `run_daily_endpoint` -> `background_tasks.add_task(run_daily_automation)`
    # This returns IMMEDIATELY with 202 Accepted.
    # Perfect.
    
    print("1. Triggering Background Task (Daily Run)...")
    res1 = requests.post(f"{API_URL}/system/run/daily")
    if res1.status_code not in [200, 202]:
        print(f"Failed to start task 1: {res1.status_code}")
        # If it's 423, maybe something is ALREADY running.
        if res1.status_code == 423:
             print("System was already busy! Resetting or waiting?")
             # For test purposes, we assume clean slate.
        return

    print("Task 1 started (Background). Giving it 1s to set heartbeat...")
    time.sleep(1)
    
    print("2. Attempting Concurrent Task (ML Training)...")
    res2 = requests.post(f"{API_URL}/models/train", json={"symbol": "AAPL", "indices": ["^VIX"], "horizons": [10]})
    
    print(f"Task 2 Status: {res2.status_code}")
    
    if res2.status_code == 423:
        print("✅ SUCCESS: Concurrency Lock Active (Got 423 Locked)")
    else:
        print(f"❌ FAILURE: Expected 423, got {res2.status_code}")
        
    # 3. Stop the first task to clean up
    print("3. Stopping Task...")
    requests.post(f"{API_URL}/system/control/stop/DailyAutomation")

if __name__ == "__main__":
    test_locking()
