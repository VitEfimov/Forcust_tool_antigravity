import yfinance as yf
import pandas as pd
from typing import Optional
from .cache import DataCache

class DataLoader:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache = DataCache(cache_dir)
        self.symbol_map = {
            "S&P 500": "SPY",
            "SP500": "SPY",
            "GSPC": "SPY",
            "NASDAQ": "QQQ",
            "IXIC": "QQQ",
            "DJIA": "DIA",
            "DOW": "DIA",
            "RUSSELL": "IWM",
            "RUT": "IWM",
            "VIX": "^VIX"
        }

    def resolve_symbol(self, symbol: str) -> str:
        """Map common names to Yahoo Finance tickers."""
        clean_symbol = symbol.upper().strip()
        return self.symbol_map.get(clean_symbol, clean_symbol)

    def get_data(self, symbol: str, start_date: str = "2000-01-01", end_date: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol.
        Tries cache first, then falls back to yfinance.
        """
        symbol = self.resolve_symbol(symbol)

        if use_cache:
            df = self.cache.load(symbol)
            if df is not None:
                print(f"Loaded {symbol} from cache.")
                return df

        print(f"Fetching {symbol} from yfinance...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                print(f"No data found for {symbol}")
                return pd.DataFrame()

            # Clean up columns (remove Dividends, Stock Splits if present, keep OHLCV)
            keep_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df[[c for c in keep_cols if c in df.columns]]
            
            # Ensure index is timezone-naive for simplicity in this skeleton
            df.index = df.index.tz_localize(None)

            if use_cache:
                self.cache.save(symbol, df)
                
            return df
        except Exception as e:
            import traceback
            with open("loader_error.log", "a") as f:
                f.write(f"Error fetching {symbol}: {e}\n")
                f.write(traceback.format_exc())
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
