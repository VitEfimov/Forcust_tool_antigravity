
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import random

# Fix path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.core.config import settings
from src.data.loader import DataLoader
from src.core.database import get_db, get_watchlist
from src.core.monitoring import monitor
import time

# Metrics for confidence proxy
def calculate_confidence(rmse, std_dev):
    """
    Crude confidence metric based on RMSE vs Target Volatility.
    If RMSE is low relative to volatility, confidence is high.
    Range 0.0 to 1.0
    """
    if std_dev == 0: return 0.5
    ratio = rmse / std_dev
    # Heuristic: if error is > 100% of sigma, confidence is 0.
    conf = max(0.0, 1.0 - ratio)
    return conf

# Configuration
DEEP_HORIZONS = [30, 180, 365] # Task 6 Requirement
LOG_DIR = project_root / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / f"deep_train_{datetime.now().strftime('%Y%m%d')}.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()
console = logging.StreamHandler()
logger.addHandler(console)

def prepare_training_data(df, horizon):
    """Align features and target for a specific horizon."""
    data = df.copy()
    data['Target'] = np.log(data['Close'].shift(-horizon) / data['Close'])
    data = data.dropna()
    
    if data.empty:
        return pd.DataFrame(), pd.Series()
        
    y = data['Target']
    X = data.drop(columns=['Target', 'Close', 'Open', 'High', 'Low', 'Volume', 'Dividends', 'Stock Splits'], errors='ignore')
    X = X.select_dtypes(include=[np.number])
    return X, y

def tune_lightgbm(X, y):
    """Randomized Search for LightGBM parameters."""
    from sklearn.model_selection import TimeSeriesSplit
    from src.models.lightgbm_forecaster import ForecastModel
    
    param_grid = {
        'num_leaves': [20, 31, 50, 70],
        'learning_rate': [0.01, 0.05, 0.1],
        'feature_fraction': [0.8, 0.9, 1.0],
        'bagging_fraction': [0.8, 0.9, 1.0]
    }
    
    best_score = float('inf')
    best_params = {}
    
    # Random Search Budget: 5 iter
    keys = list(param_grid.keys())
    
    # TimeSeries CV
    tscv = TimeSeriesSplit(n_splits=3)
    
    for _ in range(5):
        current_params = {k: random.choice(param_grid[k]) for k in keys}
        current_params['objective'] = 'regression'
        current_params['metric'] = 'rmse'
        current_params['verbose'] = -1
        
        scores = []
        for train_index, val_index in tscv.split(X):
            X_train, X_val = X.iloc[train_index], X.iloc[val_index]
            y_train, y_val = y.iloc[train_index], y.iloc[val_index]
            
            model = ForecastModel()
            model.params.update(current_params)
            metrics = model.train(X_train, y_train)
            scores.append(metrics['rmse'])
            
        avg_score = np.mean(scores)
        if avg_score < best_score:
            best_score = avg_score
            best_params = current_params
            
    return best_params

def train_regime_classifier(symbol, df, registry):
    """Train HMM Regime Classifier."""
    from src.models.hmm import RegimeDetector
    logger.info(f"  Training Regime Classifier (HMM) for {symbol}...")
    try:
        returns = df['Close'].pct_change().dropna()
        if len(returns) < 252:
            logger.warning("    Insufficient data for HMM.")
            return None

        hmm = RegimeDetector(n_components=2)
        hmm.fit(returns)
        registry.save_hmm(symbol, hmm)
        
        # Return current regime for forecast context
        regime_idx = int(hmm.predict(returns)[-1])
        regime_label = hmm.get_regime_label(regime_idx)
        return regime_label
    except Exception as e:
        logger.error(f"    HMM Training failed: {e}")
        return "Unknown"

def train_sequence_model(symbol, df_feats, registry):
    """Train Transformer (Sequence)."""
    from src.models.transformer_model import TransformerForecaster
    logger.info(f"  Training Transformer (Sequence) for {symbol}...")
    try:
        # Target: Next Day Return (Simple 1-step forecast for seq model)
        X, y = prepare_training_data(df_feats, horizon=1)
        if len(X) < 100: return
        
        dim = X.shape[1]
        model = TransformerForecaster(input_dim=dim, seq_len=30)
        
        # Fit (Heavy Step)
        model.fit(X, y, epochs=5) # Low epochs for Weekly CPU
        
        registry.save_transformer(symbol, model)
        logger.info("    Transformer trained and saved.")
    except Exception as e:
        logger.error(f"    Transformer Training failed: {e}")

def run_deep_training_logic(run_id=None):
    """
    Main Logic for Deep Training (callable from API or CLI).
    """
    start_time = time.time()
    source = "manual" if run_id else "scheduled" 
    logger.info("=== STARTING DEEP TRAINING JOB (Tasks: 30d, 180d, 365d) ===")
    
    db = get_db()
    
    # Create Run if not provided (CLI)
    if not run_id:
        run_id = db.start_training_run("deep", "scheduled_script")

    try:
        monitor.log_heartbeat("DeepTraining", "running", {"step": "start", "source": source})
        
        from src.models.registry import ModelRegistry
        from src.features.pipeline import FeaturePipeline
        from src.models.lightgbm_forecaster import ForecastModel
        
        loader = DataLoader(settings.DATA_CACHE_DIR)
        registry = ModelRegistry()
        pipeline = FeaturePipeline()
        
        # Target Selection: Focused mainly on T1/T2 + Watchlist
        watchlist = get_watchlist()
        candidates = set(watchlist)
        candidates.update(settings.TRAINING_TARGETS)
        candidates.update(settings.TIER_1_INDICES) 
        
        target_list = sorted(list(candidates))
        
        # External Data (Macros)
        logger.info("  Fetching Macro/Factor Data...")
        external_data = {}
        indices = settings.TIER_1_INDICES + settings.TIER_2_INDICES + ['^MEGACAP']
        for idx in indices:
            try:
                d = loader.get_data(idx)
                if not d.empty:
                    external_data[idx] = d
            except: pass

        # Initialize Forecast Map for Snapshot
        forecast_map = {}

        for symbol in target_list:
            logger.info(f"Processing {symbol}...")
            
            # 1. Fetch Data
            df = loader.get_data(symbol, start_date="2010-01-01")
            
            # --- START SNAPSHOT PRE-CALC ---
            if symbol not in forecast_map: forecast_map[symbol] = {}
            # --- END SNAPSHOT PRE-CALC ---

            if df.empty: continue

            
            current_price = df['Close'].iloc[-1]
            
            # 2. Train Shared Models (HMM, Transformer)
            # Only need to train these once per symbol (structure learning)
            regime = train_regime_classifier(symbol, df, registry)
            
            try:
                # Prepare features once
                df_feats = pipeline.prepare_features(df, external_data=None)
                train_sequence_model(symbol, df_feats, registry)
            except: pass
            
            # 3. Train & Forecast per Horizon (Deep Only)
            for h in DEEP_HORIZONS:
                logger.info(f"  Horizon: {h} days...")
                try:
                    X, y, feats = pipeline.get_training_data(df, external_data=external_data, horizon=h)
                    
                    if len(X) < 100: 
                        logger.warning(f"    Skipping h={h}: Insufficient data (n={len(X)} < 100). Fetch more history.")
                        continue
                        
                    # Hyperparameter Tuning
                    best_params = tune_lightgbm(X, y)
                    
                    # Final Train
                    model = ForecastModel()
                    model.params.update(best_params)
                    metrics = model.train(X, y)
                    rmse = metrics.get('rmse', 0.1)
                    
                    # Save Model
                    registry.save_forecast_model(symbol, model, h)
                    
                    # --- GENERATE FORECAST FROM NEW MODEL ---
                    X_inf = pipeline.get_inference_data(df, external_data=external_data)
                    pred_log_ret = model.predict(X_inf)[0]
                    
                    # Convert to Pct Return
                    pred_return_pct = (np.exp(pred_log_ret) - 1) * 100
                    
                    # Capture for Snapshot
                    forecast_map[symbol][h] = pred_return_pct

                    # Calculate Confidence
                    # Use std dev of target (y)
                    sigma = y.std()
                    confidence = calculate_confidence(rmse, sigma)
                    
                    # Calculate Volatility Label
                    vol_30 = df['Close'].pct_change().tail(30).std() * np.sqrt(252) * 100
                    vol_label = "Moderate"
                    if vol_30 > 30: vol_label = "High Volatility"
                    elif vol_30 < 12: vol_label = "Low Volatility"
                    
                    # Save to DB (New Table)
                    db.save_symbol_forecast(
                        run_id=run_id,
                        symbol=symbol,
                        horizon=h,
                        expected_return=pred_return_pct,
                        confidence=confidence,
                        regime=regime,
                        volatility=vol_label
                    )

                    # --- COMPATIBILITY FIX: Save to Legacy Table for API/Analytics ---
                    # Calculate target price and date
                    target_price = current_price * (1 + pred_return_pct/100)
                    # Use business days approximation or just calendar days
                    target_date = (datetime.now() + timedelta(days=h)).strftime("%Y-%m-%d")
                    
                    db.save_forecast(
                        date=datetime.now().strftime("%Y-%m-%d"),
                        symbol=symbol,
                        horizon=h,
                        prediction=target_price,
                        start_price=current_price,
                        target_date=target_date
                    )

                    logger.info(f"    Saved Forecast: {pred_return_pct:.2f}% (Conf: {confidence:.2f})")
                    
                except Exception as e:
                    logger.error(f"    Failed h={h}: {e}")
            
            # Cleanup
            import gc
            gc.collect()

        # --- NEW: Generate & Save Market Snapshot (History Entry) ---
        try:
            logger.info("Generating Analytics Snapshot...")
            full_snapshot = []
            
            # Combine all relevant symbols for snapshot
            snapshot_symbols = sorted(list(set(settings.TRAINING_TARGETS + settings.TIER_1_INDICES + settings.TIER_2_INDICES + ["^MEGACAP"])))
            
            for sym in snapshot_symbols:
                try:
                    df_sym = loader.get_data(sym)
                    if df_sym.empty: continue
                    
                    # Basic Stats
                    price = float(df_sym['Close'].iloc[-1])
                    prev = float(df_sym['Close'].iloc[-2]) if len(df_sym) > 1 else price
                    change_pct = (price - prev) / prev * 100
                    
                    # Regime/Vol
                    sma20 = df_sym['Close'].tail(20).mean()
                    regime_lbl = "Uptrend" if price > sma20 else "Downtrend"
                    
                    rets = df_sym['Close'].pct_change().tail(30).dropna()
                    vol = rets.std() * np.sqrt(252) * 100
                    risk = "Moderate"
                    if vol > 30: risk = "High Volatility"
                    elif vol < 12: risk = "Low Volatility"
                    
                    # Get Forecasts (Deep Learning or derived)
                    # If this symbol was just trained, we use the fresh map.
                    # If not, we might check DB or leave blank.
                    sym_forecasts = forecast_map.get(sym, {})
                    
                    full_snapshot.append({
                        "symbol": sym,
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                        "regime": regime_lbl,
                        "risk_label": risk,
                        "volatility_outlook": "Stable" if risk == "Low Volatility" else "Unstable",
                        "forecasts": sym_forecasts
                    })
                except: pass
                
            if full_snapshot:
                db.save_market_overview({"overview": full_snapshot})
                logger.info(f"Detailed Snapshot Saved ({len(full_snapshot)} symbols).")
            else:
                logger.warning("Snapshot generation failed (empty).")

        except Exception as e:
            logger.error(f"Failed to generate snapshot: {e}")

        logger.info("Deep Training Complete.")
        db.end_training_run(run_id, status="success")
        
        duration = time.time() - start_time
        monitor.log_heartbeat("DeepTraining", "success", {"symbols": len(target_list)}, duration)
        
    except Exception as e:
        logger.error(f"Deep Training Job Failed: {e}")
        db.end_training_run(run_id, status="failed")
        raise e

if __name__ == "__main__":
    run_deep_training_logic()
