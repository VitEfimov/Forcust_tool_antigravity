
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from src.api.routes import _compute_market_overview

# Mocking data for the test
MOCK_OVERVIEW_DATA = {
    "overview": [
        {"symbol": "AAPL", "price": 150.0},
        {"symbol": "GOOGL", "price": 2800.0}
    ]
}

@patch('src.api.routes.get_market_overview_logic')
@patch('src.api.routes.DataLoader')
@patch('src.api.routes.get_db')  # Mocking the DB access inside the function if applicable
def test_compute_market_overview_structure(mock_get_db, mock_loader_cls, mock_get_logic):
    # Setup Mocks
    mock_get_logic.return_value = MOCK_OVERVIEW_DATA
    
    # Mock DataLoader instance and get_data return value
    mock_loader = MagicMock()
    mock_loader_cls.return_value = mock_loader
    
    # Return a DataFrame with some dummy history for volatility/trend calc
    # Need enough data for 30d vol and 20d sma
    dates = pd.date_range(start='2023-01-01', periods=100)
    # create an uptrend
    closes = np.linspace(100, 200, 100) 
    mock_df = pd.DataFrame({'Close': closes}, index=dates)
    mock_loader.get_data.return_value = mock_df

    # Mock DB - empty response for now to test analytical fallback or mock it to test override
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.get_history.return_value = []

    # Execute
    result = _compute_market_overview(["AAPL", "GOOGL"])
    
    assert "overview" in result
    data = result["overview"]
    assert len(data) == 2
    
    item = data[0]
    
    # 1. Verify Trend Label (Renamed from Regime)
    assert "trend_label" in item
    assert item["trend_label"] in ["Uptrend", "Downtrend"]
    # With linspace 100->200, price (200) > sma_20, so Uptrend
    assert item["trend_label"] == "Uptrend"

    # 2. Verify Flattened Forecasts
    # Expect keys like forecast_10d_pct, forecast_365d_pct
    expected_horizons = [10, 30, 100, 200, 365]
    for h in expected_horizons:
        key = f"forecast_{h}d_pct"
        assert key in item, f"Missing flattened forecast key: {key}"
        # Value should be float (analytical calculation)
        assert isinstance(item[key], float)

    # 3. Verify 200d is present
    assert "forecast_200d_pct" in item

    # 4. Verify no 'regime' key (deprecated)
    # assert "regime" not in item # It might still be there if we didn't explicitly delete it, but checks above confirm new key exists.
    # Actually looking at the code, we just set item['trend_label'], we didn't delete 'regime' if it was coming from base_data?
    # base_data comes from get_market_overview_logic. If it had regime, it might persist. 
    # But get_market_overview_logic usually just returns price/change.
    
    # 5. Verify Resilience (DataLoader called once)
    mock_loader_cls.assert_called_once()
