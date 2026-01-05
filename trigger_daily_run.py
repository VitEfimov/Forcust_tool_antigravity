import requests
import time
import json

BASE_URL = "http://localhost:8000"

def get_logs():
    try:
        r = requests.get(f"{BASE_URL}/system/heartbeats?limit=5")
        if r.status_code == 200:
            return r.json().get("events", [])
        return []
    except:
        return []

print("--- Initial Logs ---")
initial_logs = get_logs()
for log in initial_logs:
    print(f"{log.get('task')} | {log.get('status')} | {log.get('timestamp')}")

print("\n--- Triggering Daily Run ---")
try:
    r = requests.post(f"{BASE_URL}/system/run/daily")
    print(f"Trigger Status: {r.status_code} |Response: {r.text}")
except Exception as e:
    print(f"Trigger Failed: {e}")
    exit(1)

print("\n--- Monitoring Logs (30s) ---")
for i in range(10):
    time.sleep(3)
    logs = get_logs()
    # Check if any new log is not in initial
    new_logs = [l for l in logs if l not in initial_logs] 
    # (Simple diff by checking top item)
    if logs:
        top_log = logs[0]
        print(f"[{i*3}s] Latest: {top_log.get('task')} - {top_log.get('status')}")
        if top_log.get('task') == 'DailyAutomation':
             print("\n✅ DailyAutomation Logged!")
             break
