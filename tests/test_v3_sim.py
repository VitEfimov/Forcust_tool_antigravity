import numpy as np
import pytest
from src.sim.vectorized_sim import vectorized_simulate
try:
    from src.sim.numba_sim import numba_simulate_wrapper
except ImportError:
    numba_simulate_wrapper = None
try:
    from src.sim.torch_sim import torch_simulate
except ImportError:
    torch_simulate = None

from src.models.advanced_simulation import AdvancedSimulator

def make_stub_params():
    # two regimes: 0 bull, 1 bear
    return {
        0: {"method": "garch", "omega": 1e-6, "alpha": 0.05, "beta": 0.92, "t_df": 8, "jump_lambda": 0.01, "long_term_vol": 0.01, "regime_type": "Bull"},
        1: {"method": "garch", "omega": 2e-6, "alpha": 0.07, "beta": 0.90, "t_df": 6, "jump_lambda": 0.03, "long_term_vol": 0.03, "regime_type": "Bear"}
    }

def test_vectorized_runs():
    p = make_stub_params()
    out = vectorized_simulate(100.0, 0, p, transmat=None, days=30, sims=2000, seed=1)
    assert "quantiles" in out and 10 in out["quantiles"]
    assert out["paths"].shape == (2000, 31)

def test_numba_runs():
    if not numba_simulate_wrapper:
        pytest.skip("Numba not available")
    p = make_stub_params()
    arr = np.array([[0.9, 0.1],[0.1,0.9]])
    out = numba_simulate_wrapper(100.0, 0, p, transmat=arr, days=30, sims=200, seed=42)
    assert out["paths"].shape == (200, 31)
    assert "quantiles" in out

def test_torch_runs_cpu():
    if not torch_simulate:
        pytest.skip("Torch not available")
    p = make_stub_params()
    out = torch_simulate(100.0, 0, p, transmat=None, days=30, sims=1000, device="cpu")
    assert "quantiles" in out
    assert out["paths"].shape == (1000, 31)

def test_dispatch_logic():
    sim = AdvancedSimulator()
    p = make_stub_params()
    
    # Test numpy dispatch
    res = sim.simulate_paths(100.0, 0, p, days=10, sims=100, engine='numpy')
    assert res['paths'].shape == (100, 11)
    
    # Test fallback legacy (implicit)
    res2 = sim.simulate_paths(100.0, 0, p, days=10, sims=100, engine='legacy')
    assert res2['paths'].shape == (100, 11)
