import pytest
import pandas as pd
import numpy as np
from src.models.hmm import RegimeDetector
from src.models.forecast import ForecastModel

def test_hmm():
    # Create dummy returns
    returns = pd.Series(np.random.normal(0, 0.01, 100))
    
    hmm = RegimeDetector(n_components=2, n_iter=10)
    hmm.fit(returns)
    
    assert hmm.is_fitted
    
    preds = hmm.predict(returns)
    assert len(preds) == len(returns)
    assert set(preds).issubset({0, 1})
    
    probs = hmm.predict_proba(returns)
    assert probs.shape == (len(returns), 2)

def test_forecast_model():
    # Create dummy data
    X = pd.DataFrame(np.random.rand(100, 5), columns=[f'f{i}' for i in range(5)])
    y = pd.Series(np.random.rand(100))
    
    model = ForecastModel()
    model.fit(X, y)
    
    assert model.model is not None
    
    preds = model.predict(X)
    assert len(preds) == len(X)
