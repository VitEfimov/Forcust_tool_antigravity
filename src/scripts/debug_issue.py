import sys
import os
sys.path.append(os.getcwd())

from src.core.database import Database
from src.data.loader import DataLoader
from src.core.config import settings
import sqlite3

def debug():
    print("--- Debugging Database ---")
    db = Database()
    print(f"DB URL: {db.db_url}")
    print(f"DB Path: {getattr(db, 'db_path', 'Mongo')}")
    
    if not db.is_mongo:
        conn = sqlite3.connect(db.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print(f"Tables: {tables}")
        conn.close()
        
        if not any('watchlist' in t for t in tables):
            print("CRITICAL: 'watchlist' table missing!")
        else:
            print("'watchlist' table exists.")

    print("\n--- Debugging Watchlist Add ---")
    try:
        db.add_to_watchlist("SPCE")
        print("Successfully added SPCE to watchlist.")
        print(f"Current Watchlist: {db.get_watchlist()}")
    except Exception as e:
        print(f"Failed to add to watchlist: {e}")

    print("\n--- Debugging Data Fetch (SPCE) ---")
    loader = DataLoader(settings.DATA_CACHE_DIR)
    try:
        df = loader.get_data("SPCE", use_cache=False)
        if df.empty:
            print("SPCE data is empty!")
        else:
            print(f"SPCE data fetched. Rows: {len(df)}")
            print(df.tail())
    except Exception as e:
        print(f"Failed to fetch data: {e}")

if __name__ == "__main__":
    debug()
