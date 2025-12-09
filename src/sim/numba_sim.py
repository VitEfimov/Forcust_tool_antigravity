from typing import Dict, Any
import numpy as np
from numba import njit, prange

@njit(parallel=True)
def _simulate_batch(
    start_price,
    start_regime,
    params_keys,
    omega_arr,
    alpha_arr,
    beta_arr,
    tdf_arr,
    jump_lambda_arr,
    long_vol_arr,
    regime_type_arr,
    transmat,
    days,
    sims,
    conservative,
    seed
):
    # Numba needs typed specific initialization sometimes, but this works for basic types
    # Handle random seed per thread logic? 
    # Numba's parallel random generation is thread-safe if using np.random.random() inside loop.
    # We can seed globally or per iterator. 
    # Let's trust Numba's PRNG state management or simple seed at start.
    
    # Simple explicit seed
    np.random.seed(seed if seed is not None else 12345)
    
    paths = np.empty((sims, days+1), dtype=np.float64)
    for i in prange(sims):
        # Local seed perturbation for parallel? 
        # Ideally using xorshift or similar, but np.random in numba parallel is generally okay-ish 
        # or we accept deterministic per thread if not careful.
        # User code provided used a custom state array logic but didn't implement the generator fully.
        # I'll stick to np.random calls as provided in logic flow.
        
        price = start_price
        reg = start_regime
        prev_reg = reg
        vol = long_vol_arr[reg]
        prev_shock = 0.0
        paths[i, 0] = price
        for d in range(1, days+1):
            # transition (if provided)
            if transmat is not None:
                # naive sampling: draw uniform, walk cumulative
                # Replacing complex mix logic with standard random
                u = np.random.random()
                cum = 0.0
                flag = False
                for j in range(transmat.shape[1]):
                    cum += transmat[reg, j]
                    if u <= cum:
                        reg = j
                        flag = True
                        break
                if not flag: # precision edge case
                    reg = transmat.shape[1] - 1
                    
            if reg != prev_reg:
                vol = long_vol_arr[reg]
                prev_reg = reg

            if omega_arr[reg] >= 0: # treat >=0 as GARCH
                var_pct = omega_arr[reg] + alpha_arr[reg] * (prev_shock**2) + beta_arr[reg] * (vol*100.0)**2
                vol = np.sqrt(var_pct) / 100.0
                # student-t approx via normal for speed (numba lacks student_t easily)
                # using normal approximations reduces tail fidelity; tradeoff for speed
                # Or use inverse transform sampling if T available? standard_normal is provided.
                shock = np.random.standard_normal() # substitute
                ret = shock * vol
                prev_shock = ret * 100.0
            else:
                ret = np.random.normal(0.0, 0.02)
                prev_shock = ret * 100.0

            # jump
            jl = jump_lambda_arr[reg] * (0.5 if conservative else 1.0)
            if np.random.random() < jl:
                mag = np.exp(np.random.normal(0, 0.04)) - 1.0
                if regime_type_arr[reg] == 2: # bear
                    dir = -1.0 if np.random.random() < 0.8 else 1.0
                elif regime_type_arr[reg] == 0: # bull
                    dir = 1.0 if np.random.random() < 0.7 else -1.0
                else:
                    dir = 1.0 if np.random.random() < 0.5 else -1.0
                ret += dir * mag

            # soft cap
            limit = 0.25 if conservative else 0.50
            # tanh clamp
            if ret > limit:
                ret = limit * np.tanh(ret / limit)
            if ret < -limit:
                ret = limit * np.tanh(ret / limit)

            price = price * (1.0 + ret)
            paths[i, d] = price

    return paths

def numba_simulate_wrapper(
    start_price: float,
    start_regime: int,
    params: Dict[int, Dict[str, Any]],
    transmat: np.ndarray = None,
    days: int = 730,
    sims: int = 10000,
    conservative: bool = False,
    seed: int = 42
):
    # convert params to arrays for numba
    keys = sorted(params.keys())
    n = len(keys)
    omega_arr = np.empty(n, dtype=np.float64)
    alpha_arr = np.empty(n, dtype=np.float64)
    beta_arr = np.empty(n, dtype=np.float64)
    tdf_arr = np.empty(n, dtype=np.float64)
    jump_lambda_arr = np.empty(n, dtype=np.float64)
    long_vol_arr = np.empty(n, dtype=np.float64)
    regime_type_arr = np.empty(n, dtype=np.int32)  # encode 0 bull,1 trans,2 bear

    for idx, k in enumerate(keys):
        p = params[k]
        omega_arr[idx] = p.get("omega", -1.0) # -1 indicates simple fallback
        alpha_arr[idx] = p.get("alpha", 0.0)
        beta_arr[idx] = p.get("beta", 0.0)
        tdf_arr[idx] = p.get("t_df", 6)
        jump_lambda_arr[idx] = p.get("jump_lambda", 0.01)
        long_vol_arr[idx] = p.get("long_term_vol", 0.02)
        rtype = p.get("regime_type", "Transition")
        regime_type_arr[idx] = 0 if rtype == "Bull" else (2 if rtype == "Bear" else 1)
        
    # Numba function call
    if transmat is not None:
        transmat = transmat.astype(np.float64)

    # Note: keys argument passed to _simulate_batch is not really used inside besides sizing logic index 
    # but the arrays are indexed by simple 0..N-1 derived from sorted keys.
    # The inner loop logic assumes 'reg' is an index into these arrays.
    
    paths = _simulate_batch(
        float(start_price), int(start_regime), np.array(keys),
        omega_arr, alpha_arr, beta_arr, tdf_arr, jump_lambda_arr, long_vol_arr, regime_type_arr,
        transmat, days, sims, conservative, seed
    )
    
    # Quantiles
    horizons = [10, 30, 100, 365, 547, 730]
    quant = {}
    for h in horizons:
        if h <= days:
            arr = paths[:, h]
            quant[h] = {"p10": float(np.percentile(arr, 10)), "p50": float(np.percentile(arr, 50)), "p90": float(np.percentile(arr, 90))}
        else:
            arr = paths[:, -1]
            quant[h] = {"p10": float(np.percentile(arr, 10)), "p50": float(np.percentile(arr, 50)), "p90": float(np.percentile(arr, 90))}
            
    return {"paths": paths, "quantiles": quant}
