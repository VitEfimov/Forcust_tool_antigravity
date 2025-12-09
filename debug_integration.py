import sys
import os
import pandas as pd
import numpy as np
# Mocking DataLoader/Settings if needed, or just use direct data
from src.models.advanced_simulation import AdvancedSimulator
from src.models.hmm import RegimeDetector

from src.data.loader import DataLoader

def debug_integration():
    print("Starting integration debug (Real Data)...")
    try:
        loader = DataLoader("data/cache")
        df = loader.get_data("SPY")
        returns = df['Close'].pct_change().dropna()
        current_price = df['Close'].iloc[-1]
        
        sim = AdvancedSimulator()
        hmm = RegimeDetector()
        
        print("Fitting HMM...")
        hmm.fit(returns)
        regimes = hmm.predict(returns)
        # Force transmat logic
        hmm_transmat = hmm.model.transmat_
        
        # ... logic continues as before ...
        current_regime = int(regimes[-1])
        transmat = hmm_transmat
        
        print(f"Transmat shape: {transmat.shape}")
        
        print("Fitting params...")
        params = sim.fit_regime_params(returns, regimes, n_regimes=transmat.shape[0])
        
        print(f"Params keys: {params.keys()}")
        print(f"Params[0]: {params.get(0)}")
        
        print("Simulating with engine='numpy'...")
        res = sim.simulate_paths(
            start_price=current_price,
            start_regime=current_regime,
            params=params,
            transmat=transmat,
            days=30,
            sims=100,
            engine='numpy'
        )
        
        print("Simulation success!")
        print("Method:", res.get("method", "Unknown"))
        print("Paths shape:", res["paths"].shape)
        
    except Exception as e:
        print("An error occurred:")
        print(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_integration()
