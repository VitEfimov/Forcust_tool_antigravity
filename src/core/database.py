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
            try:
                self.db = self.client.get_default_database()
            except Exception:
                self.db = self.client.get_database("antigravity")
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
        # Full Market Overviews Table (Fix for 500 Error)
        c.execute('''
            CREATE TABLE IF NOT EXISTS full_market_overviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                date TEXT,
                json_data TEXT
            )
        ''')
        # Advanced Simulation Results Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS advanced_simulation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                symbol TEXT,
                mc_p10 REAL,
                mc_p50 REAL,
                mc_p90 REAL,
                conservative_mode BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # System Config Table (New)
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Walk Forward Results Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS walk_forward_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                symbol TEXT,
                prediction_price REAL,
                reliability_score REAL,
                regime_label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # --- NEW: Training System Tables ---
        c.execute('''
            CREATE TABLE IF NOT EXISTS training_runs (
                id TEXT PRIMARY KEY,
                run_type TEXT, 
                trigger_source TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS symbol_forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                symbol TEXT,
                horizon_days INTEGER,
                expected_return REAL,
                confidence REAL,
                regime TEXT,
                volatility_label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES training_runs(id)
            )
        ''')
        
        # Ensure columns exist (Migration for SQLite)
        try:
            c.execute('ALTER TABLE walk_forward_results ADD COLUMN mode TEXT')
        except: pass
        try:
            c.execute('ALTER TABLE walk_forward_results ADD COLUMN trained BOOLEAN')
        except: pass
        try:
            c.execute('ALTER TABLE walk_forward_results ADD COLUMN derived_from INTEGER')
        except: pass
        
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

    def save_market_summary(self, summary: Dict):
        """
        Save a compact daily market summary.
        summary: dict with keys [date, regime, vix, credit_spread, model_confidence, forecast_spy]
        """
        date = summary.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        if self.is_mongo:
            # Upsert based on date
            self.db.market_summaries.update_one(
                {"date": date},
                {"$set": summary},
                upsert=True
            )
        elif self.is_excel:
            try:
                summary_file = self.local_dir / "market_summaries.xlsx"
                if summary_file.exists():
                    df = pd.read_excel(summary_file)
                else:
                    df = pd.DataFrame()
                
                # Convert summary to flat dict (handle nested dicts like forecast_spy)
                flat_summary = summary.copy()
                if "forecast_spy" in flat_summary and isinstance(flat_summary["forecast_spy"], dict):
                    flat_summary["spy_pred"] = flat_summary["forecast_spy"].get("pred")
                    flat_summary["spy_upside"] = flat_summary["forecast_spy"].get("upside")
                    del flat_summary["forecast_spy"]
                    
                new_row = pd.DataFrame([flat_summary])
                
                if not df.empty and "date" in df.columns:
                    # Update if exists
                    if date in df["date"].values:
                        idx = df[df["date"] == date].index
                        for col, val in flat_summary.items():
                            df.loc[idx, col] = val
                    else:
                        df = pd.concat([df, new_row], ignore_index=True)
                else:
                     df = new_row
                     
                df.to_excel(summary_file, index=False)
            except Exception as e:
                print(f"Error saving excel summary: {e}")
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Ensure table exists
            c.execute('''
                CREATE TABLE IF NOT EXISTS market_summaries (
                    date TEXT PRIMARY KEY,
                    regime TEXT,
                    vix REAL,
                    credit_spread REAL,
                    model_confidence REAL,
                    spy_pred REAL,
                    json_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Prepare data
            import json
            spy_pred = 0.0
            if "forecast_spy" in summary and isinstance(summary["forecast_spy"], dict):
                spy_pred = summary["forecast_spy"].get("pred", 0.0)
            
            c.execute('''
                INSERT OR REPLACE INTO market_summaries (date, regime, vix, credit_spread, model_confidence, spy_pred, json_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                summary.get("regime"),
                float(summary.get("vix", 0.0)),
                float(summary.get("credit_spread", 0.0)),
                float(summary.get("model_confidence", 0.0)),
                float(spy_pred),
                json.dumps(summary)
            ))
            conn.close()

    def save_market_overview(self, overview_data: Dict):
        """
        Save the full Market Overview JSON to the database.
        """
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d")
        
        doc = {
            "timestamp": timestamp,
            "date": date_str,
            "type": "market_overview",
            "data": overview_data
        }
        
        if self.is_mongo:
            # We can use a Time Series collection or just a standard one.
            # Standard 'market_overviews' collection.
            self.db.market_overviews.insert_one(doc)
            
        elif self.is_excel:
            # For Excel, saving the full JSON structure is messy.
            # We might save just the latest one to a separate file, or try to flatten it?
            # User specifically asked for DB, so file-based fallback is secondary.
            # We'll stick to the existing behavior of scheduler saving to disk for file-based.
            # But here we can maybe append to a log or skip.
            pass
            
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS full_market_overviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    date TEXT,
                    json_data TEXT
                )
            ''')
            import json
            c.execute('''
                INSERT INTO full_market_overviews (timestamp, date, json_data)
                VALUES (?, ?, ?)
            ''', (timestamp, date_str, json.dumps(overview_data)))
            conn.commit()
            conn.close()

    def get_market_overview_history(self, limit: int = 5) -> List[Dict]:
        """
        Get historical market overviews.
        """
        if self.is_mongo:
            cursor = self.db.market_overviews.find().sort("timestamp", -1).limit(limit)
            results = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            return results
        elif self.is_excel:
             # Not supported in Excel mode currently
            return []
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT * FROM full_market_overviews 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                rows = c.fetchall()
                
                results = []
                import json
                for row in rows:
                    d = dict(row)
                    if d.get("json_data"):
                        d["data"] = json.loads(d["json_data"])
                        # Clean up raw json string from response if needed, but keeping it is fine.
                        # Actually standardizing to match Mongo structure:
                        # Mongo: {timestamp, date, type, data: {...}}
                        # Sqlite: {timestamp, date, json_data} -> convert to {timestamp, date, data}
                    results.append(d)
                return results
            except sqlite3.OperationalError:
                # Table might not exist yet if save_market_overview hasn't run
                return []
            except Exception:
                return []
            finally:
                 conn.close()

    
    def save_advanced_simulation_result(self, result):
        """
        Save AdvancedSimulationResult pydantic model.
        """
        data = result.model_dump() # Pydantic v2
        
        if self.is_mongo:
            self.db.advanced_simulation_results.insert_one(data)
        elif self.is_excel:
            # Skip for excel to keep it simple or implement append
            pass
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO advanced_simulation_results (date, symbol, mc_p10, mc_p50, mc_p90, conservative_mode)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['date'], data['symbol'], 
                data['mc_p10'], data['mc_p50'], data['mc_p90'], 
                data['conservative_mode']
            ))
            conn.commit()
            conn.close()
            
    def save_walk_forward_result(self, result):
        """
        Save WalkForwardResult pydantic model.
        """
        data = result.model_dump()
        
        if self.is_mongo:
            self.db.walk_forward_results.insert_one(data)
        elif self.is_excel:
            pass
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Ensure columns exist (Migration for SQLite)
            try:
                c.execute('ALTER TABLE walk_forward_results ADD COLUMN mode TEXT')
            except: pass
            try:
                c.execute('ALTER TABLE walk_forward_results ADD COLUMN trained BOOLEAN')
            except: pass
            try:
                c.execute('ALTER TABLE walk_forward_results ADD COLUMN derived_from INTEGER')
            except: pass
            
            c.execute('''
                INSERT INTO walk_forward_results (date, symbol, prediction_price, reliability_score, regime_label, mode, trained, derived_from)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['date'], data['symbol'], 
                data['prediction_price'], data['reliability_score'], data['regime_label'],
                data.get('mode'), data.get('trained'), data.get('derived_from')
            ))
            conn.commit()
            conn.close()

    def get_latest_walk_forward_result(self, symbol: str, horizon: int = 10):
        """
        Get the most recent trained result for a symbol to reuse metadata (e.g. Regime).
        """
        if self.is_mongo:
            # Sort by date desc
            return self.db.walk_forward_results.find_one(
                {"symbol": symbol},
                sort=[("date", -1)]
            )
        elif self.is_excel:
            return None
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # We filter by symbol. Ideally valid/recent.
            c.execute('''
                SELECT * FROM walk_forward_results 
                WHERE symbol = ? 
                ORDER BY date DESC LIMIT 1
            ''', (symbol,))
            row = c.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None

    def get_config(self, key: str) -> Optional[str]:
        """Get system config value."""
        if self.is_mongo:
            doc = self.db.system_config.find_one({"_id": key})
            return doc["value"] if doc else None
        elif self.is_excel:
            return None # Not implemented for Excel
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT value FROM system_config WHERE key = ?', (key,))
            row = c.fetchone()
            conn.close()
            return row[0] if row else None

    def set_config(self, key: str, value: str):
        """Set system config value."""
        if self.is_mongo:
            self.db.system_config.update_one(
                {"_id": key},
                {"$set": {"value": str(value), "updated_at": datetime.now()}},
                upsert=True
            )
        elif self.is_excel:
            pass
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)', (key, str(value)))
            conn.commit()
            conn.close()

    def start_training_run(self, run_type: str, source: str) -> str:
        """Start a new training run and return its ID."""
        import uuid
        run_id = str(uuid.uuid4())
        started_at = datetime.now()
        
        if self.is_mongo:
            self.db.training_runs.insert_one({
                "_id": run_id,
                "run_type": run_type,
                "trigger_source": source,
                "started_at": started_at,
                "status": "running"
            })
        elif self.is_excel:
            pass # Skip for excel
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO training_runs (id, run_type, trigger_source, started_at, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (run_id, run_type, source, started_at, "running"))
            conn.commit()
            conn.close()
        return run_id

    def end_training_run(self, run_id: str, status: str = "success"):
        """Mark a training run as completed."""
        completed_at = datetime.now()
        
        if self.is_mongo:
            self.db.training_runs.update_one(
                {"_id": run_id},
                {"$set": {"completed_at": completed_at, "status": status}}
            )
        elif self.is_excel:
            pass
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                UPDATE training_runs 
                SET completed_at = ?, status = ?
                WHERE id = ?
            ''', (completed_at, status, run_id))
            conn.commit()
            conn.close()

    def save_symbol_forecast(self, run_id: str, symbol: str, horizon: int, expected_return: float, 
                           confidence: float, regime: str, volatility: str):
        """Save a single forecast linked to a run."""
        
        doc = {
            "run_id": run_id,
            "symbol": symbol,
            "horizon_days": horizon,
            "expected_return": expected_return,
            "confidence": confidence,
            "regime": regime,
            "volatility_label": volatility,
            "created_at": datetime.now()
        }
        
        if self.is_mongo:
             self.db.symbol_forecasts.insert_one(doc)
        elif self.is_excel:
             pass
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO symbol_forecasts 
                (run_id, symbol, horizon_days, expected_return, confidence, regime, volatility_label, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (run_id, symbol, horizon, expected_return, confidence, regime, volatility, datetime.now()))
            conn.commit()
            conn.close()

    def get_latest_forecasts(self, symbol: str) -> Dict[int, Dict]:
        """
        Get the most recent forecast for EACH horizon for a given symbol.
        Returns: {10: {return: 0.05, conf: 0.8}, 30: {...}}
        """
        if self.is_mongo:
            # Aggregation pipeline to get latest by horizon
            pipeline = [
                {"$match": {"symbol": symbol}},
                {"$sort": {"created_at": -1}},
                {"$group": {
                    "_id": "$horizon_days",
                    "doc": {"$first": "$$ROOT"}
                }}
            ]
            results = self.db.symbol_forecasts.aggregate(pipeline)
            final = {}
            for res in results:
                h = res["_id"]
                doc = res["doc"]
                final[h] = {
                    "expected_return": doc["expected_return"],
                    "confidence": doc["confidence"],
                    "regime": doc["regime"],
                    "volatility": doc["volatility_label"]
                }
            return final
            
        elif self.is_excel:
            return {}
        else:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Window function to get latest per horizon
            # SQLite 3.25+ supports window functions. 
            # If primitive sqlite, we might need a different query.
            # Fallback: SELECT * FROM symbol_forecasts WHERE symbol=? ORDER BY created_at DESC 
            # and filter in python. Safer for older sqlite.
            
            c.execute('''
                SELECT horizon_days, expected_return, confidence, regime, volatility_label 
                FROM symbol_forecasts 
                WHERE symbol = ? 
                ORDER BY created_at DESC
            ''', (symbol,))
            
            rows = c.fetchall()
            conn.close()
            
            final = {}
            for row in rows:
                h, ret, conf, reg, vol = row
                if h not in final: # First one seen is latest because of ORDER BY DESC
                    final[h] = {
                        "expected_return": ret,
                        "confidence": conf,
                        "regime": reg,
                        "volatility": vol
                    }
            return final

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
    import os
    
    # 1. Fix Cache Issue
    try:
        yf.set_tz_cache_location("/tmp/yf_cache")
    except:
        pass 

    from datetime import datetime
    
    if not symbols:
        return {"overview": []}
    
    overview = []
    
    try:
        # Optimized: Single Threaded for Low Memory
        print(f"[MARKET OVERVIEW] Fetching {len(symbols)} symbols in batch (Low Memory Mode)...")
        
        data = yf.download(
            symbols, 
            period="5d", 
            group_by='ticker', 
            threads=False,   
            progress=False
        )
        
        for symbol in symbols:
            try:
                if len(symbols) == 1:
                    df = data
                else:
                    df = data[symbol] if symbol in data.columns.get_level_values(0) else None
                
                if df is None or df.empty:
                    continue
                    
                # Safe access
                close = df['Close'].dropna()
                if len(close) < 1: continue

                last_price = float(close.iloc[-1])
                prev_price = float(close.iloc[-2]) if len(close) > 1 else last_price
                change_pct = ((last_price - prev_price) / prev_price) * 100 if prev_price else 0
                
                overview.append({
                    "symbol": symbol,
                    "price": round(last_price, 2),
                    "change_pct": round(change_pct, 2),
                    "signal": "bullish" if change_pct > 0.5 else "bearish" if change_pct < -0.5 else "neutral"
                })
            except Exception as e:
                continue
        
        print(f"[MARKET OVERVIEW] Successfully fetched {len(overview)} symbols")
        
    except Exception as e:
        print(f"[MARKET OVERVIEW] Batch download error: {e}")
        return {"overview": [], "error": str(e)}
    
    return {"overview": overview}
