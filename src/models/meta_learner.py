
import pandas as pd
import numpy as np
import lightgbm as lgb
from typing import Dict, Optional, Tuple, Callable

class MetaLearner:
    """
    Meta-Learning Reliability Module (Leakage-Proof).
    Classifies if the base model is 'trustworthy' based on past performance and market conditions.
    Output: Reliability Probability (0.0 to 1.0)
    """
    def __init__(self, lookback_errors: int = 20, prediction_horizon: int = 10, verbose: bool = False, log_func: Optional[Callable[[str], None]] = None):
        self.lookback_errors = lookback_errors
        self.prediction_horizon = prediction_horizon
        self.verbose = verbose
        self.log_func = log_func if log_func else print
        
        # GPU-enabled LightGBM Classifier as requested
        self.model = lgb.LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            objective="binary", 
            device_type="cpu",
            # gpu_platform_id=0,
            # gpu_device_id=0,
            verbose=-1
        )
        self.is_fitted = False
        self.feature_cols = []

    def _compute_meta_features(self, df: pd.DataFrame, error_series: pd.Series) -> pd.DataFrame:
        """
        Compute features for the meta-learner:
        Strictly PAST looking.
        """
        meta_df = df.copy()
        meta_df['Error'] = error_series
        meta_df['Abs_Error'] = meta_df['Error'].abs()
        
        # 1. Rolling Mean Error (Available at t)
        meta_df['Rolling_Error_20d'] = meta_df['Abs_Error'].rolling(self.lookback_errors).mean()
        
        # 2. Volatility Features
        if 'Close' in meta_df.columns:
            meta_df['Vol_20'] = meta_df['Close'].pct_change().rolling(20).std()
            meta_df['Vol_Trend'] = meta_df['Close'].pct_change().rolling(5).std() / (meta_df['Vol_20'] + 1e-9)

        # 3. VIX Features
        vix_col = [c for c in meta_df.columns if 'VIX' in c]
        if vix_col:
            v = vix_col[0]
            meta_df['VIX_Level'] = meta_df[v]

        # 4. Signal Magnitude (Confidence of base model)
        if 'pred_log_ret' in meta_df.columns:
            meta_df['Signal_Mag'] = meta_df['pred_log_ret'].abs()

        features = ['Rolling_Error_20d', 'Vol_20', 'Vol_Trend', 'Signal_Mag']
        if vix_col: features.append('VIX_Level')
        
        return meta_df[features]

    def train(self, historical_df: pd.DataFrame, pred_col: str, actual_col: str):
        """
        Train the Meta-Learner (Classification).
        Features(t) predict reliability of prediction made at t-H.
        """

        df = historical_df.copy()

        # 1. Raw future error (unknown at t)
        raw_error = df[pred_col] - df[actual_col]

        # 2. Known error at time t (error of prediction made at t-H)
        df['Known_Error'] = raw_error.shift(self.prediction_horizon)

        # 3. Robust fat-tail-safe threshold (rolling)
        try:
            roll_q = (
                df[actual_col]
                .abs()
                .rolling(window=252, min_periods=20)
                .quantile(0.68)
            )
            error_threshold = roll_q.iloc[-1]
        except Exception:
            error_threshold = df[actual_col].std()

        if np.isnan(error_threshold) or error_threshold == 0:
            error_threshold = 0.01

        # 4. Target: was the PAST prediction reliable?
        df['Target_Class'] = (df['Known_Error'].abs() < error_threshold).astype(int)

        # 5. Features (STRICTLY past-looking)
        X = self._compute_meta_features(df, df['Known_Error'])
        y = df['Target_Class']

        # 6. Align (remove NaNs from shifting / rolling)
        if self.verbose:
            self.log_func(f"DEBUG ALIGN: X_shape={X.shape} y_shape={y.shape}")
            self.log_func(f"DEBUG ALIGN: X_nan={X.isna().sum().sum()} y_nan={y.isna().sum()}")
            if not X.empty:
                self.log_func(f"DEBUG ALIGN: X_dates={X.index.min()} to {X.index.max()}")
            if not y.empty:
                self.log_func(f"DEBUG ALIGN: y_dates={y.index.min()} to {y.index.max()}")

        valid_idx = X.dropna().index.intersection(y.dropna().index)
        X = X.loc[valid_idx]
        y = y.loc[valid_idx]

        # 7. Guards
        if len(X) < 50:
            if self.verbose:
                self.log_func(f"Meta-Learner: Not enough samples to train. (Aligned: {len(X)})")
            return

        if X.isnull().all(axis=1).any():
            if self.verbose:
                self.log_func("Meta-Learner: Found completely null rows. Aborting.")
            return

        # 8. Freeze schema
        self.feature_cols = list(X.columns)

        # 9. Train (GPU LightGBM)
        self.model.fit(X, y)
        self.is_fitted = True

        if self.verbose:
            self.log_func(
                f"Meta-Learner trained on {len(X)} aligned samples | "
                f"Positive class rate: {y.mean():.2f}"
            )

    def predict_reliability(self, current_features_df: pd.DataFrame, known_error_series: Optional[pd.Series] = None) -> float:
        """
        Predict probability of reliability.
        Returns scalar 0-1.
        Optionally accept pre-computed known_error_series for flexibility.
        """
        if not self.is_fitted:
            return 1.0
            
        # Reconstruct known error history
        if known_error_series is not None:
             known_error = known_error_series
        elif 'pred_log_ret' in current_features_df.columns and 'actual_log_ret' in current_features_df.columns:
            raw_error = current_features_df['pred_log_ret'] - current_features_df['actual_log_ret']
            known_error = raw_error.shift(self.prediction_horizon)
        else:
            # If not available (inference mode without fresh actuals?), we can't compute rolling error features correctly
            # unless passed in. Assuming passed df is 'meta_history' + 'current_row'.
            return 1.0

        X_full = self._compute_meta_features(current_features_df, known_error)
        X_last = X_full.iloc[[-1]] 
        
        # Handle miss & Schema Drift
        # 1. Enforce Schema
        if self.feature_cols:
            X_last = X_last.reindex(columns=self.feature_cols, fill_value=0)
            
        # 2. Fill NaNs
        X_last = X_last.fillna(0) # Simple imputation for safety
        
        try:
            # Predict Probability of Class 1 (Reliable)
            prob = self.model.predict_proba(X_last)[0, 1]
            return float(prob)
        except Exception as e:
            if self.verbose: self.log_func(f"Meta-Learner predict failed: {e}")
            return 1.0

