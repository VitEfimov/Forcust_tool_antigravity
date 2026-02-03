import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_job():
    print("Starting Job...")
    res = requests.post(f"{BASE_URL}/simulation/v2/run", json={"symbol": "SPCE", "engine": "ensemble", "conservative": True})
    if res.status_code != 200:
        print(f"Error starting job: {res.text}")
        return
    
    job_id = res.json()["job_id"]
    print(f"Job ID: {job_id}")
    
    while True:
        res = requests.get(f"{BASE_URL}/jobs/{job_id}")
        data = res.json()
        status = data["status"]
        print(f"Status: {status}")
        
        if status == "completed":
            result = data["result"]
            print("Job Completed.")
            print("Keys:", result.keys())
            if "analysis" in result and "current_price" in result:
                print("SUCCESS: Missing fields are present.")
                print(f"Price: {result['current_price']}")
                print(f"Analysis Size: {len(result['analysis'])}")
            else:
                print("FAILURE: Missing fields still missing.")
            break
        
        if status == "failed":
            print(f"Job Failed: {data.get('error')}")
            break
            
        time.sleep(2)

if __name__ == "__main__":
    test_job()
