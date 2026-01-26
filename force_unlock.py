import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.core.monitoring import monitor

if __name__ == "__main__":
    print("Forcing System Unlock...")
    count = monitor.force_clear_locks()
    print(f"Cleared {count} stale locks.")
