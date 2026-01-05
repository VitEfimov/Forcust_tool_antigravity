import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, name, expect_data=True):
    print(f"\n--- Testing {name} ({endpoint}) ---")
    try:
        if method == "POST":
            r = requests.post(f"{BASE_URL}{endpoint}")
        else:
            r = requests.get(f"{BASE_URL}{endpoint}")
            
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            # Summary
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"Keys: {keys}")
                # Specific checks
                if "history" in data:
                    print(f"History Items: {len(data['history'])}")
                if "overview" in data:
                     print(f"Overview Items: {len(data['overview'])}")
            print("✅ Success")
            return True
        else:
            print(f"❌ Failed: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def run_tests():
    # 1. Unlock
    test_endpoint("POST", "/system/unlock", "System Unlock")
    
    # 2. Market Overview
    test_endpoint("GET", "/market/overview", "Market Overview")
    
    # 3. Market History
    # Limiting to 30 to match frontend
    test_endpoint("GET", "/market/history?limit=30", "Market History")
    
    # 4. Forecast SPY
    test_endpoint("GET", "/forecast/SPY", "Forecast SPY")
    
    # 5. Advanced Sim
    test_endpoint("GET", "/simulation/v2/SPY", "Advanced Simulation (V2)")

if __name__ == "__main__":
    try:
        run_tests()
    except KeyboardInterrupt:
        print("\nAborted.")
