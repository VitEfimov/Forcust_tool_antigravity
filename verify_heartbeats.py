
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(os.getcwd())

from src.core.monitoring import monitor
from src.core.scheduler import run_scheduled_market_overview

def test_heartbeat_logging():
    print("Testing Heartbeat Logging...")
    
    # 1. Test Manual Heartbeat (mimicking Startup)
    print("1. Logging Startup Heartbeat...")
    monitor.log_heartbeat("SystemStartup", "success", {"message": "Verification Test"})
    
    # 2. Test Scheduled Task Heartbeat
    print("2. Running Scheduled Market Overview (Mock)...")
    try:
        # We don't want to actually run the heavy compute if we can avoid it, 
        # or we accept it takes a second. 
        # The function `run_scheduled_market_overview` calls `_compute_market_overview`
        # which might overwrite files. That's actually fine/good for verification.
        run_scheduled_market_overview()
    except Exception as e:
        print(f"Task ran with error (expected if DB not connected etc): {e}")
        
    # 3. Verify Log File Content
    log_file = Path("data/logs/system_heartbeats.jsonl")
    print(f"3. Checking {log_file}...")
    
    if not log_file.exists():
        print("FAIL: Log file does not exist.")
        return
        
    found_startup = False
    found_overview = False
    
    with open(log_file, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data["task"] == "SystemStartup" and data["details"].get("message") == "Verification Test":
                    found_startup = True
                if data["task"] == "MarketOverview":
                    found_overview = True
            except: pass
            
    if found_startup:
        print("PASS: SystemStartup heartbeat found.")
    else:
        print("FAIL: SystemStartup heartbeat NOT found.")
        
    if found_overview:
        print("PASS: MarketOverview heartbeat found.")
    else:
        print("FAIL: MarketOverview heartbeat NOT found.")

if __name__ == "__main__":
    test_heartbeat_logging()
