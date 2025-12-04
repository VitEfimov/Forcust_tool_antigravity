import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = "data/forecasts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Forecasts table
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
        # Check if start_price exists (migration for existing db)
        try:
            c.execute("SELECT start_price FROM forecasts LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE forecasts ADD COLUMN start_price REAL")
            
        conn.commit()
        conn.close()

    def save_forecast(self, date: str, symbol: str, horizon: int, prediction: float, start_price: float, target_date: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO forecasts (date, symbol, horizon, prediction, start_price, target_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, symbol, horizon, prediction, start_price, target_date))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def update_actuals(self, symbol: str, current_date: str, current_price: float):
        """
        Update 'actual' values for past forecasts where target_date <= current_date.
        Actual Return = log(Current Price / Start Price)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Find forecasts that have reached their target date and don't have an actual yet
        # Note: In a real system, we'd need the price EXACTLY at target_date. 
        # Here we are approximating by updating when we see a price AFTER target_date?
        # Or we assume this runs daily and we check for target_date == current_date.
        
        # Let's just update any where target_date <= current_date and actual IS NULL
        # But we need the price at target_date, not necessarily current_price if target_date was yesterday.
        # For this simplified version, we'll assume we are updating ON the target date.
        
        import numpy as np
        
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

    def update_actuals(self, symbol: str, current_date: str, current_price: float):
        """
        Update 'actual' values for past forecasts where target_date <= current_date.
        We need the price at the time of prediction to calculate the actual return.
        Since we don't store the start price, we can't perfectly calculate return 
        UNLESS we look up the historical price for 'date' again.
        
        For this implementation, we will assume we can look up the start price 
        if we have the data loader, OR we can just update the schema to store start_price.
        Let's update the schema to store start_price for easier calculation.
        """
        pass # Schema update required first
