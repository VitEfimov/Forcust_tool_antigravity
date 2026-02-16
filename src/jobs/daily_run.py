
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path

# Fix path to include project root
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.core.config import settings
from src.data.loader import DataLoader
# Lazy Import: WalkForwardForecaster (LightGBM)
# Lazy Import: AdvancedSimulator (Torch)
from src.core.database import get_watchlist
from src.core.monitoring import monitor
from src.core.control import task_controller
import time
import threading
import requests

# Logging
LOG_DIR = project_root / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / f"daily_run_{datetime.now().strftime('%Y%m%d')}.log",
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger()
import gc

REPORT_DIR = project_root / "data" / "daily_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 2.1 Market Data Update
MACRO_SYMBOLS = settings.TIER_1_INDICES + settings.TIER_2_INDICES + settings.TIER_3_INDICES

def generate_megacap_index(loader):
    """
    Generate a synthetic '^MEGACAP' index from top 10 components.
    Saves the result to cache and deletes the individual components to save space.
    """
    logger.info("Step 2.1.1: Generating Mega-Cap Index")
    components = settings.MEGA_CAP_COMPONENTS
    
    # 1. Fetch Components (temporary)
    prices_df = pd.DataFrame()
    valid_components = []
    
    for sym in components:
        try:
            df = loader.get_data(sym)
            if not df.empty and len(df) > 100:
                 # Align dates
                 prices_df[sym] = df['Close']
                 valid_components.append(sym)
        except Exception as e:
            logger.warning(f"Failed to fetch component {sym}: {e}")
            
    if prices_df.empty:
        logger.error("No valid mega-cap components found.")
        return

    # 2. Compute Equal-Weighted Index
    # Forward fill missing data
    prices_df = prices_df.ffill().dropna()
    
    # Normalize to start at 100
    normalized = prices_df / prices_df.iloc[0] * 100
    
    # Create the Index (Mean of normalized prices captures the 'Factor' nicely)
    # Alternatively, mean of returns is better for a tradeable index, but 'Mean of Normalized' 
    # is a standard "Basket" approach.
    megacap_series = normalized.mean(axis=1)
    
    # 3. Create DataFrame structure matching standard cache
    # OHLC will just be the index value
    megacap_df = pd.DataFrame(index=megacap_series.index)
    megacap_df['Open'] = megacap_series
    megacap_df['High'] = megacap_series
    megacap_df['Low'] = megacap_series
    megacap_df['Close'] = megacap_series
    megacap_df['Volume'] = 0
    megacap_df['Adj Close'] = megacap_series
    
    # 4. Save to Cache
    loader.save_data('^MEGACAP', megacap_df)
    logger.info(f"Generated ^MEGACAP index with {len(valid_components)} components.")
    
    # 5. Cleanup Components from Cache (Free Tier Optimization)
    # We use internal method or just file deletion if we know the path.
    # Loader doesn't have explicit delete, so we do it manually safely.
    cleanup_count = 0
    for sym in valid_components:
        try:
            p = Path(settings.DATA_CACHE_DIR) / f"{sym}.parquet"
            if p.exists():
                p.unlink()
                cleanup_count += 1
        except: pass
    logger.info(f"Cleaned up {cleanup_count} component files to save space.")


def step_1_update_data(watchlist):
    """Fetch OHLCV for Watchlist + Macro + Megacap."""
    logger.info("Step 2.1: Market Data Update")
    loader = DataLoader(settings.DATA_CACHE_DIR)
    
    # 1. Fetch Core Indices (Tiers 1 & 2)
    macros = MACRO_SYMBOLS
    
    # 2. Fetch User Watchlist
    all_symbols = sorted(list(set(watchlist + macros)))
    
    stats = {"updated": 0, "errors": 0}
    
    for sym in all_symbols:
        try:
            df = loader.get_data(sym) 
            if not df.empty:
                stats["updated"] += 1
        except Exception as e:
            logger.error(f"Failed to fetch {sym}: {e}")
            stats["errors"] += 1
            
    # 3. Generate Mega-Cap Factor
    try:
        generate_megacap_index(loader)
        stats["generated_megacap"] = True
    except Exception as e:
        logger.error(f"Failed to generate megacap: {e}")
            
    logger.info(f"Data Update Complete. {stats}")
    return loader

def step_2_walk_forward(symbol, loader, horizon=10, train_window=730, step=30, use_meta=True):
    """Run Walk-Forward Pipeline (Rolling Training)."""
    try:
        from src.models.walk_forward import WalkForwardForecaster
    except ImportError as e:
        logger.info(f"  Lightweight Mode: Skipping ML for {symbol} (dependencies missing: {e}).")
        # Return basic data so the pipeline continues
        df = loader.get_data(symbol)
        if df.empty: return None
        price = df['Close'].iloc[-1]
        return {
            "dates": datetime.now(),
            "ml_forecast_price": price, # Fallback to current price (Neutral)
            "reliability_score": 0.5,
            "regime": "Unknown",
            "current_price": price
        }
        
    logger.info(f"Step 2.2: Walk-Forward for {symbol} (H={horizon}, W={train_window})")
    
    # Context Data
    external_data = {}
    for mac in MACRO_SYMBOLS:
        try:
            d = loader.get_data(mac)
            if not d.empty:
                external_data[mac.replace('^','')] = d
        except: pass
        
    df = loader.get_data(symbol)
    if df.empty: return None
    
    # Configure Pipeline
    wf = WalkForwardForecaster(
        symbol=symbol,
        df=df,
        external_data=external_data,
        prediction_horizon=horizon,
        train_window=train_window,
        step=step,
        use_meta_learner=use_meta,
        verbose=True,
        log_func=logger.info
    )
    
    # Run
    results = wf.run()
    
    # Extract latest state
    latest_pred = df['Close'].iloc[-1] # Default to current price if empty
    reliability = 0.5
    regime_label = "Unknown"
    
    if not results.empty:
        last_row = results.iloc[-1]
        # Calculate Price from Log Return
        # Pred Price = Current Price * exp(Pred Log Return)
        pred_log_ret = last_row.get('pred_log_ret', 0.0)
        latest_pred = latest_pred * np.exp(pred_log_ret)
        
        reliability = last_row.get('reliability_prob', 1.0) # Correct key is reliability_prob
        regime_label = last_row.get('regime', 'Sideways') # Key is lowercase 'regime'
        
    return {
        "dates": last_row['date'] if not results.empty else datetime.now(),
        "ml_forecast_price": latest_pred,
        "reliability_score": reliability,
        "regime": regime_label,
        "current_price": df['Close'].iloc[-1]
    }

def step_4_simulation(symbol, loader, current_price, tier="tier_3", ml_drift=None):
    """Run Fast Monte-Carlo (Advanced Simulation)."""
    try:
        from src.models.advanced_simulation import AdvancedSimulator
    except ImportError as e:
        logger.info(f"  Lightweight Mode: Skipping Simulation for {symbol} (dependencies missing: {e}).")
        return {
            "mc_p10": current_price,
            "mc_p50": current_price,
            "mc_p90": current_price
        }

    logger.info(f"Step 2.4: Advanced Simulation for {symbol} (Drift={ml_drift})")
    
    try:
        sim = AdvancedSimulator()
        df = loader.get_data(symbol)
        returns = df['Close'].pct_change().dropna()
        
        # We want GARCH calibration if explicitly requested, but for 'Fast' daily
        # we stick to robust methods unless we are sure GARCH won't fail (recursion limit).
        # Let's use 'simple' (historical vol) for speed and stability in Cron, 
        # or 'garch' if we fixed recursion. User said we fixed recursion. 
        # Let's try 'garch' with fallback.
        
        try:
            method = 'garch'
            # Quick check if arch imported
            # Quick check if arch imported
            import arch
            import scipy # Also Check Scipy
        except:
            method = 'simple'
            
        if method == 'garch':
            # Fit GARCH parameters properly
            # Assume single global regime for daily fast simulation
            regimes = np.zeros(len(returns), dtype=int)
            params = sim.fit_regime_params(returns, regimes)
        else:
            params={0: {'method': 'simple', 'std': returns.std(), 'mean': returns.mean()}}
            
        # Determine Sims based on Tier
        sims = 500
        if tier == "tier_1": sims = 2000
        elif tier == "tier_2": sims = 1000
        
        logger.info(f"    Running Simulation ({sims} paths) for {symbol}...")
        
        res = sim.simulate_paths(
            start_price=current_price,
            start_regime=0,
            params=params, 
            days=30,
            sims=sims,
            engine='numpy',
            daily_drift=ml_drift # Inject ML Drift
        )
        
        # Extract Quantiles
        q30 = res['quantiles'][30]
        return {
            "mc_p10": q30['p10'],
            "mc_p50": q30['p50'],
            "mc_p90": q30['p90']
        }
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return {"mc_p50": current_price}

def generate_report_content(symbol, wf_data, sim_data):
    """
    Generate Plain-Language Summary (Section 2.5).
    """
    price = wf_data['current_price']
    ml_target = wf_data.get('ml_forecast_price')
    mc_target = sim_data.get('mc_p50')
    mc_p10 = sim_data.get('mc_p10')
    mc_p90 = sim_data.get('mc_p90')
    rel_score = wf_data.get('reliability_score', 0.5)
    
    # Calculations
    if ml_target:
        ml_upside = (ml_target - price) / price * 100
        ml_upside_str = f"{ml_upside:+.2f}%"
        ml_target_str = f"{ml_target:.2f}"
    else:
        ml_upside = 0
        ml_upside_str = "N/A"
        ml_target_str = "N/A (Cloud Only)"

    if mc_target:
        mc_upside = (mc_target - price) / price * 100
        mc_upside_str = f"{mc_upside:+.2f}%"
        mc_target_str = f"{mc_target:.2f}"
    else:
        mc_upside = 0
        mc_upside_str = "N/A"
        mc_target_str = "N/A"

    # Confidence Intervals
    range_str = "N/A"
    if mc_p10 and mc_p90:
        p10_upside = (mc_p10 - price) / price * 100
        p90_upside = (mc_p90 - price) / price * 100
        range_str = f"[{p10_upside:+.1f}%, {p90_upside:+.1f}%]"
    
    # Agreement
    agreement = "WAITING FOR CLOUD WORKER"
    if ml_target and mc_target:
        if ml_upside > 0 and mc_upside > 0:
            agreement = "STRONG BUY (Confluence)"
        elif ml_upside < 0 and mc_upside < 0:
            agreement = "STRONG SELL (Confluence)"
        elif abs(ml_upside - mc_upside) < 2.0:
            agreement = "NEUTRAL / CONSENSUS"
        else:
            agreement = "DIVERGENCE"
        
    # Final Forecast (Meta-Learning Logic 2.3)
    # final_forecast = (base_forecast_return * reliability) ... roughly
    # effective_return = ml_return * reliability
    effective_ml_return = ml_upside * rel_score
    
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Regime Logic Fallback
    regime = wf_data.get('regime', 'Unknown')
    
    if regime == 'Unknown':
        # Simple fallback based on price vs MC
        if mc_upside > 5: regime = 'Bull'
        elif mc_upside < -5: regime = 'Bear'
        else: regime = 'Sideways'

    agreement_icon = "⚪"
    if "STRONG BUY" in agreement: agreement_icon = "🟢"
    elif "STRONG SELL" in agreement: agreement_icon = "🔴"
    elif "NEUTRAL" in agreement: agreement_icon = "🟡"
    
    # Cost Control Mode
    mode_label = wf_data.get('summary_mode', 'short').upper()
    
    report = f"""
============================================================
DAILY INTELLIGENCE BRIEFING | {date_str} | MODE: {mode_label}
============================================================
ASSET: {symbol}
PRICE: {price:.2f}

1. MARKET REGIME
   - Classification: {regime.upper()}
   - Volatility State: {"HIGH" if rel_score < 0.5 else "NORMAL"}
   - VIX Level: (See Dashboard)

2. FORECASTS (Horizon: {wf_data.get('horizon', 'N/A')} Days)
   - ML Model Target: {ml_target_str} ({ml_upside_str})
   - Monte-Carlo Target: {mc_target_str} ({mc_upside_str})
   - 80% Confidence Range: {range_str}
   - Agreement Level: {agreement_icon} {agreement}

3. META-LEARNER (Reliability Layer)
   - Model Reliability Score: {rel_score:.2f} (0=Low, 1=High)
   - Adjusted Prediction: {effective_ml_return:+.2f}% Upside

4. STRATEGY OUTLOOK
   The system detects a {regime} environment.
   Machine Learning suggests a {ml_upside_str} move, while statistical simulations suggest {mc_upside_str}.
   
   Final Verdict: {agreement}
   Confidence: {"HIGH" if rel_score > 0.7 else "LOW - CAUTION"}

============================================================
[End of Briefing]
"""
    return report

def generate_overview_table(snapshot_data, forecast_map=None):
    """
    Generate a text-based table for the Market Overview.
    forecast_map: {symbol: {30: pct, 365: pct}}
    """
    if not snapshot_data:
        return "No Market Data Available."
    
    if forecast_map is None: forecast_map = {}

    # Sort by Type (Indices first) then Change %
    # Heuristic: Indices start with ^ or are in MACRO list
    indices = []
    stocks = []
    
    for item in snapshot_data:
        sym = item['symbol']
        if sym.startswith('^') or sym in ['DX-Y.NYB', 'CL=F', 'GC=F']:
            indices.append(item)
        else:
            stocks.append(item)
            
    # Sort stocks by abs change (movers)
    stocks.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    lines = []
    lines.append("========================================================================================")
    lines.append("MARKET OVERVIEW SNAPSHOT")
    lines.append("========================================================================================")
    # Header
    lines.append(f"{'SYMBOL':<10} | {'PRICE':<10} | {'CHANGE':<8} | {'REGIME':<10} | {'VOLATILITY':<15} | {'FCST(30d)':<10} | {'FCST(1y)':<10}")
    lines.append("-" * 96)
    
    for item in indices + stocks:
        sym = item['symbol']
        price = f"{item['price']:.2f}"
        chg = f"{item['change_pct']:+.2f}%"
        reg = item['regime']
        vol = item['risk_label']
        
        # Get Forecasts
        f_30 = "N/A"
        f_365 = "N/A"
        
        if sym in forecast_map:
            if 30 in forecast_map[sym]:
                val = forecast_map[sym][30]
                f_30 = f"{val:+.2f}%"
            if 365 in forecast_map[sym]:
                val = forecast_map[sym][365]
                f_365 = f"{val:+.2f}%"
        
        lines.append(f"{sym:<10} | {price:<10} | {chg:<8} | {reg:<10} | {vol:<15} | {f_30:<10} | {f_365:<10}")
        
    return "\n".join(lines)

def cleanup_reports(days_retention=14):
    """Delete daily reports older than N days."""
    try:
        cutoff = datetime.now() - timedelta(days=days_retention)
        count = 0
        if REPORT_DIR.exists():
            for f in REPORT_DIR.glob("daily_report_*.txt"):
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink()
                    count += 1
        logger.info(f"Cleaned up {count} old reports.")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

        logger.error(f"Cleanup failed: {e}")

def keep_alive_pinger(stop_event):
    """
    Background thread to ping the server every 9 minutes execution.
    Target: https://forcust-tool-antigravity.vercel.app/
    purpose: Prevent idle timeout on free tier / keep server alive.
    """
    url = "https://forcust-tool-antigravity.vercel.app/"
    logger.info(f"[KeepAlive] Starting ping loop to {url}")
    while not stop_event.is_set():
        try:
            logger.info("[KeepAlive] Pinging server...")
            requests.get(url, timeout=10)
        except Exception as e:
            logger.warning(f"[KeepAlive] Ping failed: {e}")
            
        # Wait 9 minutes (540s) or until stopped
        if stop_event.wait(540):
            break
    logger.info("[KeepAlive] Stopped.")

def run_daily_automation(scheduled_run: bool = False):
    start_time = time.time()
    run_type = "SCHEDULED" if scheduled_run else "MANUAL"
    print(f"=== STARTING DAILY AUTOMATION ({run_type} RUN) ===")
    
    # Execution Source Logging
    source = os.getenv("EXECUTION_SOURCE", "scheduler")
    if source == "github_actions":
        logger.info("Execution source: GitHub Actions")
        print("Execution source: GitHub Actions")
        
    monitor.log_heartbeat("DailyAutomation", "running", {"source": source})
    
    # --- NEW: Start Run Record ---
    from src.core.database import get_db
    db = get_db()
    run_id = db.start_training_run("daily", source)
    logger.info(f"Started Training Run ID: {run_id}")  
    
    # Start Keep-Alive Thread
    stop_ping = threading.Event()
    ping_thread = threading.Thread(target=keep_alive_pinger, args=(stop_ping,), daemon=True)
    ping_thread.start()
    
    
    # --- LOGIC: HELPER FOR MODE DETERMINATION ---
    def determine_analysis_mode(symbol: str, horizon: int, training_config: dict):
        """
        Determine if we should TRAIN, INFERENCE, or DERIVE.
        """
        tiers = settings.SYMBOL_TIERS
        base_horizons = settings.BASE_HORIZONS
        derived_map = settings.DERIVED_HORIZONS
        AnalysisMode = settings.AnalysisMode
        
        # 0. Check for "ALLOW_FULL_TRAINING" flag (Config or DB)
        # Note: We prefer to check the flag once outside, but here is fine.
        allow_full_training = training_config.get("allow_weekly_training", False) or training_config.get("force_training", False)
        
        # 1. Derived Horizons: STRICTLY NEVER TRAINED (User Rule 5)
        # Always derived from 10d or 100d
        if horizon in derived_map:
             return AnalysisMode.DERIVED, derived_map[horizon]

        # 2. Base Horizons (10, 100)
        # If Full Training is ON -> TRAIN
        # Else -> INFERENCE
        if horizon in base_horizons:
             if allow_full_training:
                  return AnalysisMode.TRAIN, None
             else:
                  return AnalysisMode.INFERENCE, None

        # 3. Fallback (Unknown Horizon)
        return AnalysisMode.INFERENCE, None

    try:
        monitor.log_heartbeat("DailyAutomation", "running", {"step": "start", "run_type": "scheduled" if scheduled_run else "manual"})
        
        # 0. Check for Stop Signal
        if task_controller.should_stop("DailyAutomation", consume=True):
             monitor.log_heartbeat("DailyAutomation", "cancelled", {"reason": "User requested stop"})
             return
        
        # --- NEW: Check Deep Training Flag (DEPRECATED IN DAILY RUN - Handled by deep_train.py) ---
        # We leave this logic off or removed to prevent double execution.
        # Deep training is now a separate job.
        deep_training_flag = False

        
        # Initialize Forecast Map for Report Table
        forecast_map = {}

        # 1. Watchlist
        watchlist = get_watchlist()
        
        # Step 1: Update Data
        loader = step_1_update_data(watchlist)
        monitor.log_heartbeat("DailyAutomation", "running", {"step": "data_update_complete", "details": "Market data fetched"})
        
        # --- NEW: Generate Analysis Configs (Tiered) ---
        ANALYSIS_CONFIGS = []
        
        # Consolidated Target List
        all_targets = set(settings.TIER_1_INDICES + settings.TIER_2_INDICES + settings.TRAINING_TARGETS + watchlist)
        all_targets = sorted(list(all_targets)) # Deduplicated
        
        
        # Horizons to cover: Base + Derived
        all_horizons = sorted(list(set(settings.BASE_HORIZONS + list(settings.DERIVED_HORIZONS.keys()))))
        
        # Build Task List
        for sym in all_targets:
            for h in all_horizons:
                mode, derived_from = determine_analysis_mode(sym, h, settings.TRAINING_CONFIG)
                
                ANALYSIS_CONFIGS.append({
                    "symbol": sym,
                    "horizon": h,
                    "mode": mode,
                    "derived_from": derived_from,
                    "train_window": 1000 if h >= 100 else 730, # Simple heuristic
                    "step": 30,
                    "meta": True 
                })
        
        # --- INTENT LOGGING ---
        intent_log = {
            "daily_run_mode": "SAFE" if not settings.TRAINING_CONFIG["allow_weekly_training"] else "FULL_TRAINING",
            "weekly_training_enabled": settings.TRAINING_CONFIG["allow_weekly_training"],
            "base_horizons": settings.BASE_HORIZONS,
            "derived_horizons": settings.DERIVED_HORIZONS,
            "total_tasks": len(ANALYSIS_CONFIGS),
            "tiers_active": ["tier_1", "tier_2", "tier_3"]
        }
        print(f"\n[INTENT] Execution Plan: {json.dumps(intent_log, indent=2)}\n")
        logger.info(f"Execution Intent: {intent_log}")
        
        # Run Analysis Loop
        final_reports = []
        
        from src.core.database import get_db
        db = get_db()
        
        from src.core.models import WalkForwardResult, AdvancedSimulationResult, MarketOverview
        from src.models.registry import ModelRegistry
        registry = ModelRegistry()
        
        # Track processed symbols to avoid duplicate Simulations per run if multiple configs exist
        processed_sim_symbols = set()
        
        # Capture critical market stats for summary
        market_stats = {
            "regime": "Unknown",
            "model_confidence": 0.5,
            "forecast_spy": {}
        }
        
        # New: Global Regime Tracker
        GLOBAL_MARKET_REGIME = "Unknown"
        total_configs = len(ANALYSIS_CONFIGS)
        
        # Optimization: Local Symbol Cache (cleared when symbol changes)
        # Stores {horizon: wf_data_result} for the current symbol only.
        symbol_cache = {}
        current_symbol_context = None
        
        for i, config in enumerate(ANALYSIS_CONFIGS):
            target_symbol = config['symbol']
            horizon = config['horizon']
            mode = config['mode']
            derived_source = config['derived_from']
            
            # Reset cache if we switched symbols
            if current_symbol_context != target_symbol:
                symbol_cache = {}
                current_symbol_context = target_symbol
                # Preload base results for Derived Mode if needed?
                # Actually, if we process horizons in order (Base then Derived), 
                # we will naturally populate symbol_cache with Base results first.
                # But parallel/sorted order might not guarantee Base First. 
                # settings.BASE_HORIZONS = [10, 100]. Derived 30 from 10.
                # If sorted(all_horizons) -> 10, 30, 60, 100, 365...
                # Yes, 10 comes before 30. 100 comes before 365.
                # So we can just rely on the loop order and `symbol_cache`.
                logger.info(f"Switched context to {target_symbol}. Cache cleared.")

            
            # --- COST CONTROL LOGIC (Fix 5) ---
            # Determine Summary Mode for Analyst
            # Default to "short" unless it's a Tier 1 asset or User Mega Cap
            summary_mode = "short"
            if target_symbol in settings.TIER_1_INDICES or target_symbol in settings.MEGA_CAP_COMPONENTS:
                summary_mode = "long"
            
            # Progress Heartbeat
            monitor.log_heartbeat("DailyAutomation", "running", {
                "step": "analyzing_symbol", 
                "symbol": target_symbol, 
                "progress": f"{i+1}/{total_configs}",
                "horizon": horizon,
                "mode": mode,
                "summary_mode": summary_mode
            })
            
            # Check Stop Signal
            if task_controller.should_stop("DailyAutomation", consume=True):
                 monitor.log_heartbeat("DailyAutomation", "cancelled", {"reason": "User requested stop", "progress": f"{i}/{total_configs}"})
                 return

            print(f"--- Analyzing {target_symbol} (H={horizon}) [Mode: {mode}] ---")
            try:
                # 0. Update Actuals (only need to do once per symbol/horizon tuple really)
                # But actuals are tracked by date/symbol/horizon in DB? 
                # Our simple update_actuals takes (symbol, date, price). It fixes ALL horizons.
                # So we can just do it.
                
                # --- MODE HANDLING ---
                if mode == settings.AnalysisMode.TRAIN:
                    # 1. HEAVY TRAINING PATH
                    wf_data = step_2_walk_forward(
                        target_symbol, loader, 
                        horizon=horizon, 
                        train_window=config['train_window'], 
                        step=config['step'],
                        use_meta=config['meta']
                    )
                    if wf_data: 
                        wf_data['trained'] = True
                        symbol_cache[horizon] = wf_data # Store for derived
                
                elif mode == settings.AnalysisMode.INFERENCE:
                    # 2. INFERENCE ONLY PATH
                    # Reuse the metadata from the last successful run in DB.
                    last_run = db.get_latest_walk_forward_result(target_symbol, horizon=horizon)
                    
                    if last_run and last_run.get('reliability_score'):
                        # Reuse Metadata
                        regime = last_run.get('regime_label', 'Unknown')
                        rel_score = last_run.get('reliability_score', 0.5)
                        prev_pred = last_run.get('prediction_price', 0)
                        
                        # Just update current price
                        df_latest = loader.get_data(target_symbol)
                        current_price = df_latest['Close'].iloc[-1] if not df_latest.empty else 0
                        
                        if current_price <= 0:
                             wf_data = None
                        else:
                            wf_data = {
                                "dates": datetime.now(),
                                "ml_forecast_price": current_price, # Neutral
                                "reliability_score": rel_score,
                                "regime": regime,
                                "current_price": current_price,
                                "trained": False
                            }
                            symbol_cache[horizon] = wf_data
                    else:
                        wf_data = None
                        
                elif mode == settings.AnalysisMode.DERIVED:
                    # 3. DERIVED MODE (Scaled from Base Horizon)
                    base_h = derived_source
                    
                    # Fetch from Local Cache (fresh from this run)
                    base_res = None
                    if base_h in symbol_cache:
                         logger.info(f"Using in-memory base result for {target_symbol} (H={base_h})")
                         # Convert wf_data dict to a format usable? 
                         # symbol_cache stores wf_data dict.
                         # Need to map keys properly:
                         # wf_data keys: ml_forecast_price, reliability_score, regime
                         cached_data = symbol_cache[base_h]
                         base_res = {
                             'prediction_price': cached_data['ml_forecast_price'],
                             'reliability_score': cached_data['reliability_score'],
                             'regime_label': cached_data['regime']
                         }
                    else:
                        # Fallback to DB if not in cache (e.g. if base horizon failed to compute/save in this run?)
                        logger.info(f"Cache miss for {target_symbol} (H={base_h}). Fetching from DB.")
                        base_res = db.get_latest_walk_forward_result(target_symbol, horizon=base_h)

                    df_latest = loader.get_data(target_symbol)
                    current_price = df_latest['Close'].iloc[-1] if not df_latest.empty else 0
                    
                    if base_res and current_price > 0:
                        base_pred = base_res.get('prediction_price', current_price)
                        base_conf = base_res.get('reliability_score', 0.5)
                        base_regime = base_res.get('regime_label', 'Unknown')
                        
                        base_log_ret = np.log(base_pred / current_price)
                        target_h = horizon
                        
                        # 1. Scaled Price (Fix 3: Log-Return Scaling with Sqrt)
                        import math
                        ratio = target_h / base_h
                        scaled_log_ret = base_log_ret * math.sqrt(ratio)
                        
                        final_pred = current_price * np.exp(scaled_log_ret)
                        
                        # Fix 5: Enforce derived != spot price (Guard)
                        if abs(final_pred - current_price) < 1e-6:
                            logger.warning(f"Derived forecast for {target_symbol} collapsed to spot price.")
                        
                        # 2. Volatility Scaling for Confidence (Fix 4: Confidence Decay)
                        decay = np.exp(-0.015 * ratio)
                        scaled_conf = base_conf * decay
                        
                        wf_data = {
                            "dates": datetime.now(),
                            "ml_forecast_price": final_pred,
                            "reliability_score": scaled_conf,
                            "regime": base_regime,
                            "current_price": current_price,
                            "trained": False,
                            "confidence_decay": decay,
                            "summary_mode": summary_mode
                        }
                        symbol_cache[horizon] = wf_data
                    else:
                        wf_data = None

                if not wf_data:
                    print(f"Analysis Failed/Skipped for {target_symbol}. Skipping.")
                    continue
                
                wf_data['horizon'] = horizon
                current_price = wf_data['current_price']
                
                # Capture Stats for Summary (Prefer SPY 10d)
                if target_symbol == 'SPY' and horizon == 10:
                    market_stats['regime'] = wf_data.get('regime', 'Unknown')
                    GLOBAL_MARKET_REGIME = market_stats['regime'] # Set Global Truth
                    
                    market_stats['model_confidence'] = wf_data.get('reliability_score', 0.5)
                    market_stats['forecast_spy'] = {
                        "pred": wf_data['ml_forecast_price'],
                        "upside": (wf_data['ml_forecast_price'] - current_price) / current_price
                    }
                
                # Enforce Global Regime Consistency (Optional: Or just log it?)
                # If we are analyzing a correlated asset (like Tech) and it says Bear but SPY says Bull,
                # we might want to flag it. For now, we trust the asset-level but we use Global for the SUMMARY.
                
                # Update Actuals using the fresh current price
                db.update_actuals(target_symbol, datetime.now().strftime("%Y-%m-%d"), current_price)
                
                # Step 4: Simulation (Run once per symbol per day to save time, unless specific horizon needed)
                # The User request lists "Advanced Simulation V2" separately with a list of symbols.
                # Typically Sim is multi-horizon. Let's run it once per symbol.
                if target_symbol not in processed_sim_symbols:
                    # CALCULATE DRIFT FROM ML
                    # ml_forecast_price is prediction at 'horizon' days.
                    # annual_drift = log(P_h/P_0) / h * 252?  Simulation takes daily_drift.
                    # daily_drift = log(P_h / P_0) / h
                    ml_drift = np.log(wf_data['ml_forecast_price'] / current_price) / horizon
                    
                    # Sanity Check Drift (don't inject crazy values)
                    # Cap at +/- 1% daily (huge)
                    ml_drift = max(min(ml_drift, 0.01), -0.01)
                    
                    # Determine Tier for Simulation Intensity (User Rule 3)
                    sim_tier = "tier_3"
                    if target_symbol in settings.TIER_1_INDICES: sim_tier = "tier_1"
                    elif target_symbol in settings.TIER_2_INDICES: sim_tier = "tier_2"

                    sim_data = step_4_simulation(target_symbol, loader, current_price, tier=sim_tier, ml_drift=ml_drift)
                    
                    # Fix 7: Sanitize Monte Carlo NaNs
                    p10, p50, p90 = sim_data['mc_p10'], sim_data['mc_p50'], sim_data['mc_p90']
                    
                    if any(np.isnan(x) for x in [p10, p50, p90]):
                        logger.warning(f"Monte Carlo produced NaNs for {target_symbol}. Skipping Simulation Save.")
                        # Fallback for report
                        sim_data = {"mc_p50": current_price, "mc_p10": current_price, "mc_p90": current_price}
                    else:
                        # Save Sim Result
                        sim_result = AdvancedSimulationResult(
                            symbol=target_symbol,
                            date=datetime.now().strftime("%Y-%m-%d"),
                            mc_p10=p10,
                            mc_p50=p50,
                            mc_p90=p90,
                            conservative_mode=False 
                        )
                        db.save_advanced_simulation_result(sim_result)
                        processed_sim_symbols.add(target_symbol)
                else:
                    # Reuse previous sim data for report if needed
                    # (Simplified: we just use placeholders or skip reporting section)
                    sim_data = {"mc_p50": current_price, "mc_p10": current_price, "mc_p90": current_price}

                
                # Step 5: Generate Report (Only for H=10 or primary config to avoid log spam?)
                # We'll generate for all but maybe group them.
                report_text = generate_report_content(target_symbol, wf_data, sim_data)
                final_reports.append(f"CONFIG: H={horizon} | {report_text}")
                
                
                # --- NEW: Save Trained Forecast to DB (User Request) ---
                # Calculate target date based on horizon
                # Horizon is trading days.
                target_date = (datetime.now() + timedelta(days=int(horizon * 1.4))).strftime("%Y-%m-%d")
                
                # 1. Standard Forecast Table
                # Fix: Only save if we have a meaningful forecast (not just current price fallback)
                # or if it was actually trained.
                is_meaningful = abs(wf_data['ml_forecast_price'] - current_price) > 0.0001
                if is_meaningful or wf_data.get('trained', False):
                    db.save_forecast(
                        date=datetime.now().strftime("%Y-%m-%d"),
                        symbol=target_symbol,
                        horizon=horizon, 
                        prediction=wf_data['ml_forecast_price'],
                        start_price=current_price,
                        target_date=target_date
                    )
                else:
                    # Optional: We could save it but mark it? For now, skipping protects the DB.
                    pass
                
                # 3. New Symbol Forecast Table (Task 6)
                db.save_symbol_forecast(
                    run_id=run_id,
                    symbol=target_symbol,
                    horizon=horizon,
                    expected_return=(wf_data['ml_forecast_price'] - current_price) / current_price * 100 if current_price else 0.0,
                    confidence=wf_data['reliability_score'],
                    regime=wf_data['regime'],
                    volatility=wf_data.get('volatility_label', 'Unknown') # Need to ensure vol label is present or derive
                ) 

                # 2. Strict Pydantic Models
                # A. Walk-Forward Result
                wf_result = WalkForwardResult(
                    symbol=target_symbol,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    prediction_price=wf_data['ml_forecast_price'],
                    reliability_score=wf_data['reliability_score'],
                    regime_label=wf_data['regime'],
                    mode=mode,
                    trained=wf_data.get('trained', False),
                    derived_from=derived_source
                )
                db.save_walk_forward_result(wf_result)
                
                # --- NEW: Capture Forecast for Report Map ---
                # Capture ALL horizons for the snapshot
                if target_symbol not in forecast_map:
                    forecast_map[target_symbol] = {}
                
                # Calculate % change
                if current_price > 0:
                    pct_change = (wf_data['ml_forecast_price'] - current_price) / current_price * 100
                    forecast_map[target_symbol][horizon] = pct_change

                print(f"[DB] Saved intelligent models for {target_symbol} (H={horizon})")
                
                monitor.log_heartbeat("DailyAnalysis", "success", {"symbol": target_symbol, "horizon": horizon})
                
            except Exception as e:
                logger.error(f"Analysis failed for {target_symbol}: {e}")
                monitor.log_heartbeat("DailyAutomation", "warning", {
                    "step": "symbol_failed",
                    "symbol": target_symbol,
                    "error": str(e)
                })
            
            # Optimization: GC after each symbol
            gc.collect()
        
        # Combine Reports
        full_report = "\n\n".join(final_reports)
        
        # Append Market Overview Table if available
        # (We need to grab the snapshot data - it's generated later in the original code,
        # but we can move that logic up or just do it twice/cache it. 
        # Actually, let's just generate the table from the snapshot logic now.)
        
        # --- NEW: Save Detailed Market Snapshot for Analytics AND Table ---
        try:
            full_snapshot = []
            # Gather all relevant symbols
            snapshot_symbols = sorted(list(set(settings.TRAINING_TARGETS + MACRO_SYMBOLS + ["^MEGACAP"])))
            
            for sym in snapshot_symbols:
                try:
                    df = loader.get_data(sym)
                    if df.empty: continue
                    
                    # Basic Stats
                    price = float(df['Close'].iloc[-1])
                    prev = float(df['Close'].iloc[-2]) if len(df) > 1 else price
                    change_pct = (price - prev) / prev * 100
                    
                    # Regime/Vol (Simplified for snapshot if not in deep analysis)
                    sma20 = df['Close'].tail(20).mean()
                    regime = "Uptrend" if price > sma20 else "Downtrend"
                    
                    # Volatility 30d
                    rets = df['Close'].pct_change().tail(30).dropna()
                    vol = rets.std() * np.sqrt(252) * 100
                    risk = "Moderate"
                    if vol > 30: risk = "High Volatility"
                    elif vol < 12: risk = "Low Volatility"
                    
                    full_snapshot.append({
                        "symbol": sym,
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                        "regime": regime,
                        "risk_label": risk,
                        "risk_label": risk,
                        "volatility_outlook": "Stable" if risk == "Low Volatility" else "Unstable",
                        "forecasts": forecast_map.get(sym, {}) # Inject trained forecasts
                    })
                except: pass
                
            get_db().save_market_overview({"overview": full_snapshot})
            print(f"[DB] Saved Analytics Snapshot ({len(full_snapshot)} symbols).")
            
            # Generate Text Table
            overview_table = generate_overview_table(full_snapshot, forecast_map)
            full_report += "\n\n" + overview_table
            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")

        # Save Report
        report_file = REPORT_DIR / f"daily_report_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(report_file, "w", encoding='utf-8') as f:
            f.write(full_report)
            
        print(full_report)
        print(f"\nReport saved to: {report_file}")
        
        # --- NEW: Save Compact Rational Summary ---
        try:
            from src.core.database import get_db
            
            # Let's check VIX and Credit Spread from Loader
            vix_val = 0.0
            credit_spread_val = 1.0
            
            # Try to get VIX
            try:
                vix_df = loader.get_data("^VIX") # or settings.TIER_1 ...
                if not vix_df.empty:
                    vix_val = float(vix_df['Close'].iloc[-1])
            except: pass
            
            # Try to get Credit Spread (HYG/LQD)
            try:
                hyg = loader.get_data("HYG")
                lqd = loader.get_data("LQD")
                if not hyg.empty and not lqd.empty:
                    credit_spread_val = float(hyg['Close'].iloc[-1] / lqd['Close'].iloc[-1])
            except: pass

            market_summary = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "vix": vix_val,
                "credit_spread": credit_spread_val,
                "regime": market_stats['regime'], 
                "model_confidence": market_stats['model_confidence'],
                "forecast_spy": market_stats['forecast_spy']
            }
            
            get_db().save_market_summary(market_summary)
            print("[DB] Market Summary Saved.")
            
        except Exception as e:
            logger.error(f"Failed to save market summary: {e}")

            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            
        # Snapshot logic moved up to be included in report. Removed duplicate block.
            
        # Cleanup Old Reports
        cleanup_reports(14)
        
        # --- RESET DEEP TRAINING FLAG ---
        if deep_training_flag:
            logger.info("Deep Training Run Complete. Resetting flag.")
            db.set_config("ALLOW_DEEP_TRAINING", "false")
        
        # --- END RUN ---
        db.end_training_run(run_id, status="success")
        print("=== DAILY AUTOMATION COMPLETE ===")

        
        duration = time.time() - start_time
        monitor.log_heartbeat("DailyAutomation", "success", {
            "targets": str(len(ANALYSIS_CONFIGS)), # rough count from config list
            "updated_symbols": len(watchlist) + 10,
            "source": source
        }, duration)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Daily Run Failed: {e}")
        monitor.log_heartbeat("DailyAutomation", "error", {"error": str(e), "source": source}, duration)

    finally:
        # Ensure Pinger Stops even if error
        stop_ping.set()
        ping_thread.join(timeout=2)

if __name__ == "__main__":
    run_daily_automation()
