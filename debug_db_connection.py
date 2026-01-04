import os
from dotenv import load_dotenv
import pymongo

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"URL: {db_url.split('@')[1]}") # Masked

client = pymongo.MongoClient(db_url)
try:
    db = client.get_default_database()
    print(f"Default DB Name: '{db.name}'")
    print(f"Collections: {db.list_collection_names()}")
    
    count = db.market_overviews.count_documents({})
    print(f"market_overviews count: {count}")
    
    # Test sort
    docs = list(db.market_overviews.find().sort("timestamp", -1).limit(5))
    print(f"Found {len(docs)} docs with sort")
    
except Exception as e:
    print(f"Error getting default: {e}")
