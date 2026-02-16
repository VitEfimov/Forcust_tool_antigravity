import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.services.logic import MarketService

def test_market_service():
    print("--- Testing Market Service (Repository Integration) ---")
    
    service = MarketService()
    
    # 1. Test get_available_dates
    print("\n[Get Available Dates]")
    dates_info = service.get_available_dates()
    print(f"Dates Info: {dates_info}")
    
    # 2. Test get_overview (should hit DB if data exists, else compute)
    # Use a symbol likely to exist or compute fast
    symbol = "SPY" 
    date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n[Get Overview for {symbol} on {date}]")
    try:
        overview = service.get_overview(symbol, date)
        print(f"Result Type: {type(overview)}")
        if hasattr(overview, 'price'):
            print(f"Price: {overview.price}")
            print(f"Regime: {overview.regime}")
        else:
            print("Overview returned dict (legacy?) or None")
            print(overview)
            
    except Exception as e:
        print(f"Service Error: {e}")

if __name__ == "__main__":
    test_market_service()
