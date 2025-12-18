
import sys
import json
from pathlib import Path

# Fix path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.core.monitoring import monitor

def debug_heartbeats():
    with open("debug_out_clean.txt", "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            
        log("--- Debugging Heartbeats ---")
        log(f"Log File: {monitor.log_file}")
        if monitor.mongo_collection is not None:
            log("Using MongoDB: YES")
        else:
            log("Using MongoDB: NO")
            
        latest = monitor.get_latest_heartbeats()
        log("\nLatest Heartbeats:")
        for task, data in latest.items():
            log(f"[{task}] Status: {data.get('status')} | Time: {data.get('timestamp')}")
            
        log("\n--- Check Busy Logic ---")
        heavy_tasks = ["DailyAutomation", "WeeklyTraining", "MLTraining", "WalkForward", "AdvancedSimulation"]
        for t in heavy_tasks:
            if t in latest:
                status = latest[t].get("status", "").lower()
                log(f"Checking {t}: {status}")
                if "running" in status:
                    log(f"!!! {t} IS BLOCKING !!!")

if __name__ == "__main__":
    debug_heartbeats()
