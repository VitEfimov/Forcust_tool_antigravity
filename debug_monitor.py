import sys
import os
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.core.monitoring import monitor

if __name__ == "__main__":
    print("=== DEBUGGING SYSTEM MONITOR ===")
    
    # 1. Check file existence
    print(f"Log File: {monitor.log_file}")
    print(f"File Exists: {monitor.log_file.exists()}")
    
    # 2. Get Raw Latest Heartbeats
    try:
        latest = monitor.get_latest_heartbeats()
        print("\n[LATEST HEARTBEATS]")
        for task, evt in latest.items():
            status = evt.get('status')
            ts = evt.get('timestamp')
            print(f"- {task}: {status} (at {ts})")
            
    except Exception as e:
        print(f"Error fetching latest: {e}")

    # 3. Check for 'Running' tasks
    print("\n[RUNNING TASKS]")
    running = [t for t, e in latest.items() if e.get('status') == 'running']
    if running:
        print(f"DETECTED RUNNING: {running}")
    else:
        print("No running tasks detected by backend logic.")

    # 4. Dump last 5 lines of file to check for corruption
    if monitor.log_file.exists():
        print("\n[LAST 5 FILE LINES]")
        with open(monitor.log_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-5:]:
                print(line.strip())
