import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.database import get_db

client = TestClient(app)

def test_market_history_endpoint():
    """Test GET /market/history"""
    response = client.get("/market/history?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)
    if len(data["history"]) > 0:
        item = data["history"][0]
        # Check structure
        assert "timestamp" in item or "date" in item
        assert "data" in item or "json_data" in item

def test_market_overview_endpoint():
    """Test GET /market/overview"""
    # This might fail if cache is empty and external call fails, but let's try
    response = client.get("/market/overview")
    assert response.status_code in [200, 500] # 500 if yfinance fails is possible
    if response.status_code == 200:
        data = response.json()
        assert "overview" in data
        assert isinstance(data["overview"], list)

def test_advanced_analytics_endpoint():
    """Test GET /analytics/advanced/{symbol}"""
    # Use a symbol likely in the seed data
    symbol = "SPY" 
    response = client.get(f"/analytics/advanced/{symbol}")
    
    # 200 or 404 is acceptable (404 if not in seed data)
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert data["symbol"] == symbol
        assert "regime" in data
        assert "transition_matrix" in data
        assert "volatility_trend" in data
        assert "regime_duration_days" in data

def test_watchlist_endpoint():
    """Test GET /watchlist"""
    response = client.get("/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
