import sys
import os
sys.path.append(os.getcwd())

import pandas as pd
import numpy as np
from src.data.loader import DataLoader
from src.models.hmm import RegimeDetector
from src.models.advanced_simulation import AdvancedSimulator
from src.core.config import settings

def calibrate(symbol="SPY", days_back=500, horizon=30):
    print(f"--- Calibrating Advanced Simulation for {symbol} ---")
    
    # 1. Load Data
    loader = DataLoader(settings.DATA_CACHE_DIR)
    df = loader.get_data(symbol)
    if df.empty:
        print("No data found.")
        return

    # 2. Setup Backtest
    # We'll do a rolling backtest over the last 'days_back'
    # Step size = 30 days
    
    test_dates = df.index[-days_back::30]
    results = []
    
    simulator = AdvancedSimulator()
    hmm = RegimeDetector()
    
    for date in test_dates:
        # Train on data UP TO this date
        train_df = df[df.index < date]
        if len(train_df) < 500:
            continue
            
        # Realized future price
        try:
            future_idx = df.index.get_loc(date) + horizon
            if future_idx >= len(df):
                continue
            future_price = df.iloc[future_idx]['Close']
        except:
            continue
            
        current_price = train_df.iloc[-1]['Close']
        returns = train_df['Close'].pct_change().dropna()
        
        # Fit HMM
        hmm.fit(returns)
        regimes = hmm.predict(returns)
        current_regime = regimes[-1]
        
        # Fit GARCH params
        params = simulator.fit_regime_params(returns, regimes)
        
        # Simulate
        sim_res = simulator.simulate_paths(
            start_price=current_price,
            start_regime=current_regime,
            params=params,
            days=horizon,
            sims=500
        )
        
        q = sim_res['quantiles']
        
        # Check coverage
        in_band = q['p10'] <= future_price <= q['p90']
        
        results.append({
            'date': date,
            'current': current_price,
            'future': future_price,
            'p10': q['p10'],
            'p50': q['p50'],
            'p90': q['p90'],
            'in_band': in_band
        })
        
        print(f"Date: {date.date()} | Price: {current_price:.2f} -> {future_price:.2f} | P10: {q['p10']:.2f} | P90: {q['p90']:.2f} | Covered: {in_band}")

    # Summary
    df_res = pd.DataFrame(results)
    coverage = df_res['in_band'].mean()
    print("\n--- Calibration Results ---")
    print(f"Horizon: {horizon} days")
    print(f"Samples: {len(df_res)}")
    print(f"Coverage (P10-P90): {coverage:.2%} (Target ~80%)")
    
    if coverage < 0.7:
        print("WARNING: Tails too narrow. Increase volatility or jump lambda.")
    elif coverage > 0.9:
        print("WARNING: Tails too wide. Reduce volatility or jump lambda.")
    else:
        print("SUCCESS: Model is well-calibrated.")

if __name__ == "__main__":
    calibrate()
