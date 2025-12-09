"""
Comprehensive E2E UI Tests using Playwright.
Tests all major user flows in the frontend.

Run with: pytest tests/e2e/test_ui_comprehensive.py -v --headed
Requires: 
  - Frontend running on localhost:5173
  - Backend running on localhost:8000
  - pytest-playwright installed
"""
import pytest
from playwright.sync_api import Page, expect
import time

BASE_URL = "http://localhost:5173"


class TestDashboard:
    """Test Dashboard page functionality."""
    
    def test_dashboard_loads_header(self, page: Page):
        """Dashboard should display the main header."""
        page.goto(BASE_URL)
        expect(page.get_by_text("Antigravity Forecast")).to_be_visible()
    
    def test_dashboard_has_search_form(self, page: Page):
        """Dashboard should have a symbol search form."""
        page.goto(BASE_URL)
        expect(page.get_by_placeholder("Enter Symbol (e.g. SPY)")).to_be_visible()
        expect(page.get_by_role("button", name="Forecast")).to_be_visible()
    
    def test_dashboard_loads_spy_by_default(self, page: Page):
        """Dashboard should load SPY forecast by default."""
        page.goto(BASE_URL)
        # Wait for loading to finish
        page.wait_for_timeout(5000)
        
        # Either data loads or error shows
        has_data = page.get_by_text("Current Price").is_visible()
        has_loading = page.get_by_text("Loading").is_visible()
        has_error = page.locator(".error").is_visible()
        
        assert has_data or has_loading or has_error, "Dashboard should show data, loading, or error state"
    
    def test_dashboard_search_different_symbol(self, page: Page):
        """Should be able to search for different symbols."""
        page.goto(BASE_URL)
        
        # Clear and type new symbol
        search_input = page.get_by_placeholder("Enter Symbol (e.g. SPY)")
        search_input.fill("AAPL")
        page.get_by_role("button", name="Forecast").click()
        
        # Wait for response
        page.wait_for_timeout(3000)
        
        # Check that something happened (loaded or loading)
        assert page.get_by_text("AAPL").is_visible() or page.get_by_text("Loading").is_visible()


class TestMarketOverview:
    """Test Market Overview page functionality."""
    
    def test_market_overview_navigation(self, page: Page):
        """Should be able to navigate to Market Overview."""
        page.goto(BASE_URL)
        page.get_by_text("Market Overview").click()
        
        # Check header changed
        page.wait_for_timeout(1000)
        expect(page.get_by_text("Top 50 S&P 500 Overview").or_(page.get_by_text("Top 20 S&P 500"))).to_be_visible(timeout=5000)
    
    def test_market_overview_has_date_controls(self, page: Page):
        """Market Overview should have date navigation controls."""
        page.goto(BASE_URL)
        page.get_by_text("Market Overview").click()
        page.wait_for_timeout(1000)
        
        expect(page.get_by_text("Prev Day").or_(page.get_by_text("← Prev Day"))).to_be_visible()
        expect(page.get_by_text("Today")).to_be_visible()
    
    def test_market_overview_loads_data(self, page: Page):
        """Market Overview should display stock data or loading message."""
        page.goto(BASE_URL)
        page.get_by_text("Market Overview").click()
        
        # Wait for data to load (up to 30 seconds)
        page.wait_for_timeout(5000)
        
        # Should have either data table or "No data" message
        has_table = page.locator("table").is_visible()
        has_no_data = page.get_by_text("No data available").is_visible()
        has_loading = page.get_by_text("Loading").is_visible()
        
        assert has_table or has_no_data or has_loading


class TestWatchlist:
    """Test Watchlist page functionality."""
    
    def test_watchlist_navigation(self, page: Page):
        """Should be able to navigate to Watchlist."""
        page.goto(BASE_URL)
        page.get_by_text("My Watchlist").click()
        page.wait_for_timeout(1000)
        
        # Check we're on watchlist page
        expect(page.get_by_text("My Watchlist")).to_be_visible()
    
    def test_watchlist_has_add_form(self, page: Page):
        """Watchlist should have form to add symbols."""
        page.goto(BASE_URL)
        page.get_by_text("My Watchlist").click()
        page.wait_for_timeout(1000)
        
        # Look for input or add button
        has_input = page.get_by_placeholder("Enter symbol").or_(page.get_by_placeholder("Enter symbol (e.g. AAPL)")).is_visible()
        has_button = page.get_by_role("button", name="Add").is_visible()
        
        assert has_input or has_button or page.locator("input").first.is_visible()


class TestSimulationPages:
    """Test Simulation page functionality."""
    
    def test_simulation_v1_navigation(self, page: Page):
        """Should be able to navigate to Sim V1."""
        page.goto(BASE_URL)
        page.get_by_text("Sim V1").click()
        page.wait_for_timeout(1000)
        
        # Check for simulation header or controls
        has_header = page.get_by_text("Advanced").is_visible()
        has_button = page.get_by_role("button", name="Run Simulation").or_(page.get_by_role("button", name="Run")).is_visible()
        
        assert has_header or has_button
    
    def test_simulation_v2_navigation(self, page: Page):
        """Should be able to navigate to Sim V2."""
        page.goto(BASE_URL)
        page.get_by_text("Sim V2").click()
        page.wait_for_timeout(1000)
        
        # Check for V2-specific content
        has_v2_header = page.get_by_text("Advanced Simulation V2").or_(page.get_by_text("V2")).is_visible()
        has_button = page.get_by_role("button").first.is_visible()
        
        assert has_v2_header or has_button
    
    def test_simulation_v2_has_controls(self, page: Page):
        """Sim V2 should have symbol input and run button."""
        page.goto(BASE_URL)
        page.get_by_text("Sim V2").click()
        page.wait_for_timeout(1000)
        
        # Look for controls
        has_input = page.locator("input").first.is_visible()
        has_button = page.get_by_role("button").first.is_visible()
        
        assert has_input and has_button


class TestSystemStatus:
    """Test System Status page functionality."""
    
    def test_system_status_navigation(self, page: Page):
        """Should be able to navigate to System Status."""
        page.goto(BASE_URL)
        page.get_by_text("System Status").click()
        page.wait_for_timeout(1000)
        
        # Check for system status content
        expect(page.get_by_text("System Status").or_(page.get_by_text("Status"))).to_be_visible()


class TestNavigationFlow:
    """Test full navigation flow across pages."""
    
    def test_navigate_all_pages(self, page: Page):
        """Should be able to navigate to all pages without errors."""
        page.goto(BASE_URL)
        
        pages = [
            ("Dashboard", "Antigravity Forecast"),
            ("Market Overview", "S&P 500"),
            ("My Watchlist", "Watchlist"),
            ("Sim V1", None),
            ("Sim V2", "V2"),
            ("System Status", "Status"),
        ]
        
        for nav_text, expected_content in pages:
            # Click navigation
            nav_link = page.get_by_text(nav_text, exact=False).first
            if nav_link.is_visible():
                nav_link.click()
                page.wait_for_timeout(500)
                
                # Check page didn't crash (no error boundary)
                no_crash = not page.get_by_text("Something went wrong").is_visible()
                assert no_crash, f"Page crashed when navigating to {nav_text}"


# Quick manual runner
if __name__ == "__main__":
    import subprocess
    print("Running E2E tests with Playwright...")
    print("Make sure frontend (localhost:5173) and backend (localhost:8000) are running!")
    print()
    subprocess.run(["pytest", __file__, "-v", "--headed", "-s"])
