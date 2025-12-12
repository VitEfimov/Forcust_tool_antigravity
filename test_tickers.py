
import yfinance as yf

def test_tickers():
    candidates = [
        # Derivatives
        "^VVIX", "^SKEW", 
        # Breadth
        "^NYAD", 
        # Credit
        "HYG", "LQD",
        # Liquidity (Unlikely on YF but testing)
        "WALCL", "RRPONTSYD",
        # Potential Proxies
        "^VIX", "SPY"
    ]
    
    print("Testing Tickers...")
    for sym in candidates:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if not hist.empty:
                print(f"[OK] {sym}: {len(hist)} rows")
            else:
                print(f"[FAIL] {sym}: No Data")
        except Exception as e:
            print(f"[ERR] {sym}: {e}")

if __name__ == "__main__":
    test_tickers()
