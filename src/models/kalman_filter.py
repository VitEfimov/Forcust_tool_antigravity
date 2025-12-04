import numpy as np
import pandas as pd
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

class KalmanTrend:
    def __init__(self, dim_x=2, dim_z=1):
        """
        Initialize Kalman Filter for trend tracking.
        State: [position, velocity]
        """
        self.kf = KalmanFilter(dim_x=dim_x, dim_z=dim_z)
        
        # State Transition Matrix (Constant Velocity Model)
        # x_t = x_{t-1} + v_{t-1} * dt
        # v_t = v_{t-1}
        self.kf.F = np.array([[1., 1.],
                              [0., 1.]])
        
        # Measurement Function
        # z_t = x_t
        self.kf.H = np.array([[1., 0.]])
        
        # Measurement Noise (R) - Estimate from data variance
        self.kf.R = np.array([[10.]]) 
        
        # Process Noise (Q)
        self.kf.Q = Q_discrete_white_noise(dim=dim_x, dt=1., var=0.1)
        
        # Initial State Covariance (P)
        self.kf.P *= 1000.

    def fit_transform(self, prices: pd.Series) -> pd.Series:
        """
        Apply Kalman Filter to smooth the price series.
        """
        # Initialize state with first observation
        self.kf.x = np.array([prices.iloc[0], 0.])
        
        smoothed_prices = []
        
        for z in prices:
            self.kf.predict()
            self.kf.update(z)
            smoothed_prices.append(self.kf.x[0])
            
        return pd.Series(smoothed_prices, index=prices.index)

    def get_current_state(self):
        """
        Return current position (trend price) and velocity (trend slope).
        """
        return {
            "trend_price": float(self.kf.x[0]),
            "trend_slope": float(self.kf.x[1])
        }
