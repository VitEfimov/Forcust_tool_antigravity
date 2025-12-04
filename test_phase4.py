import requests
import time

BASE_URL = "http://localhost:8000"

def test_phase4():
    print("Testing /market/overview (Top 50)...")
    try:
        start_time = time.time()
        res = requests.get(f"{BASE_URL}/market/overview")
        duration = time.time() - start_time
        print(f"Status: {res.status_code}")
        print(f"Time taken: {duration:.2f}s")
        
        data = res.json()
        overview = data.get('overview', [])
        print(f"Items returned: {len(overview)}")
        
        if len(overview) > 0:
            first = overview[0]
            print("First Item Sample:")
            print(f"Symbol: {first.get('symbol')}")
            print(f"Today Open: {first.get('today_open')}")
            print(f"Past Open (-10d): {first.get('past_open')}")
            print(f"Forecast 10d: {first.get('forecast_10d_pct')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_phase4()
