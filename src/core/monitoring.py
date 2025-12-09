
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Path Configuration
project_root = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = project_root / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
HEARTBEAT_FILE = LOGS_DIR / "system_heartbeats.jsonl"

class SystemMonitor:
    def __init__(self):
        self.log_file = HEARTBEAT_FILE

    def log_heartbeat(self, task: str, status: str, details: dict = None, duration_sec: float = 0.0):
        """
        Log a structured heartbeat event.
        task: e.g., "DailyAutomation", "WeeklyTrain"
        status: "success", "error", "running"
        details: dict of extra metrics
        """
        if details is None:
            details = {}
            
        event = {
            "task": task,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "duration_sec": round(duration_sec, 2),
            "details": details
        }
        
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"Failed to log heartbeat: {e}")

    def get_latest_heartbeats(self):
        """
        Retrieve the most recent status for each unique task.
        Returns a dict: { "TaskName": {event_dict}, ... }
        """
        latest_map = {}
        if not self.log_file.exists():
            return {}
            
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        task = event.get("task")
                        if task:
                            latest_map[task] = event
                    except:
                        continue
        except Exception as e:
            print(f"Error reading heartbeats: {e}")
            
        return latest_map

# Global Instance
monitor = SystemMonitor()
