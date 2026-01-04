import pymongo
import json
from datetime import datetime

# Helper to serialize datetimes
def my_converter(o):
    if isinstance(o, datetime):
        return o.__str__()
    return o.__str__()

db_url = "mongodb+srv://vitvalef_db_user:yftZ097dE2hrlAbY@cluster0.c6x0pdu.mongodb.net/?appName=Cluster0"
client = pymongo.MongoClient(db_url)
db = client.get_database("antigravity")

print("\n--- Market OVERVIEWS (1 doc) ---")
doc = db.market_overviews.find_one()
if doc:
    # Print keys and nested keys
    print(f"Keys: {doc.keys()}")
    if 'data' in doc:
        print(f"Data keys: {doc['data'].keys() if isinstance(doc['data'], dict) else 'Not a dict'}")
        if 'overview' in doc.get('data', {}):
             ov = doc['data']['overview']
             print(f"Overview items: {len(ov) if isinstance(ov, list) else 'Not a list'}")
    print(json.dumps(doc, default=my_converter, indent=2))
else:
    print("None")

print("\n--- Market SUMMARIES (Sample) ---")
doc = db.market_summaries.find_one()
if doc:
     print(json.dumps(doc, default=my_converter, indent=2))
else:
     print("None")
