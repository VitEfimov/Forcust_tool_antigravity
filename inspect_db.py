from src.core.database import get_db
from datetime import datetime

db = get_db()
print("--- Checking Walk Forward Results ---")
# Get latest 5 results (collection name from database.py seems to be 'walk_forward' or 'results'?)
# Actually, let's just print collection names
print(f"Collections: {db.list_collection_names()}")
# Try 'walk_forward_results' or 'walk_forward' based on typical patterns
results = list(db['walk_forward_results'].find().sort("created_at", -1).limit(5))

for r in results:
    print(f"Symbol: {r.get('symbol')}")
    print(f"Horizon: {r.get('horizon')}") # Note: horizon might not be in root of WF result if not added, checking structure
    print(f"Date: {r.get('date')} (Type: {type(r.get('date'))})")
    print(f"Pred: {r.get('prediction_price')}")
    print(f"Reliability: {r.get('reliability_score')}")
    print("-" * 20)
