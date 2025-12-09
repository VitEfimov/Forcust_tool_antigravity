import pytest
import os
import shutil
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Set env vars BEFORE importing database/settings
os.environ["STORAGE_TYPE"] = "excel"
os.environ["LOCAL_DATA_DIR"] = "data/test_local"

from src.core.database import Database, get_db
from src.core.config import settings

@pytest.fixture
def clean_db():
    """Setup and teardown for local Excel db."""
    local_dir = Path("data/test_local")
    if local_dir.exists():
        shutil.rmtree(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    
    # Force re-init of singleton if needed, or just create new instance
    db = Database()
    yield db
    
    # Teardown
    if local_dir.exists():
        shutil.rmtree(local_dir)

def test_init_creates_files(clean_db):
    """Test that initialization creates the necessary Excel files."""
    assert clean_db.watchlist_file.exists()
    assert clean_db.forecasts_file.exists()
    
    df_wl = pd.read_excel(clean_db.watchlist_file)
    assert "symbol" in df_wl.columns
    
    df_fc = pd.read_excel(clean_db.forecasts_file)
    assert "prediction" in df_fc.columns

def test_watchlist_crud(clean_db):
    """Test adding and removing from watchlist."""
    # Add
    clean_db.add_to_watchlist("AAPL")
    clean_db.add_to_watchlist("MSFT")
    
    # Read back directly
    df = pd.read_excel(clean_db.watchlist_file)
    assert "AAPL" in df['symbol'].values
    assert "MSFT" in df['symbol'].values
    
    # Add Duplicate (should allow but handle or ignore based on logic, our logic upserts/ignores)
    clean_db.add_to_watchlist("AAPL")
    df = pd.read_excel(clean_db.watchlist_file)
    # Our logic in database.py checks `if symbol not in df['symbol'].values`, so no duplicates
    assert len(df[df['symbol'] == 'AAPL']) == 1
    
    # Get via Method
    wl = clean_db.get_watchlist()
    assert "AAPL" in wl
    assert "MSFT" in wl
    assert len(wl) == 2
    
    # Remove
    clean_db.remove_from_watchlist("AAPL")
    wl = clean_db.get_watchlist()
    assert "AAPL" not in wl
    assert "MSFT" in wl
    assert len(wl) == 1

def test_forecast_crud(clean_db):
    """Test saving and retrieving forecasts."""
    date = datetime.now().strftime("%Y-%m-%d")
    symbol = "TEST"
    horizon = 10
    prediction = 150.0
    start_price = 140.0
    target_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    
    # Save
    clean_db.save_forecast(date, symbol, horizon, prediction, start_price, target_date)
    
    # Verify file
    df = pd.read_excel(clean_db.forecasts_file)
    assert len(df) == 1
    row = df.iloc[0]
    assert row['symbol'] == symbol
    assert row['prediction'] == prediction
    
    # Get History
    history = clean_db.get_history(symbol)
    assert len(history) == 1
    assert history[0]['prediction'] == prediction
    
    # Update mechanics (save same key with different value)
    new_prediction = 155.0
    clean_db.save_forecast(date, symbol, horizon, new_prediction, start_price, target_date)
    
    df = pd.read_excel(clean_db.forecasts_file)
    assert len(df) == 1 # Should still be 1 row
    assert df.iloc[0]['prediction'] == new_prediction

def test_update_actuals(clean_db):
    """Test updating actuals for past forecasts."""
    date = "2023-01-01"
    symbol = "OLD"
    horizon = 10
    start_price = 100.0
    # Target date in past
    target_date = "2023-01-11" 
    
    clean_db.save_forecast(date, symbol, horizon, 110.0, start_price, target_date)
    
    # Verify actual is None/NaN
    df = pd.read_excel(clean_db.forecasts_file)
    assert pd.isna(df.iloc[0]['actual'])
    
    # Update Actuals
    current_date = "2023-01-12"
    current_price = 105.0 # 5% gain approx
    
    clean_db.update_actuals(symbol, current_date, current_price)
    
    df = pd.read_excel(clean_db.forecasts_file)
    # Filter for the symbol we care about
    row = df[df['symbol'] == symbol].iloc[0]
    actual = row['actual']
    
    # Debug log (optional but kept for safety)
    try:
        with open("debug_log.txt", "w") as f:
            f.write(f"Actual: {actual}\n")
            f.write(f"Row:\n{row}\n")
    except:
        pass
    
    assert not pd.isna(actual), "Actual should not be NaN for symbol OLD"
    # Expected log return: ln(105/100) ~ 0.04879
    import numpy as np
    expected = np.log(105.0/100.0)
    assert abs(actual - expected) < 0.0001
    print("test_update_actuals passed")

if __name__ == "__main__":
    try:
        # Manually setup clean_db fixture logic
        local_dir = Path("data/test_local")
        if local_dir.exists():
            shutil.rmtree(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        
        db = Database()
        
        print("Running tests...")
        
        # We need to pass the db instance manually since we aren't using pytest runner
        class MockFixture:
            pass
        
        # Just use the db instance directly, the tests expect it as arg 'clean_db'
        test_init_creates_files(db)
        test_watchlist_crud(db)
        test_forecast_crud(db)
        test_update_actuals(db)
        
        print("ALL TESTS PASSED")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("TESTS FAILED")
    finally:
        # Teardown
        if local_dir.exists():
            shutil.rmtree(local_dir)
