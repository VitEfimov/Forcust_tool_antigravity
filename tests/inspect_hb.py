import sys
from pathlib import Path
import json

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.monitoring import monitor

def inspect():
    print("--- RAW HEARTBEATS ---")
    latest = monitor.get_latest_heartbeats()
    print(json.dumps(latest, indent=2, default=str))

if __name__ == "__main__":
    inspect()
