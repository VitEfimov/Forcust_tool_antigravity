import numpy as np
from typing import Dict, Any

class EnsembleModel:
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize Ensemble with weights.
        Default weights:
        - LightGBM: 0.4
        - Transformer: 0.3
        - Regime (HMM Adjustment): 0.1
        - Trend (Kalman Adjustment): 0.1
        - Volatility (GARCH Adjustment): 0.1
        """
        if weights is None:
            self.weights = {
                "lgbm": 0.4,
                "transformer": 0.3,
                "regime": 0.1,
                "trend": 0.1,
                "volatility": 0.1
            }
        else:
            self.weights = weights

    def predict(self, 
                lgbm_pred: float, 
                transformer_pred: float, 
                current_regime: int, 
                trend_slope: float, 
                volatility: float,
                copula_stress: float = 0.0) -> float:
        """
        Combine predictions into a final meta-forecast.
        
        lgbm_pred: Log return from LightGBM
        transformer_pred: Log return from Transformer
        current_regime: 0 (Bear) or 1 (Bull)
        trend_slope: Slope from Kalman Filter
        volatility: Annualized volatility from GARCH
        copula_stress: Stress impact from Copula (e.g., -0.02 for 2% drop)
        """
        
        # Base forecast from ML models
        ml_forecast = (self.weights["lgbm"] * lgbm_pred) + \
                      (self.weights["transformer"] * transformer_pred)
        
        # Adjustments
        regime_adj = 0.0005 if current_regime == 0 else -0.0005
        trend_adj = trend_slope * 0.1 
        vol_factor = 1.0 / (1.0 + volatility)
        
        # Copula Adjustment: Add stress factor directly
        # If copula predicts a crash in correlated assets, this will be negative
        copula_adj = copula_stress * 0.5 # Weight it
        
        final_pred = (ml_forecast + regime_adj + trend_adj + copula_adj) * vol_factor
        
        return final_pred
