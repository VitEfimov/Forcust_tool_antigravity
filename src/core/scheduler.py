from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from ..data.loader import DataLoader
from ..features.pipeline import FeaturePipeline
from ..models.hmm import RegimeDetector
from ..models.lightgbm_forecaster import ForecastModel
from ..models.registry import ModelRegistry
# from ..core.database import Database
from .config import settings
import pandas as pd

def update_job():
    """
    Daily update job:
    1. Fetch new data.
    2. Retrain models (or update).
    3. Log results.
    """
    print("Starting daily update job...")
    loader = DataLoader(settings.DATA_CACHE_DIR)
    pipeline = FeaturePipeline()
    registry = ModelRegistry(settings.MODELS_DIR)

    for symbol in settings.SYMBOLS:
        print(f"Updating {symbol}...")
        # 1. Fetch Data
        df = loader.get_data(symbol, use_cache=False) # Force refresh
        if df.empty:
            continue

        # 2. Prepare Data
        X, y, _ = pipeline.get_training_data(df)
        
        # 3. Train HMM
        # We use returns for HMM
        # Use Mini-cycle window
        returns = df['Close'].pct_change().dropna()
        returns_mini = returns.tail(settings.MINI_CYCLE_DAYS)
        hmm = RegimeDetector()
        hmm.fit(returns_mini)
        registry.save_hmm(symbol, hmm)

        # 4. Train GARCH (Volatility)
        from ..models.garch_volatility import GarchModel
        garch = GarchModel()
        garch.fit(returns) # Use full history or mini-cycle? GARCH benefits from history.
        registry.save_garch(symbol, garch)

        # 5. Train Transformer (Deep Learning)
        from ..models.transformer_model import TransformerForecaster
        # Use Business Cycle window for Transformer
        df_train = df.tail(settings.BUSINESS_CYCLE_DAYS)
        X, y, _ = pipeline.get_training_data(df_train, horizon=10) # Base 10d model
        if not X.empty:
            transformer = TransformerForecaster(input_dim=X.shape[1])
            transformer.fit(X, y, epochs=10) # Train a bit more in background
            registry.save_transformer(symbol, transformer)

        # 6. Train Forecast Models (LightGBM)
        horizons = [10, 100, 365, 547, 730]
        for h in horizons:
            # Use Business Cycle window
            df_train = df.tail(settings.BUSINESS_CYCLE_DAYS)
            X, y, _ = pipeline.get_training_data(df_train, horizon=h)
            if X.empty:
                continue
            lgb_model = ForecastModel()
            lgb_model.fit(X, y)
            registry.save_forecast_model(symbol, lgb_model, h)
            
        # 7. Update Actuals in DB (Analysis Step)
        current_price = df['Close'].iloc[-1]
        current_date = str(df.index[-1].date())
        # db = Database()
        # db.update_actuals(symbol, current_date, float(current_price))
        
    print("Daily update job completed.")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run every day at 6 PM
    trigger = CronTrigger(hour=18, minute=0)
    scheduler.add_job(update_job, trigger)
    scheduler.start()
    return scheduler
