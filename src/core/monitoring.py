
import json
import os
import time
from datetime import datetime
from pathlib import Path

from src.core.config import settings

# Path Configuration
project_root = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = project_root / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
HEARTBEAT_FILE = LOGS_DIR / "system_heartbeats.jsonl"

class SystemMonitor:
    def __init__(self):
        self.log_file = HEARTBEAT_FILE
        self.mongo_collection = None
        self.start_time = datetime.now()
        
        # Initialize MongoDB if configured
        if settings.DATABASE_URL and "mongodb" in settings.DATABASE_URL:
            try:
                import pymongo
                client = pymongo.MongoClient(settings.DATABASE_URL)
                try:
                    self.mongo_collection = client.get_default_database().heartbeats
                except Exception:
                    # Fallback if no db in connection string
                    self.mongo_collection = client.get_database("antigravity").heartbeats
                    
                print(f"[MONITOR] Persistent Heartbeats Enabled (MongoDB)")
            except Exception as e:
                print(f"[MONITOR] Failed to connect to MongoDB: {e}")

    def log_heartbeat(self, task: str, status: str, details: dict = None, duration_sec: float = 0.0):
        """
        Log a structured heartbeat event.
        task: e.g., "DailyAutomation", "WeeklyTrain"
        status: "success", "error", "running"
        details: dict of extra metrics
        """
        if details is None:
            details = {}
            
        # Use UTC for consistency
        from datetime import timezone
        now_ts = datetime.now(timezone.utc).isoformat()

        event = {
            "task": task,
            "status": status,
            "timestamp": now_ts,
            "duration_sec": round(duration_sec, 2),
            "details": details
        }
        
        # 1. Local File (Always, for debugging/fallback)
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"Failed to log heartbeat locally: {e}")
            
        # 2. MongoDB (Persistent)
        if self.mongo_collection is not None:
            try:
                self.mongo_collection.insert_one(event)
            except Exception as e:
                print(f"Failed to log heartbeat to Mongo: {e}")

    def get_latest_heartbeats(self):
        """
        Retrieve the most recent status for each unique task.
        Returns a dict: { "TaskName": {event_dict}, ... }
        """
        latest_map = {}
        
        # Priority: MongoDB (Persistent) > Local File (Ephemeral)
        if self.mongo_collection is not None:
            try:
                # Aggregate to get last entry for each task
                pipeline = [
                    {"$sort": {"timestamp": 1}},
                    {"$group": {
                        "_id": "$task",
                        "last_event": {"$last": "$$ROOT"}
                    }}
                ]
                results = list(self.mongo_collection.aggregate(pipeline))
                for res in results:
                    task = res["_id"]
                    event = res["last_event"]
                    if "_id" in event: del event["_id"] # clean for frontend
                    latest_map[task] = event
                return latest_map
            except Exception as e:
                print(f"[MONITOR] Mongo read failed: {e}. Falling back to file.")
        
        # Fallback: Local File
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

    def get_recent_heartbeats(self, limit: int = 50) -> list:
        """
        Retrieve a flat list of the most recent heartbeat events across all tasks.
        """
        # 1. MongoDB
        if self.mongo_collection is not None:
            try:
                events = list(self.mongo_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
                return events
            except Exception as e:
                print(f"[MONITOR] Mongo read failed: {e}")
        
        # 2. Local File Fallback
        events = []
        if self.log_file.exists():
            try:
                # Read all lines (inefficient for large files but ok for log rotation)
                with open(self.log_file, "r") as f:
                    lines = f.readlines()
                    for line in reversed(lines): # Read backwards
                        try:
                            if len(events) >= limit: break
                            events.append(json.loads(line))
                        except: continue
            except Exception: pass
            
        return events

    def check_stale_tasks(self):
        """
        Scan for tasks stuck in 'running' state from previous sessions.
        Called on system startup.
        """
        try:
            latest = self.get_latest_heartbeats()
            for task, event in latest.items():
                if event.get("status") == "running":
                    # Parse timestamp
                    try:
                        ts_str = event.get("timestamp")
                        # Handle various formats or ISO
                        ts = datetime.fromisoformat(ts_str)
                        
                        # Compare: If timestamp is clearly older than our start_time
                        # (Allow a small buffer or just check if it was engaged before NOW)
                        # Actually simple logic: ANY task 'running' when we just booted up is likely stale/interrupted.
                        # Because we claim to be "SystemStartup".
                        
                        self.log_heartbeat(task, "interrupted", {"reason": "System Restart Detected"})
                        print(f"[MONITOR] Marked stale task '{task}' as INTERRUPTED.")
                        
                    except Exception as e:
                        print(f"[MONITOR] Failed to check stale task {task}: {e}")
        except Exception as e:
            print(f"[MONITOR] Error checking stale tasks: {e}")

    def force_clear_locks(self):
        """
        Manually force-clear any running locks. 
        Useful if the system gets stuck in 'Busy' state.
        """
        heavy_tasks = ["DailyAutomation", "WeeklyTraining", "MLTraining", "WalkForward", "AdvancedSimulation"]
        cleared_count = 0
        
        try:
            # Check latest status first to avoid spamming
            latest = self.get_latest_heartbeats()
            
            for task in heavy_tasks:
                # If explicit Running, OR if it's not present but we want to be safe?
                # Mainly clear "running" ones.
                evt = latest.get(task, {})
                if evt.get("status") == "running":
                    self.log_heartbeat(task, "interrupted", {"reason": "Manual Unlock Triggered"})
                    print(f"[MONITOR] Force-unlocked task: {task}")
                    cleared_count += 1
                    
            return cleaned_count if 'cleaned_count' in locals() else cleared_count
            
        except Exception as e:
            print(f"[MONITOR] Error force clearing locks: {e}")
            return 0
            
# Global Instance
monitor = SystemMonitor()
