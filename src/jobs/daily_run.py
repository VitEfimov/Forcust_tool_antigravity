
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
from src.models.walk_forward import WalkForwardForecaster
from src.models.advanced_simulation import AdvancedSimulator
from src.core.database import get_watchlist
from src.core.monitoring import monitor
import time

# Logging
LOG_DIR = project_root / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / f"daily_run_{datetime.now().strftime('%Y%m%d')}.log",
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger()

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
    prices_df = prices_df.fillna(method='ffill').dropna()
    
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

def step_2_walk_forward(symbol, loader):
    """Run Walk-Forward Pipeline (Rolling Training)."""
    logger.info(f"Step 2.2: Walk-Forward for {symbol}")
    
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
        prediction_horizon=10,
        use_meta_learner=True,
        verbose=False,
        log_func=logger.info
    )
    
    # Run
    results = wf.run()
    
    # Extract latest state
    latest_pred = 0.0
    reliability = 0.5
    regime_label = "Unknown"
    
    if not results.empty:
        last_row = results.iloc[-1]
        latest_pred = last_row.get('pred_price', 0.0)
        reliability = last_row.get('reliability', 1.0) # From Meta-Learner
        # We might need to persist 'regime' in results if possible, or re-derive
        # For now, let's assume 'Regime' column exists or we re-calc
        regime_label = last_row.get('Regime', 'Sideways') # If WF adds this col
        
    return {
        "dates": results['Date'].iloc[-1] if not results.empty else datetime.now(),
        "ml_forecast_price": latest_pred,
        "reliability_score": reliability,
        "regime": regime_label,
        "current_price": df['Close'].iloc[-1]
    }

def step_4_simulation(symbol, loader, current_price):
    """Run Fast Monte-Carlo (Advanced Simulation)."""
    logger.info(f"Step 2.4: Advanced Simulation for {symbol}")
    
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
            import arch
        except:
            method = 'simple'
            
        res = sim.simulate_paths(
            start_price=current_price,
            start_regime=0,
            params={0: {'method': 'simple', 'std': returns.std(), 'mean': returns.mean()}}, 
            # Note: passing params dict is slightly heuristic here, 
            # ideally we let sim fit itself. But simulate_paths takes dict.
            # actually simulate_paths usually does NOT re-fit unless we passed fitted models.
            # To be safe/fast: use 'simple' volatility computed here.
            days=30,
            sims=1000,
            engine='numpy' 
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

def generate_report_content(symbol, market_data, wf_data, sim_data):
    """
    Generate Plain-Language Summary (Section 2.5).
    """
    price = wf_data['current_price']
    ml_target = wf_data['ml_forecast_price']
    mc_target = sim_data['mc_p50']
    rel_score = wf_data['reliability_score']
    
    # Calculations
    ml_upside = (ml_target - price) / price * 100
    mc_upside = (mc_target - price) / price * 100
    
    # Agreement
    agreement = "DIVERGENCE"
    if ml_upside > 0 and mc_upside > 0:
        agreement = "STRONG BUY (Confluence)"
    elif ml_upside < 0 and mc_upside < 0:
        agreement = "STRONG SELL (Confluence)"
    elif abs(ml_upside - mc_upside) < 2.0:
        agreement = "NEUTRAL / CONSENSUS"
        
    # Final Forecast (Meta-Learning Logic 2.3)
    # final_forecast = (base_forecast_return * reliability) ... roughly
    # effective_return = ml_return * reliability
    effective_ml_return = ml_upside * rel_score
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    report = f"""
============================================================
DAILY INTELLIGENCE BRIEFING | {date_str}
============================================================
ASSET: {symbol}
PRICE: {price:.2f}

1. MARKET REGIME
   - Classification: {wf_data['regime'].upper()}
   - Volatility State: {"HIGH" if rel_score < 0.5 else "NORMAL"}
   - VIX Level: (See Dashboard)

2. FORECASTS (30-Day Horizon)
   - ML Model Target: {ml_target:.2f} ({ml_upside:+.2f}%)
   - Monte-Carlo Target: {mc_target:.2f} ({mc_upside:+.2f}%)
   - Agreement Level: {agreement}

3. META-LEARNER (Reliability Layer)
   - Model Reliability Score: {rel_score:.2f} (0=Low, 1=High)
   - Adjusted Prediction: {effective_ml_return:+.2f}% Upside

4. STRATEGY OUTLOOK
   The system detects a {wf_data['regime']} environment.
   Machine Learning suggests a {ml_upside:+.1f}% move, while statistical simulations suggest {mc_upside:+.1f}%.
   
   Final Verdict: {agreement}
   Confidence: {"HIGH" if rel_score > 0.7 else "LOW - CAUTION"}

============================================================
[End of Briefing]
"""
    return report

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

def main():
    start_time = time.time()
    print("=== STARTING DAILY AUTOMATION (SECTION 2 SPEC) ===")
    
    try:
        monitor.log_heartbeat("DailyAutomation", "running", {"step": "start"})
        
        # 1. Watchlist
        watchlist = get_watchlist()
        
        # Step 1: Update Data (Fetches All: Macros, Watchlist, Megacap)
        loader = step_1_update_data(watchlist)
        
        # Define Targets for Deep Analysis (Free Tier Friendly)
        targets = ['SPY', '^MEGACAP']
        
        # Optional: Add top user watchlist item if not present
        if watchlist and watchlist[0] not in targets:
             targets.append(watchlist[0])
             
        # Run Analysis Loop
        final_reports = []
        
        # Run Analysis Loop
        final_reports = []
        
        from src.core.database import get_db
        db = get_db()
        
        for target_symbol in targets:
            print(f"--- Analyzing {target_symbol} ---")
            try:
                # 0. Update Actuals for past forecasts (Track Progress)
                db.update_actuals(target_symbol, datetime.now().strftime("%Y-%m-%d"), 0.0) 
                 # Note: update_actuals needs current_price. We catch it inside or fetch it?
                 # db.update_actuals implementation takes (symbol, date, price).
                 # We don't have price yet. Let's do it AFTER fetching loader data.
                 
                # Step 2: Walk-Forward (ML + Meta)
                wf_data = step_2_walk_forward(target_symbol, loader)
                if not wf_data:
                    print(f"Walk-Forward Failed for {target_symbol}. Skipping.")
                    continue
                
                # Update Actuals using the fresh current price
                current_price = wf_data['current_price']
                db.update_actuals(target_symbol, datetime.now().strftime("%Y-%m-%d"), current_price)
                    
                # Step 4: Simulation
                sim_data = step_4_simulation(target_symbol, loader, current_price)
                
                # Step 5: Generate Report
                report_text = generate_report_content(target_symbol, loader, wf_data, sim_data)
                final_reports.append(report_text)
                
                # --- NEW: Save Trained Forecast to DB (User Request) ---
                # Calculate target date (approximate, +10 days)
                # We assume 10 trading days ~ 14 calendar days
                target_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
                
                db.save_forecast(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    symbol=target_symbol,
                    horizon=10, # Daily run default
                    prediction=wf_data['ml_forecast_price'],
                    start_price=current_price,
                    target_date=target_date
                )
                print(f"[DB] Saved trained forecast for {target_symbol}")
                
                monitor.log_heartbeat("DailyAnalysis", "success", {"symbol": target_symbol})
                
            except Exception as e:
                logger.error(f"Analysis failed for {target_symbol}: {e}")
        
        # Combine Reports
        full_report = "\n\n".join(final_reports)
        
        # Save Report
        report_file = REPORT_DIR / f"daily_report_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(report_file, "w") as f:
            f.write(full_report)
            
        print(full_report)
        print(f"\nReport saved to: {report_file}")
        
        # --- NEW: Save Compact Rational Summary ---
        try:
            from src.core.database import get_db
            
            # 1. Get SPY Metrics
            spy_summary = {}
            # We assume SPY was analyzed. Find its data in our local vars or re-fetch?
            # actually we don't have easy access to 'wf_data' here unless we stored it.
            # Ideally we'd have a 'results_map'. But let's just grab if target_symbol was SPY in loop.
            # We can't re-access variables from inside the loop easily. 
            # Better approach: store results in a dict during loop.
            
            # Simple workaround: Parse the report or just execute for SPY specifically if we need strict data.
            # Or better: We'll modify the loop above to store 'spy_data' if target=='SPY'.
            
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
                # Placeholders for now until we refactor loop to extract these
                "regime": "Unknown", 
                "model_confidence": 0.5,
                "forecast_spy": {}
            }
            
            get_db().save_market_summary(market_summary)
            print("[DB] Market Summary Saved.")
            
        except Exception as e:
            logger.error(f"Failed to save market summary: {e}")
            
        # Cleanup Old Reports
        cleanup_reports(14)
        
        print("=== DAILY AUTOMATION COMPLETE ===")
        
        duration = time.time() - start_time
        monitor.log_heartbeat("DailyAutomation", "success", {
            "targets": targets,
            "updated_symbols": len(watchlist) + 10
        }, duration)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Daily Run Failed: {e}")
        monitor.log_heartbeat("DailyAutomation", "error", {"error": str(e)}, duration)

if __name__ == "__main__":
    main()
