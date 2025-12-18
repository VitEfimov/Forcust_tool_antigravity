
from pathlib import Path
project_root = Path(__file__).resolve().parent

log_file = project_root / "api_error_log.txt"
if not log_file.exists():
    log_file = project_root / "server_log.txt"

print(f"Reading {log_file}...")
try:
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        print("\n".join(lines[-30:]))
except Exception as e:
    print(f"Error reading log: {e}")
