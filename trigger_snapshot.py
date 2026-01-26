import sys
import os
import asyncio

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.core.scheduler import run_scheduled_market_overview
from src.core.database import get_db

if __name__ == "__main__":
    print("Triggering Manual Market Snapshot...")
    try:
        # Run the scheduled task logic which computes and saves to DB
        run_scheduled_market_overview()
        print("Success! Snapshot saved.")
        
        # Verify
        db = get_db()
        history = db.get_market_overview_history(limit=1)
        if history:
            print(f"Latest Snapshot Date: {history[0]['date']}")
            data = history[0].get('data', {}).get('overview', [])
            if data and len(data) > 0:
                print(f"Sample Forecasts Keys: {data[0].get('forecasts', {}).keys()}")
    except Exception as e:
        print(f"Error: {e}")
