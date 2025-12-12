import pandas as pd
import numpy as np
from .indicators import add_technical_indicators

class FeaturePipeline:
    def __init__(self):
        pass

    def prepare_features(self, df: pd.DataFrame, external_data: dict = None, target_col: str = 'Log_Return', horizon: int = 1) -> pd.DataFrame:
        """
        Prepare features for training/inference.
        1. Add technical indicators.
        2. Merge external features (Indices).
        3. Create target variable (future return over horizon).
        """
        if df.empty:
            return df

        # Add indicators
        df = add_technical_indicators(df)
        
        # Merge External Data (Indices)
        if external_data:
            # external_data is dict: {'SPY': spy_df, 'VIX': vix_df}
            # We assume external DFs have a 'Close' column and same index (Date)
            for name, ext_df in external_data.items():
                if 'Close' in ext_df.columns:
                    # Rename to avoid collision
                    col_name = f"{name}_Close"
                    # Join on index (Date)
                    # We use merge or join. 
                    temp = ext_df[['Close']].rename(columns={'Close': col_name})
                    df = df.join(temp, how='left')
                    
                    # Forward fill missing external data (e.g. holidays differ?)
                    df[col_name] = df[col_name].ffill()
                    
                    # Also maybe add 20d return for the index?
                    df[f"{name}_Ret_20d"] = df[col_name].pct_change(20)

        # 3. Dedicated Credit Spread Feature (HYG / LQD)
        if 'HYG_Close' in df.columns and 'LQD_Close' in df.columns:
            # Ratio > 1 implies Risk On (Junk outperforming Grade)
            # Ratio < 1 implies Risk Off
            df['Credit_Spread_Ratio'] = df['HYG_Close'] / df['LQD_Close']

        # Create Target: Future log return over 'horizon' days
        future_close = df['Close'].shift(-horizon)
        df['Target'] = np.log(future_close / df['Close'])

        # Drop NaNs created by indicators, external join, and shifting
        return df

    def get_training_data(self, df: pd.DataFrame, external_data: dict = None, horizon: int = 1):
        """
        Returns X, y for training.
        """
        df_processed = self.prepare_features(df, external_data, horizon=horizon)
        df_clean = df_processed.dropna()
        
        feature_cols = [c for c in df_clean.columns if c not in ['Target', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        X = df_clean[feature_cols]
        y = df_clean['Target']
        
        return X, y, feature_cols

    def get_inference_data(self, df: pd.DataFrame, external_data: dict = None):
        """
        Returns the last row of features for making a prediction.
        """
        df_processed = self.prepare_features(df, external_data)
        
        # We need the last row
        last_row = df_processed.iloc[[-1]].copy()
        
        feature_cols = [c for c in last_row.columns if c not in ['Target', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        if last_row[feature_cols].isna().any().any():
            print("Warning: NaNs in inference features.")
        
        return last_row[feature_cols]
