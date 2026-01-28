
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock paths to allow imports
sys.path.append(os.getcwd())

from src.core.config import settings
from src.data.loader import DataLoader
from src.core.database import get_db

def debug_overview(symbols):
    print(f"--- Debugging {symbols} ---")
    loader = DataLoader(settings.DATA_CACHE_DIR)
    db = get_db()
    
    VALID_HORIZONS = [10, 30, 100, 200, 365]
    BASE_HORIZONS = {10, 100}
    DERIVED_MAP = {30: 10, 200: 100, 365: 100}

    for symbol in symbols:
        print(f"\nProcessing {symbol}:")
        
        # 1. Check DB
        db_forecasts = db.get_history(symbol)
        print(f"  DB Entries found: {len(db_forecasts)}")
        ml_overrides_pct = {}
        for f in db_forecasts:
            h = f.get('horizon')
            print(f"    - Found H={h}, Pred={f.get('prediction')}")
            if h in BASE_HORIZONS:
                start_p = f.get('start_price')
                if f.get('prediction') and start_p:
                     pct = (f.get('prediction') - start_p) / start_p * 100
                     ml_overrides_pct[h] = pct
                     print(f"      -> ACCEPTED Base H={h}: {pct:.2f}%")
        
        # 2. Check Analytical
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        print(f"  Fetching data since {start_date}...")
        df = loader.get_data(symbol, start_date=start_date)
        print(f"  DF Shape: {df.shape}")
        
        drift = np.nan
        if not df.empty:
            returns = df['Close'].pct_change().dropna()
            print(f"  Returns count: {len(returns)}")
            if len(returns) > 0:
                mu = returns.mean()
                sigma = returns.std()
                raw_drift = mu - 0.5 * (sigma ** 2)
                ann_drift = raw_drift * 252
                print(f"  Mu: {mu:.6f}, Sigma: {sigma:.6f}, Ann Drift: {ann_drift:.2%}")
                
                capped_ann_drift = max(-0.20, min(0.30, ann_drift))
                drift = capped_ann_drift / 252
                print(f"  Final Drift (Daily): {drift:.6f}")
            else:
                print("  No returns computed (not enough data?)")
        else:
            print("  DF is EMPTY!")

        # 3. Simulate Logic
        forecasts = {}
        for h in VALID_HORIZONS:
            final_pct = None
            if h in ml_overrides_pct:
                final_pct = ml_overrides_pct[h]
                print(f"  H={h}: Uses ML Override -> {final_pct:.2f}%")
            elif h in DERIVED_MAP:
                base_h = DERIVED_MAP[h]
                if base_h in ml_overrides_pct:
                    base_pct = ml_overrides_pct[base_h]
                    base_log = np.log(1 + base_pct/100)
                    scale = h / base_h
                    derived_log = base_log * scale
                    final_pct = (np.exp(derived_log) - 1) * 100
                    print(f"  H={h}: Derived from base {base_h} -> {final_pct:.2f}%")
            
            if final_pct is None and not np.isnan(drift):
                 decay_factor = 1.0 / (1.0 + (h / 60.0))
                 analytical_log = drift * h * decay_factor
                 final_pct = (np.exp(analytical_log) - 1) * 100
                 print(f"  H={h}: Analytical Fallback -> {final_pct:.2f}%")
            
            if final_pct is None:
                print(f"  H={h}: FAIL (0.00%)")

if __name__ == "__main__":
    debug_overview(["AAPL", "NVDA", "GOOGL"])
