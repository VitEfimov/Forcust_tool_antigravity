from typing import Dict, Any, Tuple
import numpy as np
import math
from scipy.stats import t as student_t

def _rand_student_t(df, size, rng):
    # sample Student-t using SciPy (vectorized)
    return student_t.rvs(df, size=size, random_state=rng)

def vectorized_simulate(
    start_price: float,
    start_regime: int,
    params: Dict[int, Dict[str, Any]],
    transmat: np.ndarray = None,
    days: int = 730,
    sims: int = 20000,
    conservative: bool = False,
    seed: int | None = None,
    daily_drift: float | None = None
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    n_regimes = transmat.shape[0] if transmat is not None else len(params)

    # Pre-allocate arrays
    paths = np.empty((sims, days + 1), dtype=np.float64)
    paths[:, 0] = float(start_price)

    # regime per sim (vector) — start everyone at start_regime
    regimes = np.full(sims, start_regime, dtype=np.int32)

    # vol and prev_shock arrays per sim
    vol = np.full(sims, params[start_regime].get("long_term_vol", 0.02), dtype=np.float64)
    # Safely get last_resid, default to 0.0
    prev_shock = np.full(sims, params[start_regime].get("last_resid", 0.0), dtype=np.float64)

    # precompute regime types array
    regime_types = {k: params[k].get("regime_type", "Transition") for k in params}

    for day in range(1, days + 1):
        # 1) regime transition (vectorized)
        if transmat is not None:
            # For each sim, sample next regime using cumulative distribution trick
            cum = transmat.cumsum(axis=1)
            r = rng.random(sims)
            # find first index j where r <= cum[current_regime, j]
            new_regimes = np.zeros(sims, dtype=np.int32)
            # Iterate through unique current regimes for efficiency
            for cur in np.unique(regimes):
                mask = regimes == cur
                if not np.any(mask):
                    continue
                rows = cum[cur]
                # broadcast: r[mask] compare to rows; find argwhere
                rr = r[mask]
                # vectorized selection via searchsorted on rows
                new_regimes[mask] = np.searchsorted(rows, rr)
            regimes = new_regimes

            # reset vol for sims that switched
            # vectorized mapping from regime -> long_term_vol
            # Important: Ensure keys are 0..N-1 or map correctly. Assuming continuous 0..N-1 for simplicity here.
            long_vols = np.array([params[r]["long_term_vol"] for r in sorted(params.keys())], dtype=np.float64)
            vol = long_vols[regimes]

        # 2) compute GARCH forecast (vectorized per sim using their regime params)
        ret = np.zeros(sims, dtype=np.float64)

        # We'll process regimes by group to avoid Python loops over sims
        for r in np.unique(regimes):
            mask = regimes == r
            if not np.any(mask):
                continue
            
            # Safe Fallback: If r not in params, use 0
            # Ideally params covers all, ensuring fallback in fit logic.
            p = params.get(r, params[0]) 

            if p["method"] == "garch":
                omega = p["omega"]
                alpha = p["alpha"]
                beta = p["beta"]
                df = max(3, p.get("t_df", 6))
                
                # vol_pct and prev_shock for mask
                vol_pct = vol[mask] * 100.0
                var_pct = omega + alpha * (prev_shock[mask] ** 2) + beta * (vol_pct ** 2)
                vol[mask] = np.sqrt(var_pct) / 100.0

                # draw t shocks
                shocks = _rand_student_t(df, size=mask.sum(), rng=rng) / math.sqrt(df / (df - 2))
                ret_seg = shocks * vol[mask]
                
                # Apply Drift
                if daily_drift is not None:
                     ret_seg += daily_drift
                     
                prev_shock[mask] = ret_seg * 100.0
                ret[mask] = ret_seg
            else:
                # simple normal fallback
                mu = daily_drift if daily_drift is not None else p.get("mean", 0.0)
                sigma = p.get("std", 0.02)
                ret_seg = rng.normal(loc=mu, scale=sigma, size=mask.sum())
                prev_shock[mask] = (ret_seg - mu) * 100.0
                ret[mask] = ret_seg

        # 3) jumps (vectorized)
        jump_lambdas = np.array([params[r].get("jump_lambda", 0.01) for r in sorted(params.keys())], dtype=np.float64)
        lambdas = jump_lambdas[regimes]
        if conservative:
            lambdas *= 0.5

        jump_flags = rng.random(sims) < lambdas
        if jump_flags.any():
            scales = np.where(conservative, 0.02, 0.04)
            # magnitude: exp(N(0, scale)) - 1
            mags = np.exp(rng.normal(0, scales, size=jump_flags.sum())) - 1.0
            
            # compute directions by regime_type
            directions = np.ones(jump_flags.sum(), dtype=np.float64)
            flagged_regs = regimes[jump_flags]
            
            # vectorized regime_type mapping
            rtype_arr = np.array([params[r].get("regime_type", "Transition") for r in sorted(params.keys())])
            # map each flagged sim to its regime_type
            flagged_types = rtype_arr[flagged_regs]
            
            directions = np.where(flagged_types == "Bear", np.where(rng.random(flagged_regs.size) < 0.8, -1.0, 1.0),
                                  np.where(flagged_types == "Bull", np.where(rng.random(flagged_regs.size) < 0.7, 1.0, -1.0),
                                           np.where(rng.random(flagged_regs.size) < 0.5, 1.0, -1.0)))
            ret[jump_flags] += directions * mags

        # 4) liquidity soft cap (tanh)
        limit = 0.25 if conservative else 0.50
        ret = limit * np.tanh(ret / limit)

        # 5) advance prices
        paths[:, day] = paths[:, day - 1] * (1.0 + ret)

    # quantiles
    horizons = [10, 30, 100, 365, 547, 730]
    quantiles = {}
    for h in horizons:
        if h <= days:
            quantiles[h] = {
                "p10": float(np.percentile(paths[:, h], 10)),
                "p50": float(np.percentile(paths[:, h], 50)),
                "p90": float(np.percentile(paths[:, h], 90)),
            }
        else:
             # Handle horizon > days
             prices_at_end = paths[:, -1]
             quantiles[h] = {
                "p10": float(np.percentile(prices_at_end, 10)),
                "p50": float(np.percentile(prices_at_end, 50)),
                "p90": float(np.percentile(prices_at_end, 90)),
            }

    return {"paths": paths, "quantiles": quantiles}
