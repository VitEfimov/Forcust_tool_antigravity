from src.api.routes import get_forecast
from src.core.config import settings
import traceback

# Mock settings if needed, but they are imported in routes
# We need to mock FastAPI dependencies if any? 
# get_forecast takes symbol: str.

try:
    print("Testing get_forecast('SP500')...")
    result = get_forecast("SP500")
    print("Success!")
    print(result)
except Exception:
    traceback.print_exc()
