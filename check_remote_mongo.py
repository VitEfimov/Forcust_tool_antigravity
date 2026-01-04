import os
import sys
import pymongo

# Load env vars manually since we might not have dotenv
db_url = "mongodb+srv://vitvalef_db_user:yftZ097dE2hrlAbY@cluster0.c6x0pdu.mongodb.net/?appName=Cluster0"

print(f"Connecting to: {db_url.split('@')[1]}") # Print masked URL

try:
    client = pymongo.MongoClient(db_url)
    # Trigger info to verify connection
    client.server_info()
    print("✅ Connected to MongoDB Atlas")
    
    # Check databases
    dbs = client.list_database_names()
    print(f"\nDatabases: {dbs}")
    
    target_db_name = "antigravity"
    if target_db_name in dbs:
        db = client.get_database(target_db_name)
        cols = db.list_collection_names()
        print(f"\nCollections in '{target_db_name}': {cols}")
        
        # Check counts
        for col in cols:
             count = db[col].count_documents({})
             print(f" - {col}: {count} docs")
             
             if count > 0:
                 print(f"   Sample: {list(db[col].find().limit(1))[0].keys()}")
    else:
        print(f"❌ Database '{target_db_name}' NOT found.")

except Exception as e:
    print(f"❌ Connection Failed: {e}")
