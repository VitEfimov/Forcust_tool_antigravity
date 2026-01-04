import sys
import os

# Set Env vars BEFORE importing src
os.environ["STORAGE_TYPE"] = "mongo"
os.environ["DATABASE_URL"] = "mongodb://localhost:27017"

sys.path.append(os.path.abspath("."))

try:
    from src.core.database import get_db
    print(f"Testing with STORAGE_TYPE={os.environ['STORAGE_TYPE']}")
    print("Attempting to fetch market history...")
    # This should hang/timeout if no mongo
    history = get_db().get_market_overview_history(limit=30)
    print("Success!")
    print(f"Items found: {len(history)}")
except Exception as e:
    print(f"Caught exception: {e}")
    # We expect this
