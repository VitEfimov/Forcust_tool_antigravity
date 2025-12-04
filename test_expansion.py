import requests
import time

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("Testing /market/overview...")
    try:
        res = requests.get(f"{BASE_URL}/market/overview")
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Overview items: {len(data.get('overview', []))}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting /forecast/SP500 (Symbol Mapping)...")
    try:
        # Should map to ^GSPC
        res = requests.get(f"{BASE_URL}/forecast/SP500")
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Symbol: {data.get('symbol')}")
        print(f"Forecasts: {list(data.get('forecasts', {}).keys())}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting /archive/SP500...")
    try:
        res = requests.get(f"{BASE_URL}/archive/^GSPC") # DB uses resolved symbol
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"History items: {len(data.get('history', []))}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    time.sleep(2) # Wait for reload
    test_endpoints()
