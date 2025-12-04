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
        self.is_mongo = self.db_url.startswith("mongodb")
        
        if self.is_mongo:
            import pymongo
            self.client = pymongo.MongoClient(self.db_url)
            self.db = self.client.get_default_database()
            self.forecasts = self.db.forecasts
        else:
            # SQLite fallback
            # Extract path from sqlite:///path/to/db or use default
            if self.db_url.startswith("sqlite:///"):
                self.db_path = Path(self.db_url.replace("sqlite:///", ""))
            else:
                self.db_path = Path("data/forecasts.db")
                
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()

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
        conn.commit()
        conn.close()

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
