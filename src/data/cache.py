import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

class DataCache:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, symbol: str) -> Path:
        return self.cache_dir / f"{symbol}.parquet"

    def save(self, symbol: str, data: pd.DataFrame):
        """Save dataframe to cache."""
        file_path = self._get_file_path(symbol)
        # Ensure index is datetime and sorted
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        data = data.sort_index()
        data.to_parquet(file_path)

    def load(self, symbol: str, max_age_hours: int = 24) -> pd.DataFrame:
        """
        Load dataframe from cache if it exists and is not too old.
        Returns None if cache miss or expired.
        """
        file_path = self._get_file_path(symbol)
        
        if not file_path.exists():
            return None

        # Check modification time
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=max_age_hours):
            return None

        try:
            return pd.read_parquet(file_path)
        except Exception as e:
            print(f"Error reading cache for {symbol}: {e}")
            return None
