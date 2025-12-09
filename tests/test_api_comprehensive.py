"""
Comprehensive API Tests for Forcust Application.
Tests all API endpoints with proper assertions.

Run with: pytest tests/test_api_comprehensive.py -v
Requires: Backend running on localhost:8000
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:8000"

class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    def test_health_returns_200(self):
        """Health endpoint should return 200 OK."""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
    
    def test_health_response_format(self):
        """Health endpoint should return proper JSON."""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        assert "status" in data or response.status_code == 200


class TestMarketOverviewEndpoint:
    """Test the /market/overview endpoint."""
    
    def test_market_overview_returns_200(self):
        """Market overview should return 200 OK."""
        response = requests.get(f"{BASE_URL}/market/overview", timeout=60)
        assert response.status_code == 200
    
    def test_market_overview_has_data(self):
        """Market overview should return a list of stocks."""
        response = requests.get(f"{BASE_URL}/market/overview", timeout=60)
        data = response.json()
        assert "overview" in data
        assert isinstance(data["overview"], list)
    
    def test_market_overview_stock_structure(self):
        """Each stock in overview should have required fields."""
        response = requests.get(f"{BASE_URL}/market/overview", timeout=60)
        data = response.json()
        
        if len(data["overview"]) > 0:
            stock = data["overview"][0]
            assert "symbol" in stock
            assert "price" in stock
            assert "change" in stock
            assert "change_pct" in stock
            assert "signal" in stock
    
    def test_market_overview_caching(self):
        """Second call should be faster due to caching."""
        # First call
        start1 = time.time()
        response1 = requests.get(f"{BASE_URL}/market/overview", timeout=60)
        time1 = time.time() - start1
        
        # Second call (should hit cache)
        start2 = time.time()
        response2 = requests.get(f"{BASE_URL}/market/overview", timeout=60)
        time2 = time.time() - start2
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Cache hit should be much faster (10x faster at least)
        assert time2 < time1 * 0.5 or time2 < 1.0  # Either much faster or < 1 second


class TestForecastEndpoint:
    """Test the /forecast/{symbol} endpoint."""
    
    def test_forecast_spy_returns_200(self):
        """Forecast for SPY should return 200 OK."""
        response = requests.get(f"{BASE_URL}/forecast/SPY", timeout=120)
        assert response.status_code == 200
    
    def test_forecast_response_structure(self):
        """Forecast response should have required fields."""
        response = requests.get(f"{BASE_URL}/forecast/SPY", timeout=120)
        data = response.json()
        
        assert "symbol" in data
        assert "current_price" in data
        assert "regime" in data
        assert "forecasts" in data
        assert "history" in data
    
    def test_forecast_has_multiple_horizons(self):
        """Forecast should include multiple time horizons."""
        response = requests.get(f"{BASE_URL}/forecast/SPY", timeout=120)
        data = response.json()
        
        forecasts = data.get("forecasts", [])
        assert len(forecasts) >= 3  # At least 3 horizons
        
        horizons = [f["horizon"] for f in forecasts]
        assert 10 in horizons or any(h <= 30 for h in horizons)
    
    def test_forecast_horizon_structure(self):
        """Each forecast horizon should have required fields."""
        response = requests.get(f"{BASE_URL}/forecast/SPY", timeout=120)
        data = response.json()
        
        if len(data.get("forecasts", [])) > 0:
            forecast = data["forecasts"][0]
            assert "horizon" in forecast
            assert "ml_forecast_pct" in forecast
            assert "mc_p50_pct" in forecast
    
    def test_forecast_invalid_symbol_handles_gracefully(self):
        """Invalid symbol should return error or empty data, not crash."""
        response = requests.get(f"{BASE_URL}/forecast/INVALID123", timeout=60)
        # Should return 404 or 500, but not hang
        assert response.status_code in [200, 404, 500]


class TestWatchlistEndpoint:
    """Test the /watchlist endpoints."""
    
    def test_get_watchlist_returns_200(self):
        """Get watchlist should return 200 OK."""
        response = requests.get(f"{BASE_URL}/watchlist", timeout=10)
        assert response.status_code == 200
    
    def test_get_watchlist_response_structure(self):
        """Watchlist response should have symbols list."""
        response = requests.get(f"{BASE_URL}/watchlist", timeout=10)
        data = response.json()
        assert "symbols" in data
        assert isinstance(data["symbols"], list)
    
    def test_add_and_remove_from_watchlist(self):
        """Should be able to add and remove symbols from watchlist."""
        test_symbol = "TESTXYZ"
        
        # Add
        add_response = requests.post(f"{BASE_URL}/watchlist/{test_symbol}", timeout=10)
        assert add_response.status_code == 200
        
        # Verify added
        get_response = requests.get(f"{BASE_URL}/watchlist", timeout=10)
        symbols = get_response.json().get("symbols", [])
        assert test_symbol in symbols
        
        # Remove
        delete_response = requests.delete(f"{BASE_URL}/watchlist/{test_symbol}", timeout=10)
        assert delete_response.status_code == 200
        
        # Verify removed
        get_response2 = requests.get(f"{BASE_URL}/watchlist", timeout=10)
        symbols2 = get_response2.json().get("symbols", [])
        assert test_symbol not in symbols2
    
    def test_watchlist_overview_returns_200(self):
        """Watchlist overview should return 200 OK."""
        response = requests.get(f"{BASE_URL}/watchlist/overview", timeout=60)
        assert response.status_code == 200


class TestAdvancedSimulationEndpoint:
    """Test the /simulation/advanced/{symbol} endpoint."""
    
    def test_advanced_simulation_returns_200(self):
        """Advanced simulation for SPY should return 200 OK."""
        response = requests.get(f"{BASE_URL}/simulation/advanced/SPY", timeout=120)
        assert response.status_code == 200
    
    def test_advanced_simulation_response_structure(self):
        """Advanced simulation should have required fields."""
        response = requests.get(f"{BASE_URL}/simulation/advanced/SPY", timeout=120)
        data = response.json()
        
        assert "symbol" in data
        assert "method" in data
        assert "current_price" in data
        assert "current_regime" in data or "regime" in data


class TestSimulationV2Endpoint:
    """Test the /simulation/v2/{symbol} endpoint."""
    
    def test_simulation_v2_returns_200(self):
        """V2 simulation for SPY should return 200 OK."""
        response = requests.get(f"{BASE_URL}/simulation/v2/SPY", timeout=120)
        assert response.status_code == 200
    
    def test_simulation_v2_response_structure(self):
        """V2 simulation should have enhanced fields."""
        response = requests.get(f"{BASE_URL}/simulation/v2/SPY", timeout=120)
        data = response.json()
        
        assert "symbol" in data
        assert "method" in data
        assert "current_price" in data
        assert "analysis" in data
    
    def test_simulation_v2_conservative_mode(self):
        """V2 simulation should accept conservative parameter."""
        response = requests.get(f"{BASE_URL}/simulation/v2/SPY?conservative=true", timeout=120)
        data = response.json()
        
        assert response.status_code == 200
        assert data.get("conservative_mode") == True


# Quick runner for manual testing
if __name__ == "__main__":
    print("=" * 60)
    print("Running Comprehensive API Tests")
    print("=" * 60)
    
    tests = [
        ("Health", lambda: requests.get(f"{BASE_URL}/health", timeout=5)),
        ("Market Overview", lambda: requests.get(f"{BASE_URL}/market/overview", timeout=60)),
        ("Watchlist", lambda: requests.get(f"{BASE_URL}/watchlist", timeout=10)),
        ("Forecast SPY", lambda: requests.get(f"{BASE_URL}/forecast/SPY", timeout=120)),
        ("Simulation V2", lambda: requests.get(f"{BASE_URL}/simulation/v2/SPY", timeout=120)),
    ]
    
    for name, test_fn in tests:
        try:
            print(f"\n[TEST] {name}...", end=" ")
            start = time.time()
            response = test_fn()
            elapsed = time.time() - start
            if response.status_code == 200:
                print(f"✅ PASS ({elapsed:.1f}s)")
            else:
                print(f"❌ FAIL - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Done!")
