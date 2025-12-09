import torch
from torch.distributions import StudentT, Normal
import numpy as np
from typing import Dict, Any

def torch_simulate(
    start_price: float,
    start_regime: int,
    params: Dict[int, Dict[str, Any]],
    transmat: np.ndarray = None,
    days: int = 730,
    sims: int = 100000,
    conservative: bool = False,
    device: str = "cuda"  # "cpu" for no GPU
):
    dev = torch.device(device if torch.cuda.is_available() and device.startswith("cuda") else "cpu")
    sims = int(sims)
    paths = torch.empty((sims, days + 1), device=dev, dtype=torch.float32)
    paths[:, 0] = float(start_price)

    regimes = torch.full((sims,), start_regime, dtype=torch.long, device=dev)
    # Ensure start_regime in params
    vol = torch.full((sims,), params[start_regime].get("long_term_vol", 0.02), device=dev, dtype=torch.float32)
    prev_shock = torch.zeros((sims,), device=dev, dtype=torch.float32)

    # prebuild arrays
    keys = sorted(params.keys())
    long_vols = torch.tensor([params[k].get("long_term_vol", 0.02) for k in keys], device=dev, dtype=torch.float32)
    jump_lambdas = torch.tensor([params[k].get("jump_lambda", 0.01) for k in keys], device=dev, dtype=torch.float32)
    
    for d in range(1, days + 1):
        # transition
        if transmat is not None:
            tm = torch.tensor(transmat, device=dev, dtype=torch.float32)
            # compute next regimes using multinomial sampling approximate
            # For memory reasons do it in chunks if huge, but here we assume it fits
            # Map current regimes to probability vectors
            probs = tm[regimes]
            
            # Weighted sampling
            new = torch.multinomial(probs, 1).squeeze(1)
            regimes = new

            vol = long_vols[regimes]

        ret = torch.zeros(sims, device=dev)
        # process regimes groupwise
        for idx, r in enumerate(keys):
            mask = (regimes == r)
            if mask.any():
                p = params[r]
                if p["method"] == "garch":
                    omega = p["omega"]
                    alpha = p["alpha"]
                    beta = p["beta"]
                    df = max(3, p.get("t_df", 6))
                    vol_pct = vol[mask] * 100.0
                    var_pct = omega + alpha * (prev_shock[mask] ** 2) + beta * (vol_pct ** 2)
                    vol[mask] = torch.sqrt(var_pct) / 100.0
                    student = StudentT(df)
                    shocks = student.sample(vol[mask].shape).to(dev) / torch.sqrt(torch.tensor(df / (df - 2.0), device=dev))
                    ret[mask] = shocks * vol[mask]
                    prev_shock[mask] = ret[mask] * 100.0
                else:
                    mu = p.get("mean", 0.0)
                    sigma = p.get("std", 0.02)
                    normal = Normal(mu, sigma)
                    ret[mask] = normal.sample(ret[mask].shape).to(dev)
                    prev_shock[mask] = (ret[mask] - mu) * 100.0

        # jumps
        lambdas = jump_lambdas[regimes]
        if conservative:
            lambdas *= 0.5
        flags = torch.rand(sims, device=dev) < lambdas
        if flags.any():
            scales = 0.02 if conservative else 0.04
            mags = torch.exp(torch.normal(0, scales, size=(flags.sum().item(),), device=dev)) - 1.0
            flagged_regs = regimes[flags]
            directions = torch.ones_like(mags)
            for i, r in enumerate(keys):
                mask2 = flagged_regs == r
                if mask2.any():
                    rtype = params[r].get("regime_type", "Transition")
                    if rtype == "Bear":
                        # 80% negative
                        rand = torch.rand(mask2.sum().item(), device=dev)
                        directions[mask2] = torch.where(rand < 0.8, torch.tensor(-1.0, device=dev), torch.tensor(1.0, device=dev))
                    elif rtype == "Bull":
                        rand = torch.rand(mask2.sum().item(), device=dev)
                        directions[mask2] = torch.where(rand < 0.7, torch.tensor(1.0, device=dev), torch.tensor(-1.0, device=dev))
                    else:
                        rand = torch.rand(mask2.sum().item(), device=dev)
                        directions[mask2] = torch.where(rand < 0.5, torch.tensor(1.0, device=dev), torch.tensor(-1.0, device=dev))
            ret[flags] += directions * mags

        # soft cap
        limit = 0.25 if conservative else 0.5
        ret = limit * torch.tanh(ret / limit)
        # advance
        paths[:, d] = paths[:, d-1] * (1.0 + ret)

    # move quantiles back to CPU numpy
    horizons = [10, 30, 100, 365, 547, 730]
    quant = {}
    for h in horizons:
        if h <= days:
            arr = paths[:, h].cpu().numpy()
            quant[h] = {"p10": float(np.percentile(arr, 10)), "p50": float(np.percentile(arr, 50)), "p90": float(np.percentile(arr, 90))}
        else:
            arr = paths[:, -1].cpu().numpy()
            quant[h] = {"p10": float(np.percentile(arr, 10)), "p50": float(np.percentile(arr, 50)), "p90": float(np.percentile(arr, 90))}

    return {"paths": paths.cpu().numpy(), "quantiles": quant}
