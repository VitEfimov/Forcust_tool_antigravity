import os
import sys

try:
    import pymongo
except ImportError:
    print("pymongo not installed")
    sys.exit(1)

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.get_database("antigravity")

cols = db.list_collection_names()
print(f"Collections: {cols}")

if "antigravity" in cols:
    print("Found 'antigravity' collection!")
    count = db.antigravity.count_documents({})
    print(f"Count: {count}")
    print("Sample:", db.antigravity.find_one())
else:
    print("'antigravity' collection NOT found.")
