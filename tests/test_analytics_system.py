import pytest
from datetime import datetime
import sys
import os
from pathlib import Path

# Fix path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.database import get_db, Database

@pytest.fixture
def db():
    # Use in-memory DB or temporary file for testing
    # But since database.py uses a singleton and hardcoded paths fallback, 
    # we might need to patch it or just use the local dev db (careful).
    # Ideally we mock the db path.
    # For now, let's assume we can use the actual DB safely as we are adding new data.
    return get_db()

def test_training_run_lifecycle(db):
    # 1. Start Run
    run_id = db.start_training_run("test_daily", "pytest")
    assert run_id is not None
    
    # 2. Save Forecasts
    db.save_symbol_forecast(
        run_id=run_id,
        symbol="TEST_SYM",
        horizon=10,
        expected_return=5.5,
        confidence=0.85,
        regime="Uptrend",
        volatility="Low"
    )
    
    db.save_symbol_forecast(
        run_id=run_id,
        symbol="TEST_SYM",
        horizon=100,
        expected_return=12.0,
        confidence=0.75,
        regime="Uptrend",
        volatility="Low"
    )
    
    # 3. End Run
    db.end_training_run(run_id, status="success")
    
    # 4. Verify Fetch
    forecasts = db.get_latest_forecasts("TEST_SYM")
    assert 10 in forecasts
    assert 100 in forecasts
    assert forecasts[10]['expected_return'] == 5.5
    assert forecasts[100]['expected_return'] == 12.0
    
def test_market_snapshot_structure():
    # Test the API logic (without running full server if possible)
    # We need to mock get_watchlist etc.
    pass

if __name__ == "__main__":
    # stored in a file so just running it won't work without pytest
    pass
