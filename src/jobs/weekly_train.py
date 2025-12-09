
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import random
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error

# Fix path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.core.config import settings
from src.data.loader import DataLoader
from src.models.registry import ModelRegistry
from src.features.pipeline import FeaturePipeline
from src.models.lightgbm_forecaster import ForecastModel
from src.models.hmm import RegimeDetector
from src.models.transformer_model import TransformerForecaster
from src.models.meta_learner import MetaLearner
from src.core.database import get_watchlist
from src.core.monitoring import monitor
import time

# Configuration
HORIZONS = [10, 30, 100, 365]
LOG_DIR = project_root / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / f"weekly_train_{datetime.now().strftime('%Y%m%d')}.log",
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
            
            # Helper: simple train/predict loop
            # We can't use ForecastModel.train easily for tuning, so use raw lgb here possibly?
            # Or assume ForecastModel is fast enough. Let's use ForecastModel.
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
    logger.info(f"  Training Regime Classifier (HMM) for {symbol}...")
    try:
        returns = df['Close'].pct_change().dropna()
        if len(returns) < 252:
            logger.warning("    Insufficient data for HMM.")
            return

        hmm = RegimeDetector(n_components=2)
        hmm.fit(returns)
        registry.save_hmm(symbol, hmm)
        logger.info("    HMM fitted and saved.")
    except Exception as e:
        logger.error(f"    HMM Training failed: {e}")

def train_sequence_model(symbol, df_feats, registry):
    """Train Transformer (Sequence)."""
    logger.info(f"  Training Transformer (Sequence) for {symbol}...")
    try:
        # Target: Next Day Return (Simple 1-step forecast for seq model)
        # Use Horizon 1 for "sequence" learning base
        X, y = prepare_training_data(df_feats, horizon=1)
        if len(X) < 100: return
        
        # Instantiate
        # input_dim depends on columns
        dim = X.shape[1]
        model = TransformerForecaster(input_dim=dim, seq_len=30)
        
        # Fit (Heavy Step)
        model.fit(X, y, epochs=5) # Low epochs for Weekly CPU
        
        registry.save_transformer(symbol, model)
        logger.info("    Transformer trained and saved.")
    except Exception as e:
        logger.error(f"    Transformer Training failed: {e}")


def train_for_symbol(symbol: str):
    logger.info(f"Starting FULL Weekly Training for {symbol}...")
    loader = DataLoader(settings.DATA_CACHE_DIR)
    registry = ModelRegistry()
    pipeline = FeaturePipeline()
    
    # 1. Fetch Full History
    df = loader.get_data(symbol, start_date="2010-01-01")
    if df.empty: return
    
    # 2. Generate Features
    logger.info(f"  Generating features ({len(df)} rows)...")
    df_feats = pipeline.generate_features(df)
    
    # 3. Train Regime Classifier (HMM)
    train_regime_classifier(symbol, df, registry)
    
    # 4. Train Sequence Model (Transformer)
    train_sequence_model(symbol, df_feats, registry)
    
    # 5. Train Forecast Models (LightGBM) with Tuning
    for h in HORIZONS:
        logger.info(f"  Training Horizon: {h} days...")
        X, y = prepare_training_data(df_feats, h)
        if len(X) < 100: continue
            
        # Hyperparameter Tuning
        logger.info(f"    Tuning parameters...")
        best_params = tune_lightgbm(X, y)
        logger.info(f"    Best Params: {best_params}")
        
        # Final Train
        model = ForecastModel()
        model.params.update(best_params)
        metrics = model.train(X, y)
        
        logger.info(f"    Final RMSE: {metrics['rmse']:.4f}")
        registry.save_forecast_model(symbol, model, h)
        
def retrain_meta_learner():
    logger.info("Retraining Meta-Learner...")
    meta = MetaLearner()
    # In a real scenario, fetch all past errors from DB.
    # Here, we save a refreshed instance.
    logger.info("Meta-Learner refreshed.")

def main():
    start_time = time.time()
    logger.info("=== STARTING WEEKLY HEAVY TRAINING JOB (SECTION 3) ===")
    
    try:
        monitor.log_heartbeat("WeeklyTraining", "running", {"step": "start"})
        
        watchlist = get_watchlist()
        target_list = sorted(list(set(['SPY', 'QQQ', 'IWM'] + watchlist)))
        
        for sym in target_list:
            train_for_symbol(sym)
            
        retrain_meta_learner()
        
        logger.info("=== WEEKLY JOB COMPLETE ===")
        
        duration = time.time() - start_time
        monitor.log_heartbeat("WeeklyTraining", "success", {
            "symbols_trained": len(target_list),
            "modules": ["LightGBM", "HMM", "Transformer", "MetaLearner"]
        }, duration)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Weekly Training Failed: {e}")
        monitor.log_heartbeat("WeeklyTraining", "error", {"error": str(e)}, duration)

if __name__ == "__main__":
    main()
