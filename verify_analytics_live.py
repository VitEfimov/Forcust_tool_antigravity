import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def run_verification():
    print("=== Analytics API Verification ===")
    
    # 1. Market History
    print("\n1. Testing /market/history...")
    try:
        res = requests.get(f"{BASE_URL}/market/history?limit=3")
        if res.status_code == 200:
            print("SUCCESS: Fetched History")
            data = res.json()
            print(f"Items: {len(data.get('history', []))}")
        else:
            print(f"FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR: {e}")

    # 2. Market Overview
    print("\n2. Testing /market/overview...")
    try:
        res = requests.get(f"{BASE_URL}/market/overview")
        if res.status_code == 200:
            print("SUCCESS: Fetched Overview")
            data = res.json()
            overview = data.get("overview", [])
            print(f"Symbols: {len(overview)}")
            if len(overview) > 0:
                print(f"Sample: {overview[0]['symbol']} | {overview[0].get('regime')} | {overview[0].get('risk_label')}")
        else:
            print(f"FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR: {e}")

    # 3. Detailed Analytics (SPY)
    print("\n3. Testing /analytics/advanced/SPY...")
    try:
        res = requests.get(f"{BASE_URL}/analytics/advanced/SPY")
        if res.status_code == 200:
            print("SUCCESS: Fetched Advanced Analytics for SPY")
            data = res.json()
            print(f"Regime: {data.get('regime')}")
            print(f"Duration: {data.get('regime_duration_days')} days")
            print(f"Vol Trend: {data.get('volatility_trend')}")
        elif res.status_code == 404:
             print("WARNING: SPY data not found (Database might need seeding)")
        else:
            print(f"FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    run_verification()
