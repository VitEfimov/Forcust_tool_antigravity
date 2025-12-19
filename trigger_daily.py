
import requests
import time

print("Triggering Daily Automation...")
res = requests.post("http://localhost:8000/system/run/daily")
print(f"Status: {res.status_code}")
print(f"Response: {res.text}")

print("Waiting 5s for logs...")
time.sleep(5)
