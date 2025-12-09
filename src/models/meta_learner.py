
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from typing import Dict, Optional, Tuple, Callable

class MetaLearner:
    """
    Meta-Learning Reliability Module.
    Learns when the base model is likely to fail based on market conditions and recent errors.
    Output: Reliability Score (0.0 to 1.0)
    """
    def __init__(self, lookback_errors: int = 10, verbose: bool = False, log_func: Optional[Callable[[str], None]] = None):
        self.lookback_errors = lookback_errors
        self.verbose = verbose
        self.log_func = log_func if log_func else print
        # Lightweight Random Forest as requested
        self.model = RandomForestRegressor(
            n_estimators=50,
            max_depth=5,
            min_samples_leaf=10,
            n_jobs=-1,
            random_state=42
        )
        self.is_fitted = False
        self.feature_cols = []

    def _compute_meta_features(self, df: pd.DataFrame, prediction_col: str, actual_col: str, error_col: str) -> pd.DataFrame:
        """
        Compute features for the meta-learner:
        1. Volatility (20d, GARCH proxy)
        2. VIX (fear index) - requires external data present in df
        3. Regime (volatility regime)
        4. Recent Forecasting Error (rolling mean)
        5. Market Dependency (Correlation with S&P500)
        """
        meta_df = df.copy()
        
        # 1. Recent Forecasting Error
        # abs error
        meta_df['Abs_Error'] = meta_df[error_col].abs()
        meta_df['Rolling_Error_10d'] = meta_df['Abs_Error'].rolling(self.lookback_errors).mean()
        
        # 2. Volatility Features
        if 'Close' in meta_df.columns:
            meta_df['Vol_20'] = meta_df['Close'].pct_change().rolling(20).std()
            meta_df['Vol_5'] = meta_df['Close'].pct_change().rolling(5).std()
            meta_df['Vol_Trend'] = meta_df['Vol_5'] / (meta_df['Vol_20'] + 1e-9)

        # 3. Market Dependency (Correlation with SPY/GSPC if available)
        # Assuming 'SPY_Close' or equivalent exists if merged
        spy_col = [c for c in meta_df.columns if 'SPY' in c or 'GSPC' in c]
        if spy_col:
            col = spy_col[0]
            # Rolling 20d correlation
            meta_df['Corr_SPY_20'] = meta_df['Close'].pct_change().rolling(20).corr(meta_df[col].pct_change())

        # 4. VIX Features
        vix_col = [c for c in meta_df.columns if 'VIX' in c]
        if vix_col:
            v = vix_col[0]
            meta_df['VIX_Level'] = meta_df[v]
            meta_df['VIX_MA_20'] = meta_df[v].rolling(20).mean()
            meta_df['VIX_Norm'] = meta_df[v] / (meta_df['VIX_MA_20'] + 1e-9)

        # Drop NaNs
        features = ['Rolling_Error_10d', 'Vol_20', 'Vol_Trend']
        if spy_col: features.append('Corr_SPY_20')
        if vix_col: features.extend(['VIX_Level', 'VIX_Norm'])
        
        self.feature_cols = features
        return meta_df[features]

    def _compute_reliability_target(self, pred: pd.Series, actual: pd.Series) -> pd.Series:
        """
        Define Reliability Target (0 to 1).
        
        Logic:
        - If signs match (Direction Correct):
            - If |Pred| <= |Actual|: Reliability = 1.0 (Under-confident or exact) -> Actually we want to scale.
            - If |Pred| > |Actual|: Reliability = |Actual| / |Pred| (Over-confident, needs damping)
        - If signs mismatch (Direction Wrong):
            - Reliability = 0.0 (Stop trading)
        
        Refined Logic (User request): "Base +10%, Reliability 0.3 -> +3%".
        This implies Reliability = Optimal_Scale_Factor.
        Target = Actual / Predicted.
        But we clip to [0, 1] to avoid leveraging up or flipping signs (meta-learner is conservative).
        """
        # Avoid div by zero
        denom = pred.replace(0, 1e-9)
        ratio = actual / denom
        
        # If signs mismatch, ratio is negative. Clip to 0.
        # If signs match, ratio is positive.
        # If ratio > 1 (Actual > Pred), we could cap at 1.0 (conservative) or allow > 1.
        # User implies damping ("reduces large forecast errors"). So max 1.0.
        
        reliability = ratio.clip(0, 1.0)
        # If direction wrong (ratio < 0), reliability becomes 0.
        return reliability

    def train(self, historical_df: pd.DataFrame, pred_col: str, actual_col: str):
        """
        Train the Meta-Learner on historical predictions and errors.
        historical_df must contain:
        - External features (VIX, SPY, etc.) merged
        - 'Close' price history
        - Base Model Predictions
        - Actual outcomes
        """
        # Calculate Error
        df = historical_df.copy()
        df['Error'] = df[pred_col] - df[actual_col]
        
        X = self._compute_meta_features(df, pred_col, actual_col, 'Error')
        y = self._compute_reliability_target(df[pred_col], df[actual_col])
        
        # Align
        valid_idx = X.dropna().index.intersection(y.dropna().index)
        X = X.loc[valid_idx]
        y = y.loc[valid_idx]
        
        if len(X) > 50:
            self.model.fit(X, y)
            self.is_fitted = True
            self.is_fitted = True
            if self.verbose:
                self.log_func(f"Meta-Learner trained on {len(X)} samples. Features: {self.feature_cols}")

    def predict_reliability(self, current_features_df: pd.DataFrame) -> float:
        """
        Predict reliability for the current state.
        Returns scalar 0-1.
        """
        if not self.is_fitted:
            return 1.0 # Default trust if no meta-learner
            
        # Ensure input features match
        # We need to re-compute features for the single row(s) context
        # But `current_features_df` passed here is expected to be raw DF with history to compute rolling
        
        # Actually, for API usage, we pass a dataframe with enough history to compute rolling features,
        # and we take the last row.
        
        # Extract features
        # We assume 'Error' column exists in input (recent errors)
        X_full = self._compute_meta_features(current_features_df, 'dummy', 'dummy', 'Error')
        
        # Take last row
        X_last = X_full.iloc[[-1]] 
        
        # Handle features miss (e.g. if VIX missing but trained on it)
        # Impute or subset
        # RandomForest is robust if we pass same columns.
        # If cols missing, we might fail.
        
        try:
            score = self.model.predict(X_last[self.feature_cols])[0]
            return float(np.clip(score, 0.0, 1.0))
        except Exception as e:
            if self.verbose: self.log_func(f"Meta-Learner predict failed: {e}")
            return 1.0

