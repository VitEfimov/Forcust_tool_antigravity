import requests
import time

API_URL = "http://localhost:8000/market/overview"

def check_api():
    print(f"Checking {API_URL}...")
    start = time.time()
    try:
        response = requests.get(API_URL, timeout=30)
        elapsed = time.time() - start
        print(f"Status: {response.status_code}")
        print(f"Time: {elapsed:.2f}s")
        if response.status_code == 200:
            data = response.json()
            overview = data.get("overview", [])
            print(f"Items: {len(overview)}")
            if len(overview) > 0:
                print(f"First Item: {overview[0]['symbol']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_api()
