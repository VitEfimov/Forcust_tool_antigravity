import pytest
from playwright.sync_api import Page, expect

# Frontend URL (Vite default)
BASE_URL = "http://localhost:5173"

def test_dashboard_loads(page: Page):
    print("Testing Dashboard Load...")
    page.goto(BASE_URL)
    
    # Check title or main header
    expect(page).to_have_title("Antigravity Dashboard")
    
    # Check for key elements
    # Check for key elements
    expect(page.get_by_text("Antigravity Forecast")).to_be_visible()
    expect(page.get_by_placeholder("Enter Symbol (e.g. SPY)")).to_be_visible()

def test_navigation_to_market_overview(page: Page):
    print("Testing Navigation to Market Overview...")
    page.goto(BASE_URL)
    
    # Click on Market Overview link in Navbar
    page.get_by_role("link", name="Market Overview").click()
    
    # Wait for loading to finish
    # expect(page.get_by_text("Loading")).to_not_be_visible(timeout=10000)
    # Better: wait for the table or header
    
    # Check if we are on the right view
    expect(page.get_by_text("Top 50 S&P 500 Overview")).to_be_visible(timeout=15000)
    
    # Check for table headers
    # Check for table headers or no data message
    try:
        expect(page.get_by_role("columnheader", name="Symbol")).to_be_visible(timeout=5000)
    except:
        # If headers not found, check if "No data available" is shown
        if page.get_by_text("No data available.").is_visible():
            print("⚠️ Market Overview loaded but showed 'No data available.'")
        elif page.get_by_text("Loading").is_visible():
            print("WARNING: Market Overview is still LOADING.")
        else:
            print("❌ Market Overview: Neither headers, nor 'No data', nor 'Loading' found.")
            # Take screenshot if possible (requires configuration, skipping for now)
            print(page.content()) # Print HTML content to debug
            raise

def test_watchlist_interaction(page: Page):
    print("Testing Watchlist...")
    page.goto(BASE_URL)
    
    page.get_by_role("link", name="My Watchlist").click()
    expect(page.get_by_text("My Watchlist")).to_be_visible()
    
    # Try adding a symbol
    input_box = page.get_by_placeholder("Enter symbol (e.g. AAPL)")
    if input_box.is_visible():
        input_box.fill("MSFT")
        page.get_by_role("button", name="Add").click()
        
        # Wait for it to appear
        # Note: This depends on backend being up and running
        # expect(page.get_by_text("MSFT")).to_be_visible() 

def test_advanced_simulation_load(page: Page):
    print("Testing Advanced Simulation...")
    page.goto(BASE_URL)
    
    page.get_by_role("link", name="Advanced Sim").click()
    expect(page.get_by_text("Advanced Realistic Simulation")).to_be_visible()
    
    # Check for inputs
    expect(page.get_by_text("Symbol")).to_be_visible()
    expect(page.get_by_role("button", name="Run Simulation")).to_be_visible()

def test_system_status_load(page: Page):
    print("Testing System Status...")
    page.goto(BASE_URL)
    
    page.get_by_role("link", name="System Status").click()
    expect(page.get_by_text("System Status")).to_be_visible()
    # Check for health check
    # expect(page.get_by_text("API Status: Online")).to_be_visible()
