import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.services.logic import MarketService, SimulationService
from src.core.config import settings

def test_services():
    print("🚀 Starting Service Response Test...")
    
    market_service = MarketService()
    simulation_service = SimulationService()
    
    symbol = "SPY"
    date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n--- Testing MarketService for {symbol} on {date} ---")
    start = time.time()
    try:
        overview = market_service.get_overview(symbol, date)
        elapsed = time.time() - start
        print(f"✅ MarketService Success ({elapsed:.2f}s)")
        print(f"   Price: {overview.price}")
        print(f"   Regime: {overview.regime}")
        print(f"   Volatility: {overview.volatility:.4f}")
    except Exception as e:
        print(f"❌ MarketService Failed: {e}")

    print(f"\n--- Testing SimulationService for {symbol} on {date} ---")
    start = time.time()
    try:
        # Test with a small horizon list for speed
        horizons = [10, 30]
        result = simulation_service.run_simulation(symbol, date, horizons)
        elapsed = time.time() - start
        print(f"✅ SimulationService Success ({elapsed:.2f}s)")
        print(f"   Regime: {result['regime']}")
        print(f"   Runs: {len(result['runs'])}")
        for run in result['runs']:
            print(f"   - Horizon {run['horizon']}d: P50={run['p50']:.2f}")
    except Exception as e:
        print(f"❌ SimulationService Failed: {e}")

if __name__ == "__main__":
    test_services()
