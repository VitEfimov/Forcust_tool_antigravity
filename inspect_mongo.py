import os
import sys

# Ensure pymongo is available
try:
    import pymongo
except ImportError:
    print("pymongo not installed")
    sys.exit(1)

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.get_database("antigravity")

print("Collections in 'antigravity' database:")
collections = db.list_collection_names()
print(collections)

for col in collections:
    count = db[col].count_documents({})
    print(f"Collection '{col}' has {count} documents")
    if count > 0:
        print(f"Sample from '{col}':")
        print(db[col].find_one())
        print("-" * 20)
