
import requests
import sys

API_URL = "http://localhost:8000"

def force_unlock():
    print(f"Connecting to {API_URL}/system/unlock ...")
    try:
        res = requests.post(f"{API_URL}/system/unlock")
        if res.status_code == 200:
            print("✅ Success! System unlocked.")
            print(res.json())
        else:
            print(f"❌ Failed: {res.status_code}")
            print(res.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    force_unlock()
