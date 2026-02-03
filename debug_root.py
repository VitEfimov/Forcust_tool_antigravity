import sys
import os
import pandas as pd
import numpy as np

# Root is current dir
sys.path.append(os.getcwd())

from src.data.loader import DataLoader
from src.core.config import settings

def debug_spce():
    print("--- Debugging SPCE (Root) ---")
    
    loader = DataLoader(settings.DATA_CACHE_DIR)
    
    # 1. Fetch Data
    print("Fetching SPCE data...")
    try:
        df = loader.get_data("SPCE", start_date="2015-01-01")
        print(f"SPCE Data: {len(df)} rows")
        if df.empty:
            print("ERROR: DataFrame is empty!")
            return
            
        print("Last Row:")
        print(df.tail(1))
        
        returns = df['Close'].pct_change().dropna()
        print(f"Returns: {len(returns)} rows")
        
    except Exception as e:
        print(f"Exception fetching data: {e}")
        return

    # 2. Test Advanced Sim Logic (Partial)
    print("\n--- Testing HMM/Sim Logic ---")
    try:
        from src.models.advanced_simulation import AdvancedSimulator
        from src.models.hmm import RegimeDetector
        
        sim = AdvancedSimulator()
        hmm = RegimeDetector()
        
        print("Fitting HMM...")
        hmm.fit(returns)
        regimes = hmm.predict(returns)
        print(f"HMM Regimes: {np.unique(regimes)}")
        
        print("Fitting Params...")
        transmat = hmm.model.transmat_
        params = sim.fit_regime_params(returns, regimes, n_regimes=transmat.shape[0])
        print("Params fitted.")
        
        print("Running Simulation (2000 sims)...")
        # Run small scale
        current_price = df['Close'].iloc[-1]
        sim_res = sim.simulate_paths(
            start_price=current_price,
            start_regime=int(regimes[-1]),
            params=params,
            transmat=transmat,
            days=730, # Full run
            sims=500, # Tier 3 scale
            conservative=False,
            engine='ensemble'
        )
        print("Sim Results keys:", sim_res.keys())
        print("Quantiles:", sim_res.get('quantiles', {}).keys())
        
    except Exception as e:
        print(f"ERROR in Simulation Logic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_spce()
