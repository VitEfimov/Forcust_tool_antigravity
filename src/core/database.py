import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from .config import settings

class Database:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.storage_type = settings.STORAGE_TYPE
        self.is_mongo = self.db_url.startswith("mongodb") or self.storage_type == "mongo"
        self.is_excel = self.storage_type == "excel"
        
        if self.is_mongo:
            import pymongo
            self.client = pymongo.MongoClient(self.db_url)
            self.db = self.client.get_default_database()
            self.forecasts = self.db.forecasts
        elif self.is_excel:
            # Excel Local Mode
            self.local_dir = Path(settings.LOCAL_DATA_DIR)
            self.local_dir.mkdir(parents=True, exist_ok=True)
            self.watchlist_file = self.local_dir / "watchlist.xlsx"
            self.forecasts_file = self.local_dir / "forecasts.xlsx"
            self._init_excel()
        else:
            # SQLite fallback
            if self.db_url.startswith("sqlite:///"):
                self.db_path = Path(self.db_url.replace("sqlite:///", ""))
            else:
                self.db_path = Path("data/forecasts.db")
                
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()

    def _init_excel(self):
        """Initialize Excel files if they don't exist."""
        if not self.watchlist_file.exists():
            df = pd.DataFrame(columns=["symbol", "added_at"])
            df.to_excel(self.watchlist_file, index=False)
            
        if not self.forecasts_file.exists():
            # Define columns for forecasts
            df = pd.DataFrame(columns=[
                "date", "symbol", "horizon", "prediction", 
                "start_price", "target_date", "actual", "created_at"
            ])
            df.to_excel(self.forecasts_file, index=False)



    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                symbol TEXT,
                horizon INTEGER,
                prediction REAL,
                start_price REAL,
                target_date TEXT,
                actual REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, symbol, horizon)
            )
        ''')
        # Watchlist Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_to_watchlist(self, symbol: str):
        symbol = symbol.upper()
        if self.is_mongo:
            self.db.watchlist.update_one(
                {"name": "default"},
                {"$addToSet": {"symbols": symbol}},
                upsert=True
            )
        elif self.is_excel:
            try:
                df = pd.read_excel(self.watchlist_file)
                if symbol not in df['symbol'].values:
                    new_row = {"symbol": symbol, "added_at": datetime.now()}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(self.watchlist_file, index=False)
            except Exception as e:
                print(f"Error adding to watchlist: {e}")
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO watchlist (symbol) VALUES (?)', (symbol,))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
            finally:
                conn.close()

    def remove_from_watchlist(self, symbol: str):
        symbol = symbol.upper()
        if self.is_mongo:
            self.db.watchlist.update_one(
                {"name": "default"},
                {"$pull": {"symbols": symbol}}
            )
        elif self.is_excel:
            try:
                df = pd.read_excel(self.watchlist_file)
                df = df[df['symbol'] != symbol]
                df.to_excel(self.watchlist_file, index=False)
            except Exception as e:
                print(f"Error removing from watchlist: {e}")    
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
            conn.commit()
            conn.close()

    def get_watchlist(self) -> List[str]:
        if self.is_mongo:
            doc = self.db.watchlist.find_one({"name": "default"})
            if doc and "symbols" in doc:
                return sorted(doc["symbols"])
            return []
        elif self.is_excel:
            try:
                if not self.watchlist_file.exists():
                    return []
                df = pd.read_excel(self.watchlist_file)
                if df.empty:
                    return []
                return sorted(df['symbol'].unique().tolist())
            except Exception:
                return []
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT symbol FROM watchlist ORDER BY symbol')
            rows = c.fetchall()
            conn.close()
            return [row[0] for row in rows]

    def save_forecast(self, date: str, symbol: str, horizon: int, prediction: float, start_price: float, target_date: str):
        if self.is_mongo:
            doc = {
                "date": date,
                "symbol": symbol,
                "horizon": horizon,
                "prediction": float(prediction),
                "start_price": float(start_price),
                "target_date": str(target_date),
                "actual": None,
                "created_at": datetime.now()
            }
            # Upsert
            self.forecasts.update_one(
                {"date": date, "symbol": symbol, "horizon": horizon},
                {"$set": doc},
                upsert=True
            )
        elif self.is_excel:
            try:
                df = pd.read_excel(self.forecasts_file)
                # Check for duplicate
                mask = (
                    (df['date'] == date) & 
                    (df['symbol'] == symbol) & 
                    (df['horizon'] == horizon)
                )
                
                new_row = {
                    "date": date,
                    "symbol": symbol,
                    "horizon": horizon,
                    "prediction": float(prediction),
                    "start_price": float(start_price),
                    "target_date": str(target_date),
                    "actual": None,
                    "created_at": datetime.now()
                }
                
                if mask.any():
                    # Update existing
                    for col, val in new_row.items():
                        df.loc[mask, col] = val
                else:
                    # Append new
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                df.to_excel(self.forecasts_file, index=False)
            except Exception as e:
                print(f"Error saving forecast: {e}")
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO forecasts (date, symbol, horizon, prediction, start_price, target_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date, symbol, horizon, float(prediction), float(start_price), str(target_date)))
                conn.commit()
            except sqlite3.IntegrityError:
                pass # Already exists
            finally:
                conn.close()

    def update_actuals(self, symbol: str, current_date: str, current_price: float):
        """
        Update 'actual' values for past forecasts where target_date <= current_date.
        Actual Return = log(Current Price / Start Price)
        """
        if self.is_mongo:
            # Find forecasts where target_date <= current_date and actual is None
            # Note: String comparison for dates works if format is YYYY-MM-DD
            cursor = self.forecasts.find({
                "symbol": symbol,
                "target_date": {"$lte": current_date},
                "actual": None
            })
            
            for doc in cursor:
                start_price = doc.get("start_price")
                if start_price and start_price > 0:
                    actual_log_return = np.log(current_price / start_price)
                    self.forecasts.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"actual": float(actual_log_return)}}
                    )
        elif self.is_excel:
            try:
                df = pd.read_excel(self.forecasts_file)
                # Ensure date columns are strings for comparison
                df['target_date'] = df['target_date'].astype(str)
                
                # Find rows to update: target_date <= current_date AND actual is NaN/None
                mask = (df['target_date'] <= current_date) & (df['actual'].isna()) & (df['symbol'] == symbol)
                
                if mask.any():
                    rows_to_update = df[mask]
                    for idx, row in rows_to_update.iterrows():
                        start_price = row['start_price']
                        if start_price and start_price > 0:
                            actual_log_return = np.log(current_price / start_price)
                            df.at[idx, 'actual'] = actual_log_return
                    
                    df.to_excel(self.forecasts_file, index=False)
            except Exception as e:
                print(f"Error updating actuals: {e}")
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                SELECT id, start_price FROM forecasts 
                WHERE symbol = ? AND target_date <= ? AND actual IS NULL
            ''', (symbol, current_date))
            
            rows = c.fetchall()
            for row in rows:
                fid, start_price = row
                if start_price and start_price > 0:
                    actual_log_return = np.log(current_price / start_price)
                    c.execute('UPDATE forecasts SET actual = ? WHERE id = ?', (actual_log_return, fid))
            
            conn.commit()
            conn.close()

    def get_history(self, symbol: str) -> List[Dict]:
        if self.is_mongo:
            cursor = self.forecasts.find({"symbol": symbol}).sort("date", -1)
            # Convert ObjectId to str if needed, or just return dicts
            results = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            return results
        elif self.is_excel:
            try:
                df = pd.read_excel(self.forecasts_file)
                df = df[df['symbol'] == symbol]
                df = df.sort_values('date', ascending=False)
                # Replace Inf/NaN with None for JSON serialization
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
                return df.to_dict('records')
            except Exception:
                return []
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''
                SELECT * FROM forecasts 
                WHERE symbol = ? 
                ORDER BY date DESC
            ''', (symbol,))
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def get_indices_history(self, symbols: List[str]) -> List[Dict]:
        if self.is_mongo:
            cursor = self.forecasts.find({"symbol": {"$in": symbols}}).sort([("date", -1), ("symbol", 1)])
            results = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            return results
        elif self.is_excel:
            try:
                df = pd.read_excel(self.forecasts_file)
                df = df[df['symbol'].isin(symbols)]
                df = df.sort_values(['date', 'symbol'], ascending=[False, True])
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
                return df.to_dict('records')
            except Exception:
                return []
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            placeholders = ','.join(['?'] * len(symbols))
            c.execute(f'''
                SELECT * FROM forecasts 
                WHERE symbol IN ({placeholders})
                ORDER BY date DESC, symbol ASC
            ''', symbols)
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]

# =============================================================================
# Helper Functions (module-level exports)
# =============================================================================

# Singleton instance
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

def add_to_watchlist(symbol: str):
    return get_db().add_to_watchlist(symbol)

def remove_from_watchlist(symbol: str):
    return get_db().remove_from_watchlist(symbol)

def get_watchlist():
    return get_db().get_watchlist()

def get_market_overview_logic(symbols: list) -> dict:
    """
    Optimized market overview using yfinance batch download.
    Returns current price, daily change, and basic info for each symbol.
    """
    import yfinance as yf
    from datetime import datetime, timedelta
    
    if not symbols:
        return {"overview": []}
    
    overview = []
    
    try:
        # Use batch download for efficiency (much faster than individual calls)
        print(f"[MARKET OVERVIEW] Fetching {len(symbols)} symbols in batch...")
        
        # Get 5 days of data to ensure we have enough for change calculation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Batch download
        data = yf.download(
            tickers=symbols,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            group_by='ticker',
            progress=False,
            threads=True,
            auto_adjust=True
        )
        
        for symbol in symbols:
            try:
                # Handle single vs multi-ticker response format
                if len(symbols) == 1:
                    symbol_data = data
                else:
                    symbol_data = data[symbol] if symbol in data.columns.get_level_values(0) else None
                
                if symbol_data is None or symbol_data.empty:
                    continue
                
                # Get latest price
                close_prices = symbol_data['Close'].dropna()
                if len(close_prices) < 2:
                    continue
                    
                current_price = float(close_prices.iloc[-1])
                prev_price = float(close_prices.iloc[-2])
                
                change = current_price - prev_price
                change_pct = (change / prev_price) * 100 if prev_price else 0
                
                overview.append({
                    "symbol": symbol,
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "signal": "bullish" if change_pct > 0.5 else "bearish" if change_pct < -0.5 else "neutral"
                })
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        print(f"[MARKET OVERVIEW] Successfully fetched {len(overview)} symbols")
        
    except Exception as e:
        print(f"[MARKET OVERVIEW] Batch download error: {e}")
        return {"overview": [], "error": str(e)}
    
    return {"overview": overview}

