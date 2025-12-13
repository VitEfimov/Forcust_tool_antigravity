from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
import asyncio
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
from collections import deque
import numpy as np
import math
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

from src.core.config import settings
from src.data.loader import DataLoader
from src.models.registry import ModelRegistry
from src.features.pipeline import FeaturePipeline
from src.core.database import get_db, add_to_watchlist, remove_from_watchlist, get_watchlist, get_market_overview_logic
from src.core.cache import timed_cache
from src.core.monitoring import monitor

router = APIRouter()

# Top 20 S&P 500 Stocks by market cap (for faster loading)
# Top 50 S&P 500 Stocks by market cap (approximate selection)
TOP_SP500 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "LLY",
    "JPM", "V", "XOM", "JNJ", "MA", "PG", "HD", "COST", "AVGO", "CVX",
    "MRK", "ABBV", "PEP", "KO", "BAC", "ADBE", "WMT", "MCD", "CSCO", "CRM",
    "ACN", "TMO", "LIN", "AMD", "NFLX", "ABT", "DHR", "ORCL", "CMCSA", "DIS",
    "WFC", "TXN", "VZ", "NEE", "PM", "UPS", "NKE", "INTC", "RTX", "MS"
]

# --- Live Logs Buffer ---
SIMULATION_LOGS = deque(maxlen=2000)

# --- Live Logs SSE Broadcaster ---
class LogBroadcaster:
    def __init__(self):
        self._subscribers = set()
        self._lock = asyncio.Lock()

    async def subscribe(self):
        queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        try:
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            async with self._lock:
                self._subscribers.remove(queue)

    async def publish(self, msg: str):
        async with self._lock:
            for queue in self._subscribers:
                queue.put_nowait(msg)

log_broadcaster = LogBroadcaster()

@router.get("/simulation/logs/stream")
async def stream_simulation_logs(request: Request):
    """SSE endpoint for live logs."""
    return StreamingResponse(log_broadcaster.subscribe(), media_type="text/event-stream")

# Keep legacy endpoint for history fetching if needed, or deprecate
@router.get("/simulation/logs")
def get_simulation_logs():
    return {"logs": list(SIMULATION_LOGS)}

@router.delete("/simulation/logs")
def clear_simulation_logs():
    SIMULATION_LOGS.clear()
    return {"status": "cleared"}
def _compute_market_overview(symbols: List[str]) -> dict:
    """Internal function to compute market overview. Checks local file cache first."""
    


    # 2. Get Base Data (Price, Change) from batch fetch
    base_data = get_market_overview_logic(symbols)
    overview_list = base_data.get("overview", [])
    
    # 3. Simple Volatility Check (Replaces heavy simulation for Overview)
    # User requested "simplest version" for overview to be fast.
    
    enriched_overview = []
    
    for item in overview_list:
        symbol = item['symbol']
        try:
            # We already validated data exists in get_market_overview_logic
            # But let's check basic volatility from the loader's cache if available or just fetch minimal
            # Ideally we reuse the data we just fetched? get_market_overview_logic just gets price.
            # We need history for volatility.
            
            loader = DataLoader(settings.DATA_CACHE_DIR)
            # Fetch last 90 days for trend/volatility
            # "if day is saturday or sunday use data from friday" -> yfinance history() does this mostly auto
            # but we will just take the last available candle.
            
            df = loader.get_data(symbol, start_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"))
            
            if not df.empty:
                # Calculate simple Volatility (Std Dev of returns)
                returns = df['Close'].pct_change().dropna()
                vol_30d = returns.tail(30).std() * np.sqrt(252) * 100 # Annualized
                
                # Trend (Simple moving average compare)
                sma_20 = df['Close'].tail(20).mean()
                price = df['Close'].iloc[-1]
                
                # Classify Risk/Trend
                if vol_30d > 40:
                    item['risk_label'] = "High Volatility"
                    item['volatility_outlook'] = "Unstable"
                elif vol_30d < 15:
                    item['risk_label'] = "Low Volatility"
                    item['volatility_outlook'] = "Stable"
                else:
                    item['risk_label'] = "Moderate"
                    item['volatility_outlook'] = "Normal"
                    
                if price > sma_20:
                    item['regime'] = "Uptrend"
                else:
                    item['regime'] = "Downtrend"
                    
                # Simple Forecast using Log-Normal Geometric Brownian Motion (Analytical Median)
                # This avoids unrealistic explosion from naive compounding.
                # Median Price = S0 * exp((mu - 0.5*sigma^2) * T)
                # We calculate % change from that.
                
                mu = returns.mean()
                sigma = returns.std()
                
                # Drift parameter
                raw_drift = mu - 0.5 * (sigma ** 2)
                
                # Capping Mechanism for Realistic Long-Term Projections
                # Even strong bull runs rarely exceed 60% CARG for 2 years straight.
                # We cap annualized drift to prevent exponential explosion (e.g. +3850%).
                
                if not np.isnan(raw_drift):
                    ann_drift = raw_drift * 252
                    # Cap between -50% and +60% annualized drift
                    capped_ann_drift = max(-0.50, min(0.60, ann_drift))
                    drift = capped_ann_drift / 252
                else:
                    drift = np.nan
                
                for h in [10, 30, 100, 365, 547, 730]:
                    if np.isnan(drift):
                        item[f'forecast_{h}d_pct'] = None
                    else:
                        # Analytical Median Return
                        projected_pct = (np.exp(drift * h) - 1) * 100
                        item[f'forecast_{h}d_pct'] = round(projected_pct, 2)
                    
            else:
                item['risk_label'] = "N/A"
                item['regime'] = "Unknown"
        
        except Exception as e:
            item['risk_label'] = "Error"
            item['regime'] = "Error"
            
        enriched_overview.append(item)
    
    result = {"overview": enriched_overview}
    


    return result

@timed_cache(refresh_hours=[10, 12, 14, 16])
def _cached_sp500_overview() -> dict:
    """Cached Top 20 S&P 500 overview."""
    return _compute_market_overview(TOP_SP500)

@timed_cache(refresh_hours=[10, 12, 14, 16])
def _cached_watchlist_overview(symbols_tuple: tuple) -> dict:
    """Cached watchlist overview."""
    return _compute_market_overview(list(symbols_tuple))

@router.get("/market/overview")
def get_market_overview():
    """
    Get market overview for Top 50 S&P 500 stocks.
    Cached and refreshes at 10am, 12pm, 2pm, 4pm.
    """
    try:
        return _cached_sp500_overview()
    except Exception as e:
        print(f"Error in market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/watchlist/overview")
def get_watchlist_overview():
    """
    Get market overview for the user's watchlist.
    Cached and refreshes at 10am, 12pm, 2pm, 4pm.
    """
    try:
        symbols = get_watchlist()
        if not symbols:
            return {"overview": []}
        # Convert to tuple for hashability in cache key
        return _cached_watchlist_overview(tuple(sorted(symbols)))
    except Exception as e:
        print(f"Error in watchlist overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/history")
def get_market_overview_history(limit: int = 5):
    """
    Get historical Daily Market Overviews (10 AM / 4 PM dumps).
    Returns list of saved market snapshots.
    """
    try:
        from src.core.database import get_db
        history = get_db().get_market_overview_history(limit=limit)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/watchlist")
def get_user_watchlist():
    """Get all symbols in watchlist."""
    return {"symbols": get_watchlist()}

@router.post("/watchlist/{symbol}")
def add_watchlist_item(symbol: str):
    """Add a symbol to watchlist."""
    try:
        add_to_watchlist(symbol.upper())
        return {"status": "success", "symbol": symbol.upper()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/watchlist/{symbol}")
def remove_watchlist_item(symbol: str):
    """Remove a symbol from watchlist."""
    try:
        remove_from_watchlist(symbol.upper())
        return {"status": "success", "symbol": symbol.upper()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@timed_cache(refresh_hours=[10, 12, 14, 16])
def _compute_full_forecast(symbol: str) -> dict:
    """Cached internal forecast computation."""
    loader = DataLoader(settings.DATA_CACHE_DIR)
    df = loader.get_data(symbol)
    
    if df.empty:
        raise ValueError("Symbol data not found")
        
    # Initialize models
    registry = ModelRegistry()
    from src.features.pipeline import FeaturePipeline
    pipeline = FeaturePipeline()
    
    # Get recent data for context
    recent = df.tail(30).reset_index()
    history = []
    for _, row in recent.iterrows():
        history.append({
            "date": row['Date'].strftime("%Y-%m-%d"),
            "price": float(row['Close']),
            "volume": int(row['Volume']) if 'Volume' in row else 0
        })
        
    current_price = float(df['Close'].iloc[-1])
    
    # Run Forecasts for multiple horizons
    horizons = [10, 30, 100, 365, 547, 730]
    forecasts = []
    
    # HMM Regime Detection
    from src.models.hmm import RegimeDetector
    hmm = RegimeDetector()
    returns = df['Close'].pct_change().dropna()
    hmm.fit(returns)
    regime_idx = int(hmm.predict(returns)[-1])
    regime_label = hmm.get_regime_label(regime_idx)
    
    # Monte Carlo Simulation (Simple for this endpoint)
    from src.models.monte_carlo import Simulator
    
    # Initialize Ensemble Components
    from src.models.ensemble import EnsembleModel
    from src.models.kalman_filter import KalmanTrend
    from src.models.garch_volatility import GarchModel
    
    # A. Kalman Trend Extraction
    kt = KalmanTrend()
    kt.fit_transform(df['Close'])
    trend_data = kt.get_current_state()
    trend_slope = trend_data['trend_slope']
    
    # B. GARCH Volatility Factor
    garch = GarchModel()
    try:
        garch.fit(returns)
        vol_annual = garch.predict(horizon=30)
    except:
        vol_annual = returns.std() * np.sqrt(252)
        
    # C. Ensemble
    ensemble = EnsembleModel()

    for h in horizons:
        # 1. ML Forecast (LightGBM)
        lgbm_log_ret = 0.0
        model = registry.load_forecast_model(symbol, h)
        if model:
            try:
                X_inf = pipeline.get_inference_data(df)
                lgbm_log_ret = model.predict(X_inf)[0]
            except:
                pass
        
        # 2. Deep Learning (Transformer) - Placeholder for now
        trans_log_ret = 0.0
        
        # 3. Meta-Model Combination
        # Map regime label to 0/1 (Bear/Bull)
        regime_code = 1 if "Bear" not in regime_label and "High Vol" not in regime_label else 0
        
        final_log_ret = ensemble.predict(
            lgbm_pred=lgbm_log_ret,
            transformer_pred=trans_log_ret,
            current_regime=regime_code,
            trend_slope=trend_slope,
            volatility=vol_annual
        )
        
        ml_forecast_pct = (np.exp(final_log_ret) - 1) * 100
        
        # 2. Monte Carlo (Simple) - Create simulator with correct horizon
        mc_sim = Simulator(n_sims=1000, horizon=h)
        mc_res = mc_sim.simulate(current_price, 0.0, returns.std())
        mc_p10 = mc_res['quantiles']['p10']
        mc_p50 = mc_res['quantiles']['p50']
        mc_p90 = mc_res['quantiles']['p90']
        
        mc_p10_pct = (mc_p10 / current_price - 1) * 100
        mc_p50_pct = (mc_p50 / current_price - 1) * 100
        mc_p90_pct = (mc_p90 / current_price - 1) * 100
        
        # Divergence Analysis
        divergence = ml_forecast_pct - mc_p50_pct
        risk_assessment = "Neutral"
        if divergence > 5: risk_assessment = "High Upside Potential (ML > MC)"
        elif divergence < -5: risk_assessment = "High Downside Risk (ML < MC)"
        
        forecasts.append({
            "horizon": h,
            "ml_forecast_pct": ml_forecast_pct,
            "ml_price": current_price * (1 + ml_forecast_pct/100),
            "mc_p10_pct": mc_p10_pct,
            "mc_p10_price": mc_p10,
            "mc_p50_pct": mc_p50_pct,
            "mc_p50_price": mc_p50,
            "mc_p90_pct": mc_p90_pct,
            "mc_p90_price": mc_p90,
            "risk_assessment": risk_assessment
        })

    return {
        "symbol": symbol,
        "current_price": current_price,
        "regime": regime_label,
        "history": history,
        "forecasts": forecasts
    }

@router.get("/forecast/{symbol}")
def get_forecast(symbol: str):
    """
    Get detailed forecast for a specific symbol.
    Cached and refreshes at 10am, 12pm, 2pm, 4pm.
    """
    try:
        symbol = symbol.upper()
        return _compute_full_forecast(symbol)  
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# V2 Advanced Simulation - NEW endpoint (does not modify existing logic)
# ============================================================================

@timed_cache(refresh_hours=[10, 12, 14, 16])
def _compute_advanced_simulation(symbol: str, conservative: bool, engine: str = 'legacy') -> dict:
    """Cached internal calculation for advanced V2 simulation"""
    loader = DataLoader(settings.DATA_CACHE_DIR)
    # Get last 8 years for robust regime fitting (was 2015)
    df = loader.get_data(symbol, start_date="2015-01-01")  
    
    if df.empty:
        raise ValueError("Symbol data not found")
        
    returns = df['Close'].pct_change().dropna()
    current_price = float(df['Close'].iloc[-1])
    
    from src.models.advanced_simulation import AdvancedSimulator
    from src.models.hmm import RegimeDetector
    
    # HMM with 3 regimes for V2 (Bull, Transition, Bear)
    # Simulator
    sim = AdvancedSimulator()
    hmm = RegimeDetector()
    
    try:
        # Try Advanced HMM+GARCH Pipeline
        hmm.fit(returns)
        regimes = hmm.predict(returns)
        current_regime = int(regimes[-1])
        regime_label = hmm.get_regime_label(current_regime)
        transmat = hmm.model.transmat_
        
        params = sim.fit_regime_params(returns, regimes, n_regimes=transmat.shape[0])
        
        sim_res = sim.simulate_paths(
            start_price=current_price,
            start_regime=current_regime,
            params=params,
            transmat=transmat,
            days=730,
            sims=2000,
            conservative=conservative,
            engine=engine
        )
        method_label = f"V2: Regime-Switching GARCH ({engine})"
        
    except Exception as e:
        print(f"[Advanced Sim] HMM/GARCH failed for {symbol}: {e}. Falling back to Bootstrap.")
        # Fallback: Robust Block Bootstrap
        # Simulate 730 days using history
        sim_res = sim.block_bootstrap(
            returns, 
            start_price=current_price, 
            days=730, 
            sims=2000
        )
        current_regime = 0
        regime_label = "Unstable (Fallback)"
        transmat = np.eye(3) # Dummy
        method_label = f"Fallback: Robust Block Bootstrap (Err: {str(e)})"

        current_regime = 0
        regime_label = "Unstable (Fallback)"
        transmat = np.eye(3) # Dummy
        method_label = f"Fallback: Robust Block Bootstrap (Err: {str(e)})"

    # =========================================================================
    # ENSEMBLE ENGINE LOGIC
    # =========================================================================
    if engine == 'ensemble':
        method_label = "V2: Ensemble (MC + ML + Regime)"
        print(f"[Ensemble] Calculating consensus for {symbol}...")
        
        # 1. Initialize Components
        registry = ModelRegistry()
        pipeline = FeaturePipeline()
        
        # 2. Get ML Forecasts (if available)
        ml_forecasts = {}
        try:
            # FETCH EXTERNAL DATA TO MATCH TRAINING SHAPE
            external_data = {}
            # Use same list as weekly_train
            indices = settings.TIER_1_INDICES + settings.TIER_2_INDICES + ['^MEGACAP']
            for idx in indices:
                try:
                    d = loader.get_data(idx)
                    if not d.empty:
                        external_data[idx] = d
                except: pass
            
            # Pass external_data to pipeline
            X_inf = pipeline.get_inference_data(df, external_data=external_data)
            
            # Check all horizons
            for h in [10, 30, 100, 365, 547, 730]:
                model = registry.load_forecast_model(symbol, h)
                if model:
                    try:
                        pred_log_ret = model.predict(X_inf)[0]
                        ml_forecasts[h] = (np.exp(pred_log_ret) - 1)
                    except Exception as e:
                        # If shapes still mismatch (e.g. old model file), catch safely
                        print(f"[Ensemble] Model predict failed for {h}d: {e}")
                        ml_forecasts[h] = None 
                else:
                    ml_forecasts[h] = None
        except Exception as e:
            print(f"[Ensemble] ML Pipeline Failed: {e}")
            
        # 3. Calculate Regime Analytical Projection (Geometric Brownian Motion)
        # Uses parameters from the fitted regime-switching model (sim.params)
        regime_projections = {}
        
        # Get params for current regime (or fallback to index 0)
        # params key is int(regime)
        r_params = params.get(current_regime, params.get(0, {}))
        
        if r_params.get('method') == 'garch':
            # Analytical drift: mu - 0.5*sigma^2
            # GARCH is mean-reverting, but for simple projection we use current or long-term?
            # Let's use long_term_vol for the projection to be stable
            sigma = r_params.get('long_term_vol', 0.01) 
            # Mean? GARCH assumes zero mean usually unless specified. 
            # We can use the sample mean of the regime?
            # r_params doesn't store mean for GARCH usually.
            # Let's calculate a simple drift from recent history or use a conservative assumption.
            # Use 8% annualized drift as a "neutral" baseline + regime bias.
            
            # Better: Use the 'regime_type' to bias the drift.
            rtype = r_params.get('regime_type', 'Transition')
            if rtype == 'Bull': annual_drift = 0.12 # 12%
            elif rtype == 'Bear': annual_drift = -0.15 # -15%
            else: annual_drift = 0.04 # 4%
            
        else:
            # Simple Params
            mu = r_params.get('mean', 0.0)
            sigma = r_params.get('std', 0.01)
            # annualized
            annual_drift = mu * 252
            
        daily_drift = annual_drift / 252.0
            
        for h in [10, 30, 100, 365, 547, 730]:
            # Simple continuous compounding
            regime_projections[h] = (np.exp(daily_drift * h) - 1)
            
        # 4. Apply Weighted Average to Quantiles
        # Weights: MC=0.4, ML=0.4, Regime=0.2
        w_mc = 0.4
        w_ml = 0.4
        w_rg = 0.2
        
        # Adjust quantiles
        new_quantiles = {}
        original_quantiles = sim_res['quantiles']
        
        for h, q in original_quantiles.items():
            if q['p50'] is None: 
                new_quantiles[h] = q
                continue
                
            mc_p50 = q['p50']
            mc_ret = (mc_p50 / current_price) - 1
            
            ml_ret = ml_forecasts.get(h)
            rg_ret = regime_projections.get(h, 0.0)
            
            # Check for NaN in ML return explicitly
            if ml_ret is None or np.isnan(ml_ret):
                eff_w_mc = w_mc + (w_ml / 2)
                eff_w_rg = w_rg + (w_ml / 2)
                eff_w_ml = 0.0
                ml_ret = 0.0 # dummy
            else:
                eff_w_mc, eff_w_ml, eff_w_rg = w_mc, w_ml, w_rg
                
            try:
                ensemble_ret = (eff_w_mc * mc_ret) + (eff_w_ml * ml_ret) + (eff_w_rg * rg_ret)
                
                if np.isnan(ensemble_ret):
                    ensemble_ret = mc_ret # Fallback to MC if calculation implies NaN
                
                ensemble_price = current_price * (1 + ensemble_ret)
                
                # Shift the distribution
                # Calculate shift vector
                shift = ensemble_price - mc_p50
                
                new_quantiles[h] = {
                    'p10': q['p10'] + shift,
                    'p50': ensemble_price,
                    'p90': q['p90'] + shift
                }
            except Exception as e:
                print(f"[Ensemble] Error calculating horizon {h}: {e}")
                new_quantiles[h] = q # Fallback to original
            
        # Overwrite results
        sim_res['quantiles'] = new_quantiles

    # Generate detailed interpretation per horizon
    analysis = {}
    horizons_info = {
        10: "Short-term: High confidence in trend.",
        30: "1 Month: Volatility drag becomes visible.",
        100: "~3 Months: Medium-term projection.",
        365: "1 Year: Long-term drift dominates.",
        547: "18 Months: Wide cone of uncertainty.",
        730: "2 Years: Very wide probability range."
    }
    
    for h, q in sim_res['quantiles'].items():
        if q['p50'] is None: continue # Skip invalid horizons if any
        
        p10, p50, p90 = q['p10'], q['p50'], q['p90']
        upside = (p90 / current_price - 1) * 100
        downside = (p10 / current_price - 1) * 100
        median_chg = (p50 / current_price - 1) * 100
        
        # Detailed risk classification
        risk_label = "Moderate"
        tail_risk = "Normal"
        volatility_outlook = "Average"
        
        if downside < -50:
            risk_label = "Extreme Downside Risk"
        elif downside < -30:
            risk_label = "High Downside Risk"
        
        if upside > 100:
            if risk_label == "Moderate": risk_label = "High Upside Potential"
        
        analysis[h] = {
            "horizon_days": h,
            "p10": round(p10, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "upside_pct": round(upside, 1),
            "downside_pct": round(downside, 1),
            "median_change_pct": round(median_chg, 1),
            "risk_label": risk_label,
            "tail_risk": tail_risk,
            "volatility_outlook": volatility_outlook,
            "horizon_description": horizons_info.get(h, ""),
            "interpretation": f"Expected: {median_chg:+.1f}% | Range: [{downside:.1f}%, +{upside:.1f}%] | {risk_label}"
        }

    return {
        "symbol": symbol,
        "method": method_label,
        "current_price": round(current_price, 2),
        "current_regime": {
            "id": current_regime,
            "label": regime_label
        },
        "transition_matrix": transmat.tolist(),
        "conservative_mode": conservative,
        "analysis": analysis,
        "paths_sample": sim_res['paths'][:50, ::10].tolist()
    }

@router.get("/simulation/v2/{symbol}")
def get_advanced_simulation_v2(symbol: str, conservative: bool = False, engine: str = 'legacy'):
    """
    V2: Advanced Realistic Simulation with full regime-aware Monte Carlo.
    - HMM regime detection + Markov transitions
    - GARCH volatility paths with Student-t shocks
    - Poisson jump processes
    - Liquidity caps
    - Multi-horizon analysis (10d, 30d, 100d, 365d, 547d, 730d)
    - Cached at scheduled hours
    """
    try:
        symbol = symbol.upper()
        return _compute_advanced_simulation(symbol, conservative, engine)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulation/save")
def save_simulation(data: dict):
    """
    Save simulation results to a local file.
    Expects JSON body with 'symbol' and simulation data.
    """
    try:
        symbol = data.get("symbol", "UNKNOWN").upper()
        # Create directory
        save_dir = Path(settings.LOCAL_DATA_DIR) / "saved_simulations"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Filename: SYMBOL_YYYYMMDD_HHMMSS.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{timestamp}.json"
        filepath = save_dir / filename
        
        # Save JSON
        import json
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
            
        return {"status": "success", "file": str(filepath)}
    except Exception as e:
        print(f"Error saving simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indices")
def get_available_indices():
    """Return list of available indices for training (Optimized Free Tier)"""
    # Map symbols to names
    names = {
        "^GSPC": "S&P 500",
        "^IXIC": "Nasdaq Composite",
        "^RUT": "Russell 2000",
        "^VIX": "CBOE Volatility Index",
        "^TNX": "10-Year Treasury Yield",
        "DX-Y.NYB": "US Dollar Index",
        "CL=F": "Crude Oil",
        "GC=F": "Gold",
        "^MEGACAP": "Mega-Cap Factor (Magnificent 10)"
    }
    
    indices = []
    # Tier 1
    for sym in settings.TIER_1_INDICES:
        indices.append({"symbol": sym, "name": names.get(sym, sym)})
    # Tier 2
    for sym in settings.TIER_2_INDICES:
        indices.append({"symbol": sym, "name": names.get(sym, sym)})
    # Factor
    indices.append({"symbol": "^MEGACAP", "name": names.get("^MEGACAP", "^MEGACAP")})
        
    return {
        "indices": indices
    }

from pydantic import BaseModel
class TrainRequest(BaseModel):
    symbol: str
    indices: List[str]
    horizons: List[int] = [10, 30, 100, 365]

@router.post("/models/train")
def train_model_endpoint(req: TrainRequest):
    """
    Train ML models for a symbol using selected indices as features.
    """
    try:
        symbol = req.symbol.upper().strip()
        loader = DataLoader(settings.DATA_CACHE_DIR)
        
        # 1. Fetch Target Stock Data
        df = loader.get_data(symbol)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
            
        # 2. Fetch Index Data
        external_data = {}
        if req.indices:
            print(f"Fetching indices: {req.indices}")
            for idx in req.indices:
                try:
                    idx_df = loader.get_data(idx)
                    if not idx_df.empty:
                        external_data[idx] = idx_df
                except Exception as e:
                    print(f"Failed to fetch index {idx}: {e}")
        
        # 3. Train Models
        from src.features.pipeline import FeaturePipeline
        from src.models.lightgbm_forecaster import ForecastModel
        
        pipeline = FeaturePipeline()
        registry = ModelRegistry()
        
        results = {}
        
        for h in req.horizons:
            print(f"Training {symbol} horizon {h}d...")
            try:
                X, y, feats = pipeline.get_training_data(df, external_data=external_data, horizon=h)
                
                if len(X) < 100:
                    print(f"Skipping {h}d - insufficient data ({len(X)} rows)")
                    results[f"{h}d"] = "Insufficient Data"
                    continue
                    
                model = ForecastModel()
                # Assuming train returns a dict of metrics
                metrics = model.train(X, y)
                
                # Save
                registry.save_forecast_model(symbol, model, h)
                results[f"{h}d"] = {"status": "trained", "metrics": metrics}
            except Exception as e:
                print(f"Error training horizon {h}: {e}")
                results[f"{h}d"] = {"status": "error", "detail": str(e)}
            
        return {"symbol": symbol, "indices_used": list(external_data.keys()), "results": results}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class WalkForwardRequest(BaseModel):
    symbol: str
    horizon: int = 10
    train_window: int = 730
    step: int = 30
    use_meta_learner: bool = True # Default to True

def _sanitize_val(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
    return v

@router.post("/models/walk_forward")
def walk_forward_endpoint(req: WalkForwardRequest):
    """
    Run a Walk-Forward Validation pipeline.
    """
    # Helper wrapper for sync calling (since WalkForwardForecaster is sync)
    def log_wrapper(msg: str):
         try:
             loop = asyncio.get_running_loop()
             loop.create_task(log_broadcaster.publish(msg))
         except RuntimeError:
             pass
         
         SIMULATION_LOGS.append(msg)
         print(msg)

    try:
        symbol = req.symbol.upper().strip()
        loader = DataLoader(settings.DATA_CACHE_DIR)
        
        # 1. Fetch Data
        log_wrapper(f"Fetching {symbol} from yfinance...")
        df = loader.get_data(symbol)
        if df.empty:
            raise ValueError("Symbol data not found")
            
        # 2. Fetch External Data for Cross-Sectional Features
        external_data = {}
        # VIX, Dollar Index, 10Y Treasury
        for ext_sym in ["^VIX", "DX-Y.NYB", "^TNX"]:
            try:
                ext_df = loader.get_data(ext_sym)
                if not ext_df.empty:
                    # Map to friendly names if needed or use raw
                    friendly_name = ext_sym.replace("^", "").split("-")[0]
                    log_wrapper(f"Fetching {ext_sym} from yfinance...")
                    external_data[friendly_name] = ext_df
            except:
                pass
            
        # 3. Run Pipeline
        from src.models.walk_forward import WalkForwardForecaster
        # Updated arguments for new class
        wf = WalkForwardForecaster(
            symbol=symbol,
            df=df,
            external_data=external_data,
            prediction_horizon=req.horizon,
            train_window=req.train_window,
            step=req.step,
            transaction_cost=0.0005, # 5bps defaults
            slippage=0.0005,
            use_meta_learner=req.use_meta_learner,
            log_func=log_wrapper
        )
        
        results_df_raw = wf.run()
        
        if results_df_raw.empty:
            return {"status": "error", "message": "Not enough data for walk-forward loop"}
            
        # 4. Compute Metrics using class method
        stats = wf.performance_report(periods_per_year=252)
        
        # Map stats to Frontend expected keys
        metrics = {
            "mae_pct": 0.0, # Not in basic stats, can be derived or ignored if acceptable
            "rmse_log": 0.0, # derived locally if needed
            "dir_acc": _sanitize_val(stats['directional_accuracy_pct']),
            "total_strategy_return_pct": _sanitize_val(stats['total_return_pct']),
            "total_benchmark_return_pct": _sanitize_val(stats['benchmark_return_pct']),
            "sharpe_ratio": _sanitize_val(stats['sharpe']),
            "cagr_pct": _sanitize_val(stats['cagr']),
            "max_drawdown_pct": _sanitize_val(stats['max_drawdown_pct']),
            "n_predictions": stats['n_trades']
        }
        
        # 5. Prepare Response List (Front-end Compatibility Mapping)
        summary = wf.summary_dataframe()
        
        # We need to construct a list of dicts that matches what Frontend expects:
        # Date, Current_Price, Predicted_Price, Actual_Price, Predicted_Log_Ret, Actual_Log_Ret, Direction_Correct
        # One_Trade_Return (for log logic), Cum_Strategy (for chart), Cum_Benchmark (for chart)
        
        # Calculate MAE/RMSE manually for completeness
        metrics["mae_pct"] = (abs(summary['Pred'] - summary['Actual_Price']) / summary['Actual_Price']).mean() * 100
        metrics["rmse_log"] = np.sqrt(((summary['Pred_LogRet'] - summary['Actual_LogRet'])**2).mean())
        
        # Benchmark Equity for charting
        # We can reconstruct it from realized benchmarks in raw results
        # results_df_raw['realized_log_ret']
        bench_log_cum = results_df_raw['realized_log_ret'].cumsum()
        bench_equity = np.exp(bench_log_cum)
        
        results_list = []
        for i, row in summary.iterrows():
            # Get benchmark equity at this step (approx matched by index)
            # summary index is 0..N-1, corresponding to folds
            b_eq = bench_equity.iloc[i] if i < len(bench_equity) else 1.0
            
            item = {
                "Date": row['Date'].strftime("%Y-%m-%d"),
                "Horizon_Days": req.horizon,
                "Current_Price": _sanitize_val(row['Price']),
                "Predicted_Log_Ret": _sanitize_val(row['Pred_LogRet']),
                "Actual_Log_Ret": _sanitize_val(row['Actual_LogRet']),
                "Predicted_Price": _sanitize_val(row['Pred']),
                "Actual_Price": _sanitize_val(row['Actual_Price']),
                "Abs_Error_Pct": _sanitize_val(abs(row['Pred'] - row['Actual_Price']) / row['Actual_Price'] * 100),
                "Direction_Correct": row['Dir_Correct'],
                "One_Trade_Return": _sanitize_val(row['Trade_LogRet']),
                "Benchmark_Return": _sanitize_val(results_df_raw.iloc[i]['realized_log_ret']), # raw realized
                "Cum_Strategy": _sanitize_val(row['Equity']),
                "Cum_Benchmark": _sanitize_val(b_eq),
                "Regime": row['Regime'],
                "Regime_Mult": _sanitize_val(row['Regime_Mult'])
            }
            results_list.append(item)
        
        return {
            "status": "success",
            "symbol": symbol,
            "metrics": metrics,
            "results": results_list
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM STATUS & LOGS
# ============================================================================

@router.get("/system/status")
def get_system_status():
    """Return health checks and rich task heartbeats."""
    status = {
        "api": "online",
        "timestamp": datetime.now().isoformat(),
        "database": "unknown",
        "tasks": {}
    }
    
    # 1. Check DB
    try:
        # Simple query
        wl = get_watchlist()
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        
    # 2. Get Heartbeats
    heartbeats = monitor.get_latest_heartbeats()
    
    # 3. Augment with timestamps from files if heartbeats missing (fallback)
    if "DailyAutomation" not in heartbeats:
        daily_report_dir = Path(settings.LOCAL_DATA_DIR) / "daily_reports"
        if daily_report_dir.exists():
            files = list(daily_report_dir.glob("daily_report_*.txt"))
            if files:
                latest = max(files, key=os.path.getmtime)
                ts = datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
                heartbeats["DailyAutomation"] = {"status": "success (legacy)", "timestamp": ts, "details": {}}
                
    if "WeeklyTraining" not in heartbeats:
        weekly_log_dir = Path(settings.LOCAL_DATA_DIR) / "logs"
        if weekly_log_dir.exists():
            files = list(weekly_log_dir.glob("weekly_train_*.log"))
            if files:
                latest = max(files, key=os.path.getmtime)
                ts = datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
                heartbeats["WeeklyTraining"] = {"status": "success (legacy)", "timestamp": ts, "details": {}}

    status["tasks"] = heartbeats
    
    return status

@router.get("/system/logs")
def get_system_logs():
    """Return the content of the latest Daily Report."""
    try:
        daily_report_dir = Path(settings.LOCAL_DATA_DIR) / "daily_reports"
        if not daily_report_dir.exists():
            return {"content": "No reports directory found."}
            
        files = list(daily_report_dir.glob("daily_report_*.txt"))
        if not files:
            return {"content": "No daily reports found."}
            
        latest = max(files, key=os.path.getmtime)
        with open(latest, "r") as f:
            content = f.read()
            
        return {"filename": latest.name, "content": content}
        
    except Exception as e:
        return {"content": f"Error reading logs: {str(e)}"}
@router.get("/system/heartbeats")
def get_system_heartbeats(limit: int = 50):
    """Get recent task activity (heartbeats)."""
    return {"events": monitor.get_recent_heartbeats(limit)}

@router.get("/system/status")
def get_system_status():
    """
    Get system health status (Database, API, Tasks).
    """
    db_status = "offline"
    try:
        from src.core.database import get_db
        # Simple check
        get_db() 
        db_status = "online"
    except:
        pass
        
    return {
        "api": "online",
        "database": db_status,
        "tasks": monitor.get_latest_heartbeats()
    }
