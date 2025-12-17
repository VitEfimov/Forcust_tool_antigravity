
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np
from datetime import datetime

# Import the app (will patch start_scheduler before imported or during import)
# Since app imports scheduler at top level, we need to be careful. 
# actually src.api.main imports start_scheduler but calls it in lifespan.
# So we can patch it easily.

with patch("src.core.scheduler.start_scheduler"), \
     patch("src.core.monitoring.monitor"):
    from src.api.main import app

client = TestClient(app)

# --- Mocks ---

@pytest.fixture
def mock_market_overview():
    with patch("src.api.routes._compute_market_overview") as mock:
        mock.return_value = {
            "overview": [
                {
                    "symbol": "SPY",
                    "price": 450.0,
                    "change": 2.5,
                    "change_pct": 0.55,
                    "volume": 50000000,
                    "risk_label": "Moderate",
                    "regime": "Uptrend",
                    "volatility_outlook": "Stable"
                }
            ]
        }
        yield mock

@pytest.fixture
def mock_forecast():
    with patch("src.api.routes._compute_full_forecast") as mock:
        mock.return_value = {
            "symbol": "SPY",
            "current_price": 450.0,
            "regime": "Bull",
            "history": [],
            "forecasts": [
                {
                    "horizon": 10,
                    "ml_forecast_pct": 1.5,
                    "mc_p50_pct": 1.2,
                    "risk_assessment": "Neutral"
                }
            ]
        }
        yield mock

@pytest.fixture
def mock_advanced_sim():
    with patch("src.api.routes._compute_advanced_simulation") as mock:
        mock.return_value = {
            "symbol": "SPY",
            "method": "V2: Mocked",
            "current_price": 450.0,
            "current_regime": {"id": 1, "label": "Bull"},
            "transition_matrix": [[0.8, 0.2], [0.3, 0.7]],
            "conservative_mode": False,
            "analysis": {
                "10": {
                    "horizon_days": 10,
                    "p50": 460.0,
                    "median_change_pct": 2.2,
                    "risk_label": "Moderate"
                }
            },
            "paths_sample": []
        }
        yield mock

@pytest.fixture
def mock_loader():
    with patch("src.api.routes.DataLoader") as MockLoader:
        loader_instance = MockLoader.return_value
        # Mock get_data to return a small DataFrame
        df = pd.DataFrame({
            "Close": [100.0, 101.0, 102.0],
            "Volume": [1000, 1100, 1200],
            "Date": [datetime.now(), datetime.now(), datetime.now()]
        })
        loader_instance.get_data.return_value = df
        yield MockLoader

@pytest.fixture
def mock_pipeline():
    with patch("src.api.routes.FeaturePipeline") as MockPipeline:
        pipeline = MockPipeline.return_value
        pipeline.get_inference_data.return_value = pd.DataFrame([{"feat": 1}])
        yield MockPipeline

@pytest.fixture
def mock_registry():
    with patch("src.api.routes.ModelRegistry") as MockRegistry:
        yield MockRegistry

@pytest.fixture
def mock_check_busy():
    # Helper to override the check_busy dependency
    # In FastAPI, we override app.dependency_overrides
    app.dependency_overrides[check_busy_mock_func] = lambda: None
    yield
    app.dependency_overrides = {}

def check_busy_mock_func():
    pass

# --- Tests ---

def test_health_check():
    response = client.get("/health")
    # Note: If /health isn't explicitly defined in main.py or routes.py, it might fallback to root or 404.
    # checking main.py again... there is NO /health, only / and routes.
    # Looking at routes.py... no /health there either.
    # Maybe it was added in a previous step? 
    # Let's check root "/"
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_market_overview(mock_market_overview):
    response = client.get("/market/overview")
    assert response.status_code == 200
    data = response.json()
    assert "overview" in data
    assert data["overview"][0]["symbol"] == "SPY"
    mock_market_overview.assert_called()

def test_watchlist_overview_empty():
    # Need to mock get_watchlist
    with patch("src.api.routes.get_watchlist", return_value=[]):
        response = client.get("/watchlist/overview")
        assert response.status_code == 200
        assert response.json()["overview"] == []

def test_watchlist_overview_with_items(mock_market_overview):
    with patch("src.api.routes.get_watchlist", return_value=["SPY"]):
        response = client.get("/watchlist/overview")
        assert response.status_code == 200
        # Should call market overview logic
        # But wait, routes.py has a caching layer: _cached_watchlist_overview
        # which calls _compute_market_overview.
        # Since we mocked _compute_market_overview, it should be fine.
        assert "overview" in response.json()

def test_forecast_endpoint(mock_forecast):
    response = client.get("/forecast/SPY")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert data["regime"] == "Bull"

def test_simulation_v2_endpoint(mock_advanced_sim):
    # Depending on check_busy? The route uses `_=Depends(check_busy)`
    # We need to override it or ensure mock_monitor returns clean heartbeats.
    
    # We can override the dependency with an empty lambda
    from src.api.routes import check_busy
    app.dependency_overrides[check_busy] = lambda: None
    
    response = client.get("/simulation/v2/SPY")
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "V2: Mocked"
    
    # Cleanup overrides
    app.dependency_overrides = {}

def test_save_simulation():
    # Need to mock file writing logic
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        with patch("pathlib.Path.mkdir"): # prevent actual dir creation
            dummy_data = {"symbol": "TEST", "result": "ok"}
            response = client.post("/simulation/save", json=dummy_data)
            assert response.status_code == 200
            assert response.json()["status"] == "success"

def test_available_indices():
    response = client.get("/indices")
    assert response.status_code == 200
    data = response.json()
    assert "indices" in data
    assert any(i["symbol"] == "^GSPC" for i in data["indices"])

def test_add_remove_watchlist():
    with patch("src.api.routes.add_to_watchlist") as mock_add:
        response = client.post("/watchlist/AAPL")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_add.assert_called_with("AAPL")

    with patch("src.api.routes.remove_from_watchlist") as mock_remove:
        response = client.delete("/watchlist/AAPL")
        assert response.status_code == 200
        mock_remove.assert_called_with("AAPL")

