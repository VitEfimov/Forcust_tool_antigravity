from fastapi import APIRouter, HTTPException
from ..data.loader import DataLoader
from ..features.pipeline import FeaturePipeline
from ..models.registry import ModelRegistry
from ..models.lightgbm_forecaster import ForecastModel
from ..models.monte_carlo import Simulator
from ..models.hmm import RegimeDetector
from ..models.garch_volatility import GarchModel
from ..models.kalman_filter import KalmanTrend
from ..models.transformer_model import TransformerForecaster
from ..models.ensemble import EnsembleModel
from ..core.config import settings
from ..core.database import Database
import numpy as np
import pandas as pd

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "version": settings.VERSION}

@router.get("/forecast/{symbol}")
def get_forecast(symbol: str):
    """
    Get forecast for a symbol using Ensemble Model.
    """
    loader = DataLoader(settings.DATA_CACHE_DIR)
    pipeline = FeaturePipeline()
    registry = ModelRegistry(settings.MODELS_DIR)
    db = Database()
    ensemble = EnsembleModel()

    try:
        # Load Data
        df = loader.get_data(symbol)
        if df.empty:
            raise HTTPException(status_code=404, detail="Symbol not found")

        # 1. Regime (HMM)
        returns = df['Close'].pct_change().dropna()
        hmm = registry.load_hmm(symbol)
        if not hmm:
            print(f"Training HMM for {symbol}...")
            returns_train = df['Close'].pct_change().dropna().tail(settings.MINI_CYCLE_DAYS)
            hmm = RegimeDetector()
            hmm.fit(returns_train)
            registry.save_hmm(symbol, hmm)

        regime_probs = hmm.predict_proba(returns)[-1]
        current_regime = int(np.argmax(regime_probs))

        # 2. Volatility (GARCH)
        garch = registry.load_garch(symbol)
        if not garch:
            print(f"GARCH model for {symbol} not found. Scheduling training...")
            # Do NOT train on the fly. It blocks.
            # We will use a fallback volatility (historical std dev)
            volatility_fallback = returns.std() * np.sqrt(252)
        else:
            volatility_fallback = None
        
        # 3. Trend (Kalman)
        # Run on fly as it's fast (keep this)
        kalman = KalmanTrend()
        kalman.fit_transform(df['Close'].tail(252)) 
        trend_state = kalman.get_current_state()
        trend_slope = trend_state['trend_slope']

        # 4. Deep Learning (Transformer)
        transformer = registry.load_transformer(symbol)
        if not transformer:
            print(f"Transformer model for {symbol} not found. Scheduling training...")
            # Do NOT train on the fly. It blocks.
            pass

        # 5. Forecasts for multiple horizons
        horizons = [10, 100, 365, 547, 730]
        forecasts = {}
        
        current_price = df['Close'].iloc[-1]
        current_date = str(df.index[-1].date())

        for h in horizons:
            # LightGBM
            lgb_model = registry.load_forecast_model(symbol, h)
            if not lgb_model:
                print(f"Training LightGBM for {symbol} horizon {h}...")
                df_train = df.tail(settings.BUSINESS_CYCLE_DAYS)
                X, y, _ = pipeline.get_training_data(df_train, horizon=h)
                if X.empty:
                    forecasts[f"{h}d"] = None
                    continue
                lgb_model = ForecastModel()
                lgb_model.fit(X, y)
                registry.save_forecast_model(symbol, lgb_model, h)

            # Inference Data
            X_inference = pipeline.get_inference_data(df)
            
            # Predictions
            lgb_pred = lgb_model.predict(X_inference)[0]
            
            # Transformer Prediction
            if h == 10 and transformer:
                trans_pred = transformer.predict(X_inference)
            else:
                trans_pred = lgb_pred # Fallback to LGBM if no specific transformer
            
            # Volatility Forecast
            if garch:
                vol_pred = garch.predict(horizon=h)
            else:
                # Fallback to historical volatility
                vol_pred = volatility_fallback if volatility_fallback else 0.2
            
            # Ensemble
            final_log_return = ensemble.predict(
                lgbm_pred=lgb_pred,
                transformer_pred=trans_pred,
                current_regime=current_regime,
                trend_slope=trend_slope,
                volatility=vol_pred
            )
            
            predicted_return_pct = (np.exp(final_log_return) - 1) * 100
            target_date = (df.index[-1] + pd.Timedelta(days=h)).date()
            
            forecasts[f"{h}d"] = {
                "log_return": float(final_log_return),
                "expected_return_pct": float(predicted_return_pct),
                "target_price": float(current_price * np.exp(final_log_return)),
                "target_date": str(target_date),
                "components": {
                    "lgbm": float(lgb_pred),
                    "transformer": float(trans_pred),
                    "volatility": float(vol_pred),
                    "trend_slope": float(trend_slope)
                }
            }
            
            # Save to DB
            db.save_forecast(current_date, symbol, h, float(final_log_return), float(current_price), str(target_date))

        # 6. Simulation (using 10d forecast for now)
        volatility = returns.std()
        sim_return = forecasts.get("10d", {}).get("log_return", 0.0)
        sim = Simulator(n_sims=500, horizon=10)
        sim_result = sim.simulate(current_price, sim_return, volatility)

        return {
            "symbol": symbol,
            "date": current_date,
            "current_price": float(current_price),
            "regime": {
                "current": current_regime,
                "probs": regime_probs.tolist()
            },
            "forecasts": forecasts,
            "simulation": sim_result['quantiles']
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/archive/{symbol}")
def get_archive(symbol: str):
    db = Database()
    history = db.get_history(symbol)
    return {"symbol": symbol, "history": history}

@router.get("/indices/history")
def get_indices_history():
    """
    Get combined history for major indices.
    """
    db = Database()
    # Map of display name to ticker
    indices = ["SPY", "QQQ", "DIA", "IWM", "^VIX"]
    history = db.get_indices_history(indices)
    return {"history": history}

@router.get("/market/overview")
def get_market_overview(date: str = None):
    """
    Get market overview for Top 50 symbols.
    Optional 'date' param (YYYY-MM-DD) to view historical snapshot.
    """
    # Top 50 S&P 500 symbols (Approximate by weight)
    top_symbols = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
        "JPM", "V", "XOM", "UNH", "MA", "PG", "COST", "JNJ", "HD", "MRK",
        "ABBV", "CVX", "BAC", "CRM", "WMT", "AMD", "PEP", "KO", "NFLX", "ADBE",
        "TMO", "LIN", "DIS", "MCD", "WFC", "CSCO", "ACN", "INTU", "ORCL", "QCOM",
        "CAT", "VZ", "IBM", "AMAT", "GE", "UBER", "NOW", "DHR", "TXN", "SPGI"
    ]
    
    overview = []
    loader = DataLoader(settings.DATA_CACHE_DIR)
    registry = ModelRegistry(settings.MODELS_DIR)
    pipeline = FeaturePipeline()
    
    target_date_ts = pd.Timestamp(date) if date else None

    for sym in top_symbols:
        try:
            # Use cache to speed up, and limit history to 5 years for overview
            # If historical date requested, ensure we fetch enough history covering that date
            df = loader.get_data(sym, start_date="2020-01-01", use_cache=True)
            
            # Smart Cache Refresh:
            # If we requested a specific date (or today) and the cache is stale (doesn't have it),
            # force a refresh from yfinance.
            if df.empty or (target_date_ts and df.index[-1] < target_date_ts):
                # Only refresh if the target date is reasonable (e.g. not in the far future)
                # But here we just trust the user/system. If it's today's date, we want fresh data.
                # We also check if target_date is <= today to avoid useless fetches for future dates
                if target_date_ts and target_date_ts <= pd.Timestamp.now().normalize():
                     print(f"Cache stale for {sym} (Requested {date}, Max {df.index[-1].date()}). Refreshing...")
                     df = loader.get_data(sym, start_date="2020-01-01", use_cache=False)

            if df.empty:
                continue

            # Filter by date if provided
            if target_date_ts:
                # Get data up to and including the target date
                df = df[df.index <= target_date_ts]
                if df.empty:
                    continue
            
            if len(df) < 15: # Need at least some history
                continue
            
            # Prices
            today_row = df.iloc[-1]
            today_date = str(df.index[-1].date())
            today_open = float(today_row['Open'])
            today_close = float(today_row['Close'])
            
            # 10 days ago (trading days)
            if len(df) > 10:
                past_row = df.iloc[-11]
                past_date = str(df.index[-11].date())
                past_open = float(past_row['Open'])
                past_close = float(past_row['Close'])
            else:
                past_date = "N/A"
                past_open = 0.0
                past_close = 0.0

            # Forecasts for multiple horizons
            horizons = [10, 100, 365, 547, 730]
            forecast_data = {}
            
            # Pre-calculate Kalman trend for fallbacks
            try:
                kalman = KalmanTrend()
                log_prices = np.log(df['Close'].tail(252))
                kalman.fit_transform(log_prices)
                trend_state = kalman.get_current_state()
                trend_slope = trend_state['trend_slope']
            except:
                trend_slope = 0.0

            for h in horizons:
                forecast_pct = None
                forecast_price = None
                
                # 1. Try LightGBM
                model = registry.load_forecast_model(sym, h)
                if model:
                    try:
                        X_inf = pipeline.get_inference_data(df)
                        pred = model.predict(X_inf)[0]
                        forecast_pct = (np.exp(pred) - 1) * 100
                    except:
                        pass
                
                # 2. Fallback to Kalman Trend
                if forecast_pct is None:
                    try:
                        # Soft Clamp (Tanh Compression)
                        # Instead of hard-capping at 40%, we use tanh to smoothly compress 
                        # high drifts towards a maximum asymptote.
                        # Max Annualized = 85% -> log(1.85) ≈ 0.615
                        # Max Daily = 0.615 / 252 ≈ 0.00244
                        max_daily_slope = 0.00244
                        
                        # tanh(x) behaves like x for small x, but approaches 1 for large x.
                        # We want: slope_out = max_slope * tanh(slope_in / max_slope)
                        if max_daily_slope > 0:
                            clamped_slope = max_daily_slope * np.tanh(trend_slope / max_daily_slope)
                        else:
                            clamped_slope = 0.0
                        
                        # Simple linear extrapolation with clamped slope
                        forecast_pct = (np.exp(clamped_slope * h) - 1) * 100
                        
                        # Final safety clamp (-90% to +500%) just in case
                        forecast_pct = max(-90.0, min(forecast_pct, 500.0))
                    except:
                        forecast_pct = 0.0

                # Calculate Target Price
                forecast_price = today_close * (1 + forecast_pct / 100)
                
                forecast_data[f"forecast_{h}d_pct"] = float(forecast_pct)
                forecast_data[f"forecast_{h}d_price"] = float(forecast_price)

            overview_item = {
                "symbol": sym,
                "date": today_date,
                "today_open": today_open,
                "today_close": today_close,
                "past_date": past_date,
                "past_open": past_open,
                "past_close": past_close,
            }
            # Merge forecast data
            overview_item.update(forecast_data)
            
            overview.append(overview_item)
            # print(f"Processed {sym}") # Debug
        except Exception as e:
            print(f"Error processing {sym}: {e}")
            continue
            
    print(f"Market Overview complete. {len(overview)} symbols.")
    return {"overview": overview}
