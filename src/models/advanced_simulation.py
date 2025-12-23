import numpy as np
import pandas as pd
from arch import arch_model
from scipy.stats import t, norm
import joblib
import os

# New Version 3 Simulation Engines
try:
    from src.sim.vectorized_sim import vectorized_simulate
except ImportError:
    vectorized_simulate = None

try:
    from src.sim.numba_sim import numba_simulate_wrapper
except ImportError:
    numba_simulate_wrapper = None
    
try:
    from src.sim.torch_sim import torch_simulate
except ImportError:
    torch_simulate = None

class AdvancedSimulator:
    def __init__(self, use_cache=True, cache_dir="data/cache/models"):
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fit_regime_params(self, returns: pd.Series, regimes: np.ndarray, n_regimes: int = None):
        """
        Fit GARCH parameters for each regime.
        returns: pd.Series of daily returns (e.g. 0.01 for 1%)
        regimes: np.ndarray of regime labels (ints)
        n_regimes: Optional total number of regimes to ensure params for all states.
        """
        # Scale returns to percentage for numerical stability in GARCH
        scaled_returns = returns * 100.0
        params = {}
        unique_regimes = np.unique(regimes)
        
        # If n_regimes is provided, ensure we cover all 0..n-1
        regome_iter = range(n_regimes) if n_regimes is not None else unique_regimes
        
        # Calculate global stats for fallback
        global_std = scaled_returns.std() / 100.0
        global_mean = scaled_returns.mean() / 100.0
        
        # Bug 12: Fit Global GARCH for fallback
        global_params = None
        try:
            gam = arch_model(scaled_returns, vol='Garch', p=1, o=0, q=1, dist='t')
            gres = gam.fit(disp='off')
            if gres.convergence_flag == 0 and not np.isnan(gres.params.values).any():
                global_params = {
                    'method': 'garch',
                    'garch_res': gres,
                    'omega': gres.params['omega'],
                    'alpha': gres.params['alpha[1]'],
                    'beta': gres.params['beta[1]'],
                    't_df': gres.params.get('nu', 6),
                    'jump_lambda': 0.015, # Average
                    'last_resid': gres.resid.iloc[-1],
                    'long_term_vol': np.sqrt(gres.params['omega'] / (1.0 - gres.params['alpha[1]'] - gres.params['beta[1]'])) / 100.0,
                    'regime_type': 'Global'
                }
        except:
            pass

        for r in regome_iter:
            # Filter returns for this regime
            rrets = scaled_returns[regimes == r]
            rrets = rrets.dropna()
            
            if len(rrets) > 0:
                pass
            
            if len(rrets) < 50:
                # Bug 12 Fix: Use Global GARCH fallback if available
                if global_params:
                    params[r] = global_params.copy()
                    # Keep regime-specific 'regime_type' logic later? 
                    # We will re-label later, so just mark it.
                    params[r]['note'] = 'global_fallback'
                    continue
                
                # Fallback for insufficient data: use simple stats
                # Fallback for insufficient data: use simple stats
                # If r is not in unique_regimes (e.g. unseen state), use global stats
                if len(rrets) == 0:
                    curr_std = global_std
                    curr_mean = global_mean
                else:
                    curr_std = rrets.std() / 100.0
                    curr_mean = rrets.mean() / 100.0
                    
                params[r] = {
                    'method': 'simple',
                    'std': curr_std,
                    'mean': curr_mean,
                    'long_term_vol': curr_std, # Simple regime long run vol is std
                    'jump_lambda': 0.01
                }
                continue

            try:
                # Fit GARCH(1,1) with Student-t errors
                am = arch_model(rrets, vol='Garch', p=1, o=0, q=1, dist='t')
                res = am.fit(disp='off')
                
                # Check for convergence or NaN values
                # convergence_flag: 0 means converged
                if res.convergence_flag != 0 or np.isnan(res.params.values).any():
                    print(f"GARCH non-convergence for regime {r} (flag={res.convergence_flag}). Using fallback.")
                    raise ValueError("GARCH convergence failed")

                params[r] = {
                    'method': 'garch',
                    'garch_res': res,
                    'omega': res.params['omega'],
                    'alpha': res.params['alpha[1]'],
                    'beta': res.params['beta[1]'],
                    't_df': res.params.get('nu', 6),
                    # Higher jump probability in high vol regimes (usually regime 1 or 2)
                    'jump_lambda': max(0.01, 0.05 if r > 0 else 0.005),
                    # Store last residual for simulation continuity
                    'last_resid': res.resid.iloc[-1],
                    # Calculate Long-Run Volatility: sqrt(omega / (1 - alpha - beta))
                    'long_term_vol': np.sqrt(res.params['omega'] / (1.0 - res.params['alpha[1]'] - res.params['beta[1]'])) / 100.0
                }
            except Exception as e:
                # print(f"GARCH fit failed or unstable for regime {r}: {e}")
                
                # Bug 12 Fix: Use Global Fallback
                if global_params:
                    params[r] = global_params.copy()
                    params[r]['note'] = 'global_fallback'
                else:
                    params[r] = {
                        'method': 'simple',
                        'std': rrets.std() / 100.0,
                        'mean': rrets.mean() / 100.0,
                        'long_term_vol': rrets.std() / 100.0,
                        'jump_lambda': 0.01
                    }
        
        # Post-process: Classify Regimes by Volatility
        # Sort regimes by long_term_vol
        for x in params:
             print(f"DEBUG: Regime {x} Vol: {params[x]['long_term_vol']}")
        
        sorted_regimes = sorted(params.keys(), key=lambda x: params[x]['long_term_vol'])
        print(f"DEBUG: Sorted: {sorted_regimes}")
        
        n = len(sorted_regimes)
        for i, r in enumerate(sorted_regimes):
            if i == 0:
                params[r]['regime_type'] = 'Bull'
                params[r]['jump_lambda'] = 0.005 # Low jump prob
            elif i == n - 1:
                params[r]['regime_type'] = 'Bear'
                params[r]['jump_lambda'] = 0.05 # High jump prob
            else:
                params[r]['regime_type'] = 'Transition'
                params[r]['jump_lambda'] = 0.02

        return params

    def simulate_paths(self, start_price, start_regime, params, transmat=None, days=730, sims=1000, cap=0.3, seed=None, conservative=False, engine='legacy', daily_drift=None):
        """
        Simulate paths using Regime-Switching GARCH + Jump Diffusion.
        transmat: Transition matrix (n_states x n_states). If None, regime is fixed.
        engine: 'legacy' (default), 'numpy', 'numba', 'torch'
        """
        # Dispatch to Version 3 Engines
        if engine == 'numpy' and vectorized_simulate:
            return vectorized_simulate(start_price, start_regime, params, transmat, days, sims, conservative, seed, daily_drift=daily_drift)
        elif engine == 'numba' and numba_simulate_wrapper:
            return numba_simulate_wrapper(start_price, start_regime, params, transmat, days, sims, conservative, seed)
        elif engine == 'torch' and torch_simulate:
            return torch_simulate(start_price, start_regime, params, transmat, days, sims, conservative)
        
        # Legacy Python loop implementation ("v1/v2")

        rng = np.random.default_rng(seed)
        end_prices = np.zeros(sims, dtype=np.float64)
        all_paths = np.zeros((sims, days + 1), dtype=np.float64)
        all_paths[:, 0] = float(start_price)
        
        n_regimes = len(params)
        if transmat is not None:
             n_regimes = transmat.shape[0]
        
        for s in range(sims):
            price = start_price
            regime = start_regime
            prev_regime = regime
            
            # Initialize Volatility and Shock
            if params[regime]['method'] == 'garch':
                # Initial vol from the last observation of the fitted model
                vol = params[regime]['garch_res'].conditional_volatility.iloc[-1] / 100.0
                # Initial shock from the last observation
                prev_shock_pct = params[regime].get('last_resid', 0.0)
            else:
                vol = params[regime]['std']
                prev_shock_pct = 0.0

            for d in range(1, days + 1):
                # 0. Regime Transition
                if transmat is not None:
                    probs = transmat[regime]
                    # Normalize probs just in case
                    probs = probs / probs.sum()
                    regime = rng.choice(n_regimes, p=probs)
                
                # Check for regime switch
                if regime != prev_regime:
                    # Reset volatility to long-term average of new regime
                    # params must have the regime key. If fit with n_regimes, it should.
                    if regime in params:
                        vol = params[regime]['long_term_vol']
                    else:
                        # Fallback if params missing (shouldn't happen if initialized right)
                        vol = params[0]['long_term_vol']
                    
                    prev_regime = regime

                p = params.get(regime, params[0]) # Safe fallback
                
                if p['method'] == 'garch':
                    # 1. Forecast next-day variance
                    vol_pct = vol * 100.0
                    # Correct GARCH recursion: omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2
                    var_pct = p['omega'] + p['alpha'] * (prev_shock_pct**2) + p['beta'] * (vol_pct**2)
                    vol_pct = np.sqrt(var_pct)
                    vol = vol_pct / 100.0
                    
                    # 2. Draw return from Student-t
                    df = max(3, p['t_df'])
                    if conservative:
                        df = max(df, 8)
                        
                    # Standardized t-distribution shock
                    shock_std = t.rvs(df, random_state=rng) / np.sqrt(df/(df-2))
                    ret = shock_std * vol
                    
                    # Update previous shock for next step
                    prev_shock_pct = ret * 100.0
                    
                    # Add ML Drift if provided
                    if daily_drift is not None:
                        ret += daily_drift

                else:
                    # Use ML Drift if provided, else Historical Mean
                    mu = daily_drift if daily_drift is not None else p['mean']
                    ret = rng.normal(mu, p['std'])
                    # For simple regime, shock is return minus mean (approx)
                    prev_shock_pct = (ret - p['mean']) * 100.0
                
                # 3. Jump Component
                jump_lambda = p['jump_lambda']
                if conservative:
                    jump_lambda *= 0.5
                    
                if rng.random() < jump_lambda:
                    # Bug 5 Fix: Reduced scale from 0.2 to 0.04 (4% std for jumps)
                    scale = 0.04 
                    if conservative:
                        scale = 0.02
                        
                    # Heavy-tailed jump magnitude (Lognormal-ish)
                    # exp(N(0, 0.04)) - 1 is approx centered at 0 with small skew.
                    # This gives jumps ~ +4% to +8% typically.
                    jump_mag = np.exp(rng.normal(0, scale)) - 1
                    
                    # Bug 6 Fix: Use regime_type for direction logic
                    # Bear -> Negative bias
                    # Bull -> Positive bias (or mixed)
                    rtype = p.get('regime_type', 'Transition')
                    
                    if rtype == 'Bear':
                        # Mostly down jumps
                        direction = -1 if rng.random() < 0.8 else 1 
                    elif rtype == 'Bull':
                        # Mostly up jumps
                        direction = 1 if rng.random() < 0.7 else -1
                    else:
                        # Mixed
                        direction = 1 if rng.random() < 0.5 else -1
                        
                    jump = direction * jump_mag
                    ret += jump
                
                # 4. Cap / Liquidity Constraint
                # Bug 11 Fix: Soft Liquidity Cap (Tanh)
                # Maps (-inf, inf) -> (-limit, limit)
                # limit = 0.50 (50%) allows crashes but prevents explosion
                liq_limit = 0.50
                if conservative:
                    liq_limit = 0.25
                
                ret = liq_limit * np.tanh(ret / liq_limit)
                
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
                    'p10': float(np.percentile(prices_at_h, 10)),
                    'p50': float(np.percentile(prices_at_h, 50)),
                    'p90': float(np.percentile(prices_at_h, 90))
                }
            
        return {
            'paths': all_paths, 
            'quantiles': quantiles
        }

    def block_bootstrap(self, returns: pd.Series, start_price, days=30, sims=1000, block_size=10, seed=None):
        """
        Empirical Block Bootstrap for microcaps/non-stationary assets.
        Returns full paths for visualization.
        """
        rng = np.random.default_rng(seed)
        rvals = returns.values
        n = len(rvals)
        # Store full paths: (sims, days + 1)
        all_paths = np.zeros((sims, days + 1), dtype=np.float64)
        all_paths[:, 0] = float(start_price)
        
        # Pre-allocate for performance
        end_prices = np.zeros(sims)
        
        for i in range(sims):
            price = start_price
            days_filled = 0
            
            while days_filled < days:
                # Pick a random block
                if n <= block_size:
                    idx = 0
                    take = min(n, days - days_filled)
                else:
                    idx = rng.integers(0, n - block_size)
                    take = min(block_size, days - days_filled)
                
                block_rets = rvals[idx : idx + take]
                
                # Apply returns
                for r in block_rets:
                    price *= (1 + r)
                    days_filled += 1
                    all_paths[i, days_filled] = price
                
            end_prices[i] = price
            
        # Calculate Quantiles for specific horizons
        horizons = [10, 30, 100, 365, 547, 730]
        quantiles = {}
        
        for h in horizons:
            # If horizon is within the simulated days
            if h <= days:
                prices_at_h = all_paths[:, h]
                quantiles[h] = {
                    'p10': float(np.percentile(prices_at_h, 10)),
                    'p50': float(np.percentile(prices_at_h, 50)),
                    'p90': float(np.percentile(prices_at_h, 90))
                }
            else:
                # Bug 14 Fix: Return last available value if horizon exceeds days
                prices_at_end = all_paths[:, -1]
                quantiles[h] = {
                    'p10': float(np.percentile(prices_at_end, 10)),
                    'p50': float(np.percentile(prices_at_end, 50)),
                    'p90': float(np.percentile(prices_at_end, 90))
                }

        return {
            'paths': all_paths,
            'quantiles': quantiles,
            'method': 'Bootstrap'
        }
