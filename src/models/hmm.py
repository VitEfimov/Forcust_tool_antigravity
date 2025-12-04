import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import joblib
import os

class RegimeDetector:
    def __init__(self, n_components: int = 2, n_iter: int = 100):
        self.n_components = n_components
        self.model = GaussianHMM(n_components=n_components, covariance_type="full", n_iter=n_iter, random_state=42)
        self.is_fitted = False

    def fit(self, returns: pd.Series):
        """
        Fit HMM on returns.
        Reshapes data to (n_samples, 1).
        """
        X = returns.values.reshape(-1, 1)
        # Handle NaNs/Infs
        mask = np.isfinite(X).all(axis=1)
        X_clean = X[mask]
        
        self.model.fit(X_clean)
        self.is_fitted = True
        
        # Sort states by mean return (or volatility) to make them interpretable
        # Let's sort by variance (volatility) - State 0 = Low Vol, State 1 = High Vol
        # Or mean return. Let's stick to variance for "Regime".
        # Actually, let's just keep it as is for now, but we could reorder.
        
    def predict(self, returns: pd.Series) -> np.ndarray:
        """
        Predict states for the given returns.
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted")
            
        X = returns.values.reshape(-1, 1)
        # Fill NaNs with 0 or drop? HMM doesn't like NaNs.
        # For prediction, we need to match indices.
        # We'll forward fill or fill 0.
        X = np.nan_to_num(X)
        
        return self.model.predict(X)

    def predict_proba(self, returns: pd.Series) -> np.ndarray:
        """
        Predict state probabilities.
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted")
            
        X = returns.values.reshape(-1, 1)
        X = np.nan_to_num(X)
        return self.model.predict_proba(X)

    def save(self, path: str):
        joblib.dump(self.model, path)

    def load(self, path: str):
        self.model = joblib.load(path)
        self.is_fitted = True
