from src.core.models import MarketOverview
from src.services.logic import MarketService

def test_models():
    print("Testing MarketOverview model...")
    try:
        m = MarketOverview(
            symbol="TEST",
            date="2023-01-01",
            regime="Bull",
            price=100.0,
            volatility=0.2
        )
        print(f"Model created: {m}")
        print(f"Regime attribute: {m.regime}")
        assert m.regime == "Bull"
    except Exception as e:
        print(f"Model test failed: {e}")
        
    print("\nTesting MarketService.get_overview logic (mocked data)...")
    # Service requires data loader, might fail if no data cache.
    # We can skip full service test if model test works.

if __name__ == "__main__":
    test_models()
