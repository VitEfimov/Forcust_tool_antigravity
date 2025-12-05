import sys
import os
import pymongo
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.config import settings

def check_db():
    print(f"Checking database connection...")
    print(f"URL: {settings.DATABASE_URL[:25]}...") # Hide password
    
    try:
        client = pymongo.MongoClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)
        # Force connection
        info = client.server_info()
        print("✅ Connection Successful!")
        
        db = client.get_default_database()
        print(f"Database: {db.name}")
        
        collections = db.list_collection_names()
        print(f"Collections: {collections}")
        
        if "market_overview" in collections:
            count = db.market_overview.count_documents({})
            print(f"Market Overviews: {count}")
        else:
            print("❌ 'market_overview' collection not found.")
            
        if "simulation_runs" in collections:
            count = db.simulation_runs.count_documents({})
            print(f"Simulation Runs: {count}")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("Tip: Check if your IP is whitelisted in MongoDB Atlas Network Access.")

if __name__ == "__main__":
    check_db()
