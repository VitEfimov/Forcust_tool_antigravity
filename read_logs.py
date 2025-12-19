
from pathlib import Path
project_root = Path(__file__).resolve().parent


log_file = project_root / "server_optimized_2.log"

print(f"Reading {log_file}...")
try:
    # Try utf-16 first (PowerShell default)
    with open(log_file, "r", encoding="utf-16", errors="ignore") as f:
        lines = f.readlines()
        print("\n".join(lines[-20:]))
except Exception as e:
    print(f"Failed utf-16, trying utf-8: {e}")
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            print("\n".join(lines[-50:]))
    except Exception as e2:
         print(f"Error: {e2}")

