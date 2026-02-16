import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.core.repository import MarketRepository, SimulationRepository, WishlistRepository
from src.core.models import MarketOverview, SimulationRun

def test_repositories():
    print("--- Testing Repositories ---")
    
    # 1. Market Repository
    print("\n[MarketRepository]")
    market_repo = MarketRepository()
    try:
        dates = market_repo.get_available_dates()
        print(f"Available Dates: {dates}")
        
        # Create a dummy overview
        dummy = MarketOverview(
            symbol="TEST_REPO",
            date=datetime.now().strftime("%Y-%m-%d"),
            regime="Test",
            price=100.0,
            volatility=0.2
        )
        saved = market_repo.create(dummy)
        print(f"Saved: {saved.symbol}")
        
        fetched = market_repo.find_by_date("TEST_REPO", dummy.date)
        if fetched:
            print(f"Pooled: {fetched.symbol} - {fetched.price}")
        else:
            print("Failed to fetch saved item.")
            
    except Exception as e:
        print(f"MarketRepo Error: {e}")

    # 2. Simulation Repository
    print("\n[SimulationRepository]")
    sim_repo = SimulationRepository()
    try:
        run = SimulationRun(
            symbol="TEST_SIM",
            date=datetime.now().strftime("%Y-%m-%d"),
            horizon=10,
            ml_forecast=0.05,
            p10=90.0,
            p50=105.0,
            p90=120.0,
            regime="Bull"
        )
        sim_repo.create(run)
        print(f"Saved Simulation Run: {run.symbol}")
        
        fetched_run = sim_repo.find_run("TEST_SIM", run.date, 10)
        if fetched_run:
             print(f"Fetched Run: {fetched_run.symbol} - P50: {fetched_run.p50}")
        else:
             print("Failed to fetch simulation run.")

    except Exception as e:
        print(f"SimRepo Error: {e}")

if __name__ == "__main__":
    test_repositories()
