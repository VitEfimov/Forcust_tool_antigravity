import requests
import time

BASE_URL = "http://localhost:8000"

def test_phase5():
    symbol = "MSFT"
    print(f"Testing /forecast/{symbol} (Triggering Training with Windows)...")
    try:
        # This might take a while if it trains
        start_time = time.time()
        res = requests.get(f"{BASE_URL}/forecast/{symbol}")
        duration = time.time() - start_time
        
        print(f"Status: {res.status_code}")
        print(f"Time taken: {duration:.2f}s")
        
        if res.status_code == 200:
            data = res.json()
            print("Success!")
            print(f"Forecasts keys: {list(data.get('forecasts', {}).keys())}")
            if "10d" in data["forecasts"]:
                print(f"10d Components: {data['forecasts']['10d'].get('components')}")
        else:
            print(f"Failed: {res.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_phase5()
