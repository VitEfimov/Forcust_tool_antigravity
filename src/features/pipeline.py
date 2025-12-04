import pandas as pd
import numpy as np
from .indicators import add_technical_indicators

class FeaturePipeline:
    def __init__(self):
        pass

    def prepare_features(self, df: pd.DataFrame, target_col: str = 'Log_Return', horizon: int = 1) -> pd.DataFrame:
        """
        Prepare features for training/inference.
        1. Add technical indicators.
        2. Create lag features.
        3. Create target variable (future return over horizon).
        """
        if df.empty:
            return df

        # Add indicators
        df = add_technical_indicators(df)

        # Create Target: Future log return over 'horizon' days
        # Target = log(Price_{t+h} / Price_t)
        # We shift the Close price back by 'horizon' to align Price_{t+h} with Price_t row?
        # No, we want to predict at time t what the return will be at t+h.
        # So Target_t = log(Close_{t+h} / Close_t)
        # This means we need to shift the future close BACK to current row.
        future_close = df['Close'].shift(-horizon)
        df['Target'] = np.log(future_close / df['Close'])

        # Drop NaNs created by indicators and shifting
        # Note: In a real prod pipeline, we might be more careful about dropping recent data for inference.
        # For training, we drop rows with missing targets.
        # For inference, we keep the last row (which has missing target but valid features).
        
        return df

    def get_training_data(self, df: pd.DataFrame, horizon: int = 1):
        """
        Returns X, y for training.
        Drops rows with NaN in features or target.
        """
        df_processed = self.prepare_features(df, horizon=horizon)
        df_clean = df_processed.dropna()
        
        feature_cols = [c for c in df_clean.columns if c not in ['Target', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        X = df_clean[feature_cols]
        y = df_clean['Target']
        
        return X, y, feature_cols

    def get_inference_data(self, df: pd.DataFrame):
        """
        Returns the last row of features for making a prediction.
        """
        df_processed = self.prepare_features(df)
        
        # We need the last row, even if Target is NaN (which it should be for tomorrow)
        last_row = df_processed.iloc[[-1]].copy()
        
        feature_cols = [c for c in last_row.columns if c not in ['Target', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Check if we have NaNs in features (e.g. not enough history for SMA_200)
        if last_row[feature_cols].isna().any().any():
            print("Warning: NaNs in inference features. Not enough history?")
            # Fill with 0 or mean? For now, just leave it, LightGBM handles NaNs.
        
        return last_row[feature_cols]
