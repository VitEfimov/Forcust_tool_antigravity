import pandas as pd
import numpy as np
from copulas.multivariate import GaussianMultivariate
from copulas.univariate import GaussianKDE

class CopulaModel:
    def __init__(self):
        """
        Initialize Gaussian Copula Model.
        """
        self.model = GaussianMultivariate()
        
    def fit(self, data: pd.DataFrame):
        """
        Fit copula to multi-asset returns.
        data: DataFrame where columns are assets and rows are returns.
        """
        self.model.fit(data)
        
    def sample(self, n_samples: int = 1000) -> pd.DataFrame:
        """
        Generate synthetic samples from the learned copula.
        """
        return self.model.sample(n_samples)
    
    def get_correlation_matrix(self) -> pd.DataFrame:
        """
        Get the correlation matrix captured by the copula.
        """
        # GaussianMultivariate doesn't expose correlation directly easily in all versions,
        # but we can sample and compute it.
        samples = self.sample(1000)
        return samples.corr()

    def stress_test(self, shock_asset: str, shock_value: float, n_samples: int = 1000) -> pd.DataFrame:
        """
        Simulate conditional scenarios (e.g., if SPY drops 5%, what happens to others?)
        This is a simplified approach using sampling and filtering.
        """
        samples = self.sample(n_samples * 10) # Generate more to filter
        
        # Filter for samples close to the shock value (e.g., within 10%)
        tolerance = abs(shock_value) * 0.1
        condition = (samples[shock_asset] >= shock_value - tolerance) & \
                    (samples[shock_asset] <= shock_value + tolerance)
        
        conditional_samples = samples[condition]
        return conditional_samples.mean()
