import yfinance as yf
import pandas as pd

symbol = "AAPL"
print(f"Testing yfinance for {symbol}...")

try:
    ticker = yf.Ticker(symbol)
    # Try fetching a small period first
    df = ticker.history(period="1mo")
    print(f"Last month data shape: {df.shape}")
    print(df.head())
    
    # Try the loader's default params
    print("\nTesting with loader params (start='2000-01-01')...")
    df_long = ticker.history(start="2000-01-01")
    print(f"Long history shape: {df_long.shape}")
    if not df_long.empty:
        print(df_long.head())
        print(df_long.tail())
    else:
        print("Long history is empty!")

except Exception as e:
    print(f"Error: {e}")
