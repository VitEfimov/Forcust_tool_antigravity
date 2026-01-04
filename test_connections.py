import os
import sys
import socket
import time
import requests

def check_mongo():
    print("\n--- MongoDB Connection ---")
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.server_info() # Trigger connection
        print("✅ MongoDB: Connected")
        
        dbs = client.list_database_names()
        print(f"Databases: {dbs}")
        
        if "antigravity" in dbs:
            db = client.get_database("antigravity")
            cols = db.list_collection_names()
            print(f"Collections in 'antigravity': {cols}")
        else:
            print("⚠️ 'antigravity' database NOT found")
            
    except ImportError:
        print("⚠️ pymongo not installed")
    except Exception as e:
        print(f"❌ MongoDB: Failed - {e}")

def check_sqlite():
    print("\n--- SQLite Connection ---")
    db_path = "data/forecasts.db"
    if os.path.exists(db_path):
        print(f"✅ SQLite DB file found: {db_path}")
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in c.fetchall()]
            print(f"Tables: {tables}")
            conn.close()
        except Exception as e:
            print(f"❌ SQLite: Failed to read - {e}")
    else:
        print(f"⚠️ SQLite DB file NOT found at {db_path}")

def check_network():
    print("\n--- Network Connection (yfinance) ---")
    try:
        # Simple ping to Yahoo Finance
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SPY", timeout=5)
        if r.status_code == 200:
             print("✅ Network: Connected (Yahoo Finance Reachable)")
        else:
             print(f"⚠️ Network: Reachable but status {r.status_code}")
    except Exception as e:
        print(f"❌ Network: Failed - {e}")

def check_backend():
    print("\n--- Backend Server (Localhost:8000) ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('localhost', 8000))
        if result == 0:
            print("✅ Backend: Port 8000 is accepting connections")
        else:
            print("❌ Backend: Port 8000 is CLOSED")
        s.close()
    except Exception as e:
         print(f"❌ Backend Check Failed: {e}")

if __name__ == "__main__":
    check_mongo()
    check_sqlite()
    check_network()
    check_backend()
