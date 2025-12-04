import pandas as pd
import numpy as np
from arch import arch_model
import joblib

class GarchModel:
    def __init__(self, p=1, q=1):
        self.p = p
        self.q = q
        self.model = None
        self.res = None

    def fit(self, returns: pd.Series):
        """
        Fit GARCH(1,1) model to returns.
        """
        # Scale returns to percentage for better convergence
        scaled_returns = returns * 100
        self.model = arch_model(scaled_returns, vol='Garch', p=self.p, q=self.q)
        self.res = self.model.fit(disp='off')

    def predict(self, horizon: int = 10) -> float:
        """
        Predict volatility for the next 'horizon' days.
        Returns annualized volatility estimate.
        """
        if self.res is None:
            raise ValueError("Model not fitted")
        
        forecasts = self.res.forecast(horizon=horizon)
        # Get the variance forecast for the next 'horizon' steps
        var_forecast = forecasts.variance.iloc[-1]
        
        # Average variance over the horizon
        avg_var = var_forecast.mean()
        
        # Convert to daily volatility then annualized
        daily_vol = np.sqrt(avg_var) / 100 # Scale back
        annualized_vol = daily_vol * np.sqrt(252)
        
        return float(annualized_vol)

    def save(self, path: str):
        joblib.dump(self.res, path)

    def load(self, path: str):
        self.res = joblib.load(path)
