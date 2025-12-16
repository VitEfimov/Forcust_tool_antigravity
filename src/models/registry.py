import os
from pathlib import Path

class ModelRegistry:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save_hmm(self, symbol: str, model):
        from .hmm import RegimeDetector
        path = self.models_dir / f"{symbol}_hmm.joblib"
        model.save(str(path))

    def load_hmm(self, symbol: str):
        path = self.models_dir / f"{symbol}_hmm.joblib"
        if not path.exists():
            return None
        from .hmm import RegimeDetector
        model = RegimeDetector()
        model.load(str(path))
        return model

    def save_forecast_model(self, symbol: str, model, horizon: int):
        from .lightgbm_forecaster import ForecastModel
        path = self.models_dir / f"{symbol}_lgb_{horizon}d.txt"
        model.save(str(path))

    def load_forecast_model(self, symbol: str, horizon: int):
        path = self.models_dir / f"{symbol}_lgb_{horizon}d.txt"
        if not path.exists():
            return None
        from .lightgbm_forecaster import ForecastModel
        model = ForecastModel()
        model.load(str(path))
        return model

    def save_garch(self, symbol: str, model):
        path = self.models_dir / f"{symbol}_garch.joblib"
        model.save(str(path))

    def load_garch(self, symbol: str):
        path = self.models_dir / f"{symbol}_garch.joblib"
        if not path.exists():
            return None
        from .garch_volatility import GarchModel
        model = GarchModel()
        model.load(str(path))
        return model

    def save_transformer(self, symbol: str, model):
        import torch
        path = self.models_dir / f"{symbol}_transformer.pt"
        torch.save(model.model.state_dict(), path)

    def load_transformer(self, symbol: str):
        path = self.models_dir / f"{symbol}_transformer.pt"
        if not path.exists():
            return None
        from .transformer_model import TransformerForecaster
        # Input dim might need to be dynamic or config based, assume 11 default
        model = TransformerForecaster(input_dim=11)
        import torch
        model.model.load_state_dict(torch.load(path))
        return model
