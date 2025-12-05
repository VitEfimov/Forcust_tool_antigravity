import requests
import sys
import json
import time

BASE_URL = "http://localhost:8001"

def test_endpoint(name, url):
    print(f"Testing {name} ({url})...", end=" ", flush=True)
    try:
        response = requests.get(url, timeout=30) # 30s timeout
        if response.status_code == 200:
            print(f"✅ OK ({len(response.content)} bytes)")
            return True, response.json()
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text[:200])
            return False, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def run_tests():
    print(f"Running diagnostics against {BASE_URL}...\n")
    
    # 1. Health
    ok, _ = test_endpoint("Health Check", f"{BASE_URL}/health")
    if not ok:
        print("\nCRITICAL: Backend is not reachable. Is uvicorn running?")
        return

    # 2. Watchlist
    ok, data = test_endpoint("Watchlist", f"{BASE_URL}/watchlist")
    
    # 3. Market Overview
    start = time.time()
    ok, data = test_endpoint("Market Overview", f"{BASE_URL}/market/overview")
    elapsed = time.time() - start
    print(f"⏱️ Market Overview took {elapsed:.2f} seconds")
    if ok and len(data.get('overview', [])) == 0:
        print("⚠️  Warning: Market Overview returned empty list. DB might be empty.")

    # 4. Forecast SPY (The heavy one)
    print("\nTesting Forecast (SPY) - This triggers model loading...")
    ok, data = test_endpoint("Forecast SPY", f"{BASE_URL}/forecast/SPY")
    if ok:
        print("✅ Forecast generated successfully!")
    else:
        print("❌ Forecast failed. Check backend logs for stack trace.")

if __name__ == "__main__":
    run_tests()
