import numpy as np
import pandas as pd

import joblib
import os

class AdvancedSimulator:
    def __init__(self, use_cache=True, cache_dir="data/cache/models"):
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fit_regime_params(self, returns: pd.Series, regimes: np.ndarray):
        """
        Fit GARCH parameters for each regime.
        returns: pd.Series of daily returns (e.g. 0.01 for 1%)
        regimes: np.ndarray of regime labels (ints)
        """
        # Scale returns to percentage for numerical stability in GARCH
        scaled_returns = returns * 100.0
        params = {}
        unique_regimes = np.unique(regimes)
        
        for r in unique_regimes:
            # Filter returns for this regime
            # We need to align indices. Assuming regimes is same length/index as returns.
            # If regimes is array, we use boolean indexing.
            rrets = scaled_returns[regimes == r]
            rrets = rrets.dropna()
            
            if len(rrets) < 50:
                # Fallback for insufficient data: use simple stats
                params[r] = {
                    'method': 'simple',
                    'std': rrets.std() / 100.0, # back to decimal
                    'mean': rrets.mean() / 100.0,
                    'jump_lambda': 0.01
                }
                continue

            try:
                # Fit GARCH(1,1) with Student-t errors
                from arch import arch_model
                am = arch_model(rrets, vol='Garch', p=1, o=0, q=1, dist='t')
                res = am.fit(disp='off')
                
                params[r] = {
                    'method': 'garch',
                    'garch_res': res,
                    'omega': res.params['omega'],
                    'alpha': res.params['alpha[1]'],
                    'beta': res.params['beta[1]'],
                    't_df': res.params.get('nu', 6),
                    # Higher jump probability in high vol regimes (usually regime 1 or 2)
                    'jump_lambda': max(0.01, 0.05 if r > 0 else 0.005) 
                }
            except Exception as e:
                print(f"GARCH fit failed for regime {r}: {e}")
                params[r] = {
                    'method': 'simple',
                    'std': rrets.std() / 100.0,
                    'mean': rrets.mean() / 100.0,
                    'jump_lambda': 0.01
                }
        
        return params

    def simulate_paths(self, start_price, start_regime, params, transmat=None, days=730, sims=1000, cap=0.3, seed=None, conservative=False):
        """
        Simulate paths using Regime-Switching GARCH + Jump Diffusion.
        transmat: Transition matrix (n_states x n_states). If None, regime is fixed.
        """
        rng = np.random.default_rng(seed)
        end_prices = np.zeros(sims)
        all_paths = np.zeros((sims, days + 1))
        all_paths[:, 0] = start_price
        
        n_regimes = len(params)
        regimes_list = list(params.keys()) # usually 0, 1, 2...
        
        for s in range(sims):
            price = start_price
            regime = start_regime
            
            # Initialize Volatility
            if params[regime]['method'] == 'garch':
                vol = params[regime]['garch_res'].conditional_volatility[-1] / 100.0
            else:
                vol = params[regime]['std']

            for d in range(1, days + 1):
                # 0. Regime Transition
                if transmat is not None:
                    # Sample next regime based on transition probabilities
                    # transmat[i, j] is prob of going from i to j
                    probs = transmat[regime]
                    regime = rng.choice(n_regimes, p=probs)
                
                p = params[regime]
                
                if p['method'] == 'garch':
                    # 1. Forecast next-day variance
                    vol_pct = vol * 100.0
                    var_pct = p['omega'] + p['alpha'] * (vol_pct**2) + p['beta'] * (vol_pct**2)
                    vol_pct = np.sqrt(var_pct)
                    vol = vol_pct / 100.0
                    
                    # 2. Draw return from Student-t
                    from scipy.stats import t
                    df = max(3, p['t_df'])
                    if conservative:
                        df = max(df, 8)
                        
                    shock_std = t.rvs(df, random_state=rng) / np.sqrt(df/(df-2))
                    ret = shock_std * vol
                    
                else:
                    ret = rng.normal(p['mean'], p['std'])
                
                # 3. Jump Component
                jump_lambda = p['jump_lambda']
                if conservative:
                    jump_lambda *= 0.5
                    
                if rng.random() < jump_lambda:
                    scale = 0.2
                    if conservative:
                        scale = 0.1
                        
                    jump_mag = np.exp(rng.normal(0, scale)) - 1
                    
                    if regime > 0: # Bear/Crash
                        direction = -1 if rng.random() < 0.7 else 1
                    else:
                        direction = 1 if rng.random() < 0.6 else -1
                        
                    jump = direction * jump_mag
                    ret += jump
                
                # 4. Cap / Liquidity Constraint
                current_cap = cap
                if conservative:
                    current_cap = 0.15
                    
                ret = np.clip(ret, -current_cap, current_cap)
                
                price *= (1 + ret)
                all_paths[s, d] = price
                
            end_prices[s] = price
            
        # Calculate Quantiles for specific horizons
        horizons = [10, 30, 100, 365, 547, 730]
        quantiles = {}
        
        for h in horizons:
            if h <= days:
                prices_at_h = all_paths[:, h]
                quantiles[h] = {
                    'p10': np.percentile(prices_at_h, 10),
                    'p50': np.percentile(prices_at_h, 50),
                    'p90': np.percentile(prices_at_h, 90)
                }
            
        return {
            'paths': all_paths, # Full paths
            'quantiles': quantiles
        }

    def block_bootstrap(self, returns: pd.Series, start_price, days=30, sims=1000, block_size=10, seed=None):
        """
        Empirical Block Bootstrap for microcaps/non-stationary assets.
        """
        rng = np.random.default_rng(seed)
        rvals = returns.values
        n = len(rvals)
        end_prices = np.zeros(sims)
        
        for i in range(sims):
            price = start_price
            days_left = days
            
            while days_left > 0:
                # Pick a random block
                idx = rng.integers(0, n - block_size)
                # Determine length of this block (take full block or remaining days)
                take = min(block_size, days_left)
                
                block_rets = rvals[idx : idx + take]
                
                # Apply returns
                for r in block_rets:
                    price *= (1 + r)
                
                days_left -= take
                
            end_prices[i] = price
            
        return {
            'final_prices': end_prices,
            'quantiles': {
                'p10': np.percentile(end_prices, 10),
                'p50': np.percentile(end_prices, 50),
                'p90': np.percentile(end_prices, 90)
            }
        }
