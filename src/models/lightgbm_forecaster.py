import lightgbm as lgb
import pandas as pd
import numpy as np
import joblib

class ForecastModel:
    def __init__(self):
        self.model = None
        self.params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9
        }

    def fit(self, X: pd.DataFrame, y: pd.Series):
        train_data = lgb.Dataset(X, label=y)
        self.model = lgb.train(self.params, train_data, num_boost_round=100)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not fitted")
        return self.model.predict(X)

    def save(self, path: str):
        if self.model:
            self.model.save_model(path)

    def load(self, path: str):
        self.model = lgb.Booster(model_file=path)
