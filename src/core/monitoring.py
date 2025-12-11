
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
            
        event = {
            "task": task,
            "status": status,
            "timestamp": datetime.now().isoformat(),
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

# Global Instance
monitor = SystemMonitor()
