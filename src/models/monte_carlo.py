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
        
        for t in range(1, self.horizon + 1):
            z = np.random.normal(0, 1, self.n_sims)
            # If mu is daily log return, then:
            # P_t = P_{t-1} * exp(mu + sigma * z) ? 
            # Or if mu is drift... let's assume mu is the predicted log return from LightGBM.
            # And sigma is the recent volatility.
            
            # LightGBM predicts E[r_{t+1}].
            # r_{t+1} ~ N(mu, sigma^2)
            r = np.random.normal(mu, sigma, self.n_sims)
            paths[:, t] = paths[:, t-1] * np.exp(r)
            
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
