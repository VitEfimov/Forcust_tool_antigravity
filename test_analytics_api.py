import requests
import json
import sys

def test_api():
    url = "http://127.0.0.1:8000/analytics/advanced/SPY"
    print(f"Testing {url}...")
    try:
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Failed: {r.status_code} {r.text}")
            sys.exit(1)
            
        data = r.json()
        print("Success! JSON Keys:")
        print(list(data.keys()))
        
        # Validate specific fields
        assert "transition_matrix" in data
        assert "regime_duration_days" in data
        assert "volatility_trend" in data
        
        print("\nTransition Matrix Stub:")
        print(json.dumps(data['transition_matrix'], indent=2))
        
        print(f"\nRegime Duration: {data['regime_duration_days']} days")
        print(f"Vol Trend: {data['volatility_trend']}")
        
    except Exception as e:
        print(f"Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_api()
