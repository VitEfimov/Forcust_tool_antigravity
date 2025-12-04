import numpy as np
import pandas as pd

class Simulator:
    def __init__(self, n_sims: int = 1000, horizon: int = 5):
        self.n_sims = n_sims
        self.horizon = horizon

    def simulate(self, current_price: float, expected_return: float, volatility: float) -> dict:
        """
        Simple geometric brownian motion simulation for now.
        Can be enhanced to use HMM states later.
        """
        dt = 1/252 # Daily step
        
        # Paths: (n_sims, horizon)
        # S_t = S_{t-1} * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
        
        # We treat expected_return as daily return for simplicity here, 
        # but usually it's annualized. Let's assume the input is the *daily* expected log return.
        mu = expected_return
        sigma = volatility
        
        paths = np.zeros((self.n_sims, self.horizon + 1))
        paths[:, 0] = current_price
        
        # Vectorized Simulation
        # Generate all random returns at once: (n_sims, horizon)
        # r ~ N(mu, sigma)
        # Note: mu is daily expected log return.
        
        # We assume mu is constant over the horizon for this simple simulation,
        # or we could decay it. For now, constant.
        
        # Adjust mu to be daily: input expected_return is total log return for horizon?
        # Wait, in routes.py we pass `sim_return` which is `final_log_return` (total for horizon).
        # So daily_mu = expected_return / horizon.
        
        daily_mu = expected_return / self.horizon
        
        # Generate random shocks
        # shape: (n_sims, horizon)
        shocks = np.random.normal(daily_mu, volatility, (self.n_sims, self.horizon))
        
        # Cumulative sum of log returns
        cum_log_returns = np.cumsum(shocks, axis=1)
        
        # Calculate prices
        # paths[:, 1:] = current_price * exp(cum_log_returns)
        # We only strictly need the final prices for quantiles, but paths are good for charts if needed.
        # For speed, we can just calculate final prices if we don't need intermediate paths.
        # But let's keep paths structure for now, just vectorized.
        
        paths = np.zeros((self.n_sims, self.horizon + 1))
        paths[:, 0] = current_price
        paths[:, 1:] = current_price * np.exp(cum_log_returns)
            
        # Calculate quantiles
        final_prices = paths[:, -1]
        quantiles = {
            'p10': float(np.percentile(final_prices, 10)),
            'p50': float(np.percentile(final_prices, 50)),
            'p90': float(np.percentile(final_prices, 90))
        }
        
        return {
            'paths': paths.tolist(), # Be careful with size if sending to frontend
            'quantiles': quantiles
        }
