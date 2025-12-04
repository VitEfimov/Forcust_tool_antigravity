import requests
import time

BASE_URL = "http://localhost:8000"

def test_phase3():
    print("Testing /indices/history...")
    try:
        res = requests.get(f"{BASE_URL}/indices/history")
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"History items: {len(data.get('history', []))}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting /forecast/SPY (New Horizons)...")
    try:
        res = requests.get(f"{BASE_URL}/forecast/SPY")
        print(f"Status: {res.status_code}")
        data = res.json()
        forecasts = data.get('forecasts', {})
        print(f"Horizons found: {list(forecasts.keys())}")
        
        # Check if 730d is present
        if '730d' in forecasts:
            print("SUCCESS: 730d horizon found.")
        else:
            print("FAILURE: 730d horizon missing.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_phase3()
