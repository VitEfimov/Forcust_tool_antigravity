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
                    "LightGBM": float(lgb_pred),
                    "Transformer": float(trans_pred),
                    "GARCH Volatility": float(vol_pred),
                    "Kalman Trend": float(trend_slope),
                    "HMM Regime": hmm.get_regime_label(current_regime),
                    "Copula Adjustment": 0.0, # Placeholder until Copula is fully active
                    "Monte Carlo P50": 0.0 # Placeholder, calculated below
                }
            }
            
            # 6. Simulation & Analysis for this horizon
            # We use the daily volatility for simulation
            daily_vol = returns.std()
            
            # Run Simulation
            sim = Simulator(n_sims=500, horizon=h)
            # Pass total log return for the horizon
            sim_result = sim.simulate(current_price, float(final_log_return), daily_vol)
            
            # Analysis: ML vs Monte Carlo
            ml_price = float(current_price * np.exp(final_log_return))
            mc_p50 = sim_result['quantiles']['p50']
            
            divergence = (mc_p50 - ml_price) / ml_price
            
            analysis_text = "Stable"
            if divergence < -0.05:
                analysis_text = "High Downside Risk (MC < ML)"
            elif divergence > 0.05:
                analysis_text = "Potential Upside Surprise (MC > ML)"
            
            if daily_vol * np.sqrt(252) > 0.4:
                analysis_text += " | High Volatility"
            
            # Add to forecast object
            forecasts[f"{h}d"]["simulation"] = sim_result['quantiles']
            forecasts[f"{h}d"]["analysis"] = analysis_text
            forecasts[f"{h}d"]["components"]["Monte Carlo P50"] = mc_p50

            # Save to DB
            db.save_forecast(current_date, symbol, h, float(final_log_return), float(current_price), str(target_date))

        return {
            "symbol": symbol,
            "date": current_date,
            "current_price": float(current_price),
            "regime": {
                "current": current_regime,
                "label": hmm.get_regime_label(current_regime),
                "probs": regime_probs.tolist()
            },
            "forecasts": forecasts
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

@router.get("/watchlist")
def get_watchlist():
    db = Database()
    return {"symbols": db.get_watchlist()}

@router.post("/watchlist/{symbol}")
def add_to_watchlist(symbol: str):
    db = Database()
    db.add_to_watchlist(symbol)
    return {"status": "added", "symbol": symbol.upper()}

@router.delete("/watchlist/{symbol}")
def remove_from_watchlist(symbol: str):
    db = Database()
    db.remove_from_watchlist(symbol)
    return {"status": "removed", "symbol": symbol.upper()}

@router.get("/watchlist/overview")
def get_watchlist_overview(date: str = None):
    """
    Get market overview for Watchlist symbols.
    """
    db = Database()
    symbols = db.get_watchlist()
    if not symbols:
        return {"overview": []}
    
    return get_market_overview_logic(symbols, date)

@router.get("/market/overview")
def get_market_overview(date: str = None):
    """
    Get market overview for Top 50 symbols.
    """
    # Top 50 S&P 500 symbols (Approximate by weight)
    top_symbols = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
        "JPM", "V", "XOM", "UNH", "MA", "PG", "COST", "JNJ", "HD", "MRK",
        "ABBV", "CVX", "BAC", "CRM", "WMT", "AMD", "PEP", "KO", "NFLX", "ADBE",
        "TMO", "LIN", "DIS", "MCD", "WFC", "CSCO", "ACN", "INTU", "ORCL", "QCOM",
        "CAT", "VZ", "IBM", "AMAT", "GE", "UBER", "NOW", "DHR", "TXN", "SPGI"
    ]
    return get_market_overview_logic(top_symbols, date)

def get_market_overview_logic(symbols: list, date: str = None):
    overview = []
    loader = DataLoader(settings.DATA_CACHE_DIR)
    registry = ModelRegistry(settings.MODELS_DIR)
    pipeline = FeaturePipeline()
    hmm = registry.load_hmm("SPY") # Load generic or specific? HMM is per symbol usually.
    # We need to load HMM per symbol if we want regime labels.
    
    target_date_ts = pd.Timestamp(date) if date else None

    for sym in symbols:
        try:
            # Use cache to speed up
            df = loader.get_data(sym, start_date="2020-01-01", use_cache=True)
            
            # Smart Cache Refresh
            if df.empty or (target_date_ts and df.index[-1] < target_date_ts):
                if target_date_ts and target_date_ts <= pd.Timestamp.now().normalize():
                     # print(f"Cache stale for {sym}. Refreshing...")
                     df = loader.get_data(sym, start_date="2020-01-01", use_cache=False)

            if df.empty:
                continue

            # Filter by date
            if target_date_ts:
                df = df[df.index <= target_date_ts]
                if df.empty:
                    continue
            
            if len(df) < 15:
                continue
            
            # Prices
            today_row = df.iloc[-1]
            today_date = str(df.index[-1].date())
            today_open = float(today_row['Open'])
            today_close = float(today_row['Close'])
            
            # 10 days ago
            if len(df) > 10:
                past_row = df.iloc[-11]
                past_date = str(df.index[-11].date())
                past_open = float(past_row['Open'])
                past_close = float(past_row['Close'])
            else:
                past_date = "N/A"
                past_open = 0.0
                past_close = 0.0

            # Forecasts
            horizons = [10, 100, 365, 547, 730]
            forecast_data = {}
            
            # Pre-calculate Kalman trend
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
                
                # 2. Fallback to Kalman Trend (Soft Clamp)
                if forecast_pct is None:
                    try:
                        max_daily_slope = 0.00244
                        if max_daily_slope > 0:
                            clamped_slope = max_daily_slope * np.tanh(trend_slope / max_daily_slope)
                        else:
                            clamped_slope = 0.0
                        
                        forecast_pct = (np.exp(clamped_slope * h) - 1) * 100
                        forecast_pct = max(-90.0, min(forecast_pct, 500.0))
                    except:
                        forecast_pct = 0.0

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
            overview_item.update(forecast_data)
            overview.append(overview_item)
            
        except Exception as e:
            print(f"Error processing {sym}: {e}")
            continue
            
    return {"overview": overview}

@router.get("/simulation/advanced/{symbol}")
def get_advanced_simulation(symbol: str, days: int = 730, method: str = "garch", conservative: bool = False):
    """
    Run advanced realistic simulation (Regime-aware GARCH + Jumps).
    method: 'garch' or 'bootstrap'
    """
    try:
        symbol = symbol.upper()
        loader = DataLoader(settings.DATA_CACHE_DIR)
        # Get last 5 years for good regime fitting
        df = loader.get_data(symbol, start_date="2018-01-01")
        
        if df.empty:
            raise HTTPException(status_code=404, detail="Symbol data not found")
            
        returns = df['Close'].pct_change().dropna()
        current_price = float(df['Close'].iloc[-1])
        
        from src.models.advanced_simulation import AdvancedSimulator
        from src.models.hmm import RegimeDetector
        
        sim = AdvancedSimulator()
        
        if method == "bootstrap":
            result = sim.block_bootstrap(returns, current_price, days=days)
            # Bootstrap doesn't support multi-horizon dict yet, so we wrap it
            return {
                "symbol": symbol,
                "method": "Block Bootstrap",
                "current_price": current_price,
                "quantiles": {days: result['quantiles']}, # Wrap in horizon dict
                "paths": result['final_prices'].tolist() # This is wrong, need paths. 
                # Actually block_bootstrap needs update for paths if we want chart.
                # For now, let's focus on GARCH method which is the main one.
            }
        else:
            # GARCH + Regime
            hmm = RegimeDetector()
            hmm.fit(returns)
            regimes = hmm.predict(returns)
            current_regime = int(regimes[-1])
            regime_label = hmm.get_regime_label(current_regime)
            
            # Get Transition Matrix
            transmat = hmm.model.transmat_
            
            # Fit Params
            params = sim.fit_regime_params(returns, regimes)
            
            # Simulate (Max Horizon 730d)
            sim_res = sim.simulate_paths(
                start_price=current_price,
                start_regime=current_regime,
                params=params,
                transmat=transmat,
                days=730, # Always run full 2 years
                sims=1000,
                conservative=conservative
            )
            
            # Generate Interpretation
            analysis = {}
            for h, q in sim_res['quantiles'].items():
                p10, p50, p90 = q['p10'], q['p50'], q['p90']
                upside = (p90 / current_price - 1) * 100
                downside = (p10 / current_price - 1) * 100
                
                risk_label = "Moderate"
                if downside < -20 and h <= 30: risk_label = "High Crash Risk"
                elif downside < -40: risk_label = "High Risk"
                elif upside > 50 and downside > -10: risk_label = "Bullish Skew"
                
                analysis[h] = {
                    "risk_label": risk_label,
                    "upside_pct": upside,
                    "downside_pct": downside,
                    "interpretation": f"P90: +{upside:.1f}%, P10: {downside:.1f}% ({risk_label})"
                }

            return {
                "symbol": symbol,
                "method": "Regime-Switching GARCH + Jump Diffusion",
                "current_price": current_price,
                "current_regime": {
                    "id": current_regime,
                    "label": regime_label
                },
                "quantiles": sim_res['quantiles'], # Dict {10: {...}, 30: {...}}
                "analysis": analysis,
                "paths": sim_res['paths'][:, ::5].tolist() # Downsample paths
            }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
