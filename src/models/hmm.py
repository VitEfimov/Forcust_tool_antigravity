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
        
        # Identify states based on Volatility (Variance)
        # self.model.covars_ is shape (n_components, 1, 1) for 'full' covariance on 1D data
        variances = np.array([self.model.covars_[i][0][0] for i in range(self.n_components)])
        means = np.array([self.model.means_[i][0] for i in range(self.n_components)])
        
        # Sort indices by variance: 0=Low Vol, 1=Med, 2=High
        self.sorted_indices = np.argsort(variances)
        
    def get_regime_label(self, state_idx: int) -> str:
        """
        Return a human-readable label for the state.
        Assumes 3 components:
        0 (Lowest Vol) -> "Bull Market (Low Vol)"
        1 (Med Vol) -> "Transition / Recovery"
        2 (Highest Vol) -> "Bear / Crash (High Vol)"
        """
        if not self.is_fitted:
            return "Unknown"
            
        # Map the raw state_idx to its rank in volatility
        # sorted_indices[0] is the index of the lowest volatility state
        # We need to find where state_idx is in sorted_indices
        
        # If state_idx == sorted_indices[0] -> Rank 0 (Low Vol)
        # If state_idx == sorted_indices[-1] -> Rank N (High Vol)
        
        rank = np.where(self.sorted_indices == state_idx)[0][0]
        
        if self.n_components == 2:
            if rank == 0: return "Bull Market (Low Vol)"
            return "Bear Market (High Vol)"
            
        elif self.n_components == 3:
            if rank == 0: return "Bull Market (Low Vol)"
            if rank == 1: return "Transition / Recovery"
            return "Bear / Crash (High Vol)"
            
        else:
            if rank == 0: return "Low Volatility"
            if rank == self.n_components - 1: return "High Volatility / Crash"
            return "Transitional"

    def predict(self, returns: pd.Series) -> np.ndarray:
        """
        Predict states for the given returns.
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted")
            
        X = returns.values.reshape(-1, 1)
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
        joblib.dump({'model': self.model, 'sorted_indices': getattr(self, 'sorted_indices', None)}, path)

    def load(self, path: str):
        data = joblib.load(path)
        if isinstance(data, dict):
            self.model = data['model']
            self.sorted_indices = data.get('sorted_indices')
        else:
            self.model = data # Legacy support
            # Re-infer sorted indices if missing (not ideal but fallback)
            variances = np.array([self.model.covars_[i][0][0] for i in range(self.model.n_components)])
            self.sorted_indices = np.argsort(variances)
            
        self.is_fitted = True
