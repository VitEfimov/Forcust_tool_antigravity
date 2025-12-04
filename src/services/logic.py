from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from src.core.repository import MarketRepository, SimulationRepository, WishlistRepository
from src.core.models import MarketOverview, SimulationRun, WishlistItem
from src.data.loader import DataLoader
from src.core.config import settings
from src.models.advanced_simulation import AdvancedSimulator
from src.models.hmm import RegimeDetector

class MarketService:
    def __init__(self):
        self.repo = MarketRepository()
        self.loader = DataLoader(settings.DATA_CACHE_DIR)

    def get_overview(self, symbol: str, date: str) -> MarketOverview:
        # 1. Try DB
        existing = self.repo.find_by_date(symbol, date)
        if existing:
            return existing

        # 2. Compute
        # Load data up to date
        df = self.loader.get_data(symbol)
        if df.empty:
            raise ValueError(f"No data for {symbol}")
        
        # Filter up to date
        df = df[df.index <= date]
        if df.empty:
             raise ValueError(f"No data for {symbol} on {date}")

        current_price = float(df['Close'].iloc[-1])
        returns = df['Close'].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252))

        # Regime
        hmm = RegimeDetector()
        hmm.fit(returns)
        regime_idx = int(hmm.predict(returns)[-1])
        regime_label = hmm.get_regime_label(regime_idx)

        # Create Object
        overview = MarketOverview(
            symbol=symbol,
            date=date,
            regime=regime_label,
            price=current_price,
            volatility=volatility,
            forecast_short={}, # Placeholder for now
            forecast_medium={},
            forecast_long={}
        )
        
        # 3. Save
        return self.repo.create(overview)

    def get_available_dates(self) -> Dict[str, List[str]]:
        dates = self.repo.get_available_dates()
        return {
            "allowed_dates": dates,
            "disabled_dates": [] # Frontend logic can handle future dates
        }

class SimulationService:
    def __init__(self):
        self.repo = SimulationRepository()
        self.market_repo = MarketRepository()
        self.loader = DataLoader(settings.DATA_CACHE_DIR)
        self.simulator = AdvancedSimulator()

    def run_simulation(self, symbol: str, date: str, horizons: List[int] = [10, 30, 100, 365, 547, 730]) -> Dict[str, Any]:
        # 1. Ensure MarketOverview exists (or create it)
        # We don't strictly need it for simulation but good for consistency
        # market_service = MarketService()
        # market_service.get_overview(symbol, date)

        runs = []
        
        # Load data once
        df = self.loader.get_data(symbol)
        df = df[df.index <= date]
        returns = df['Close'].pct_change().dropna()
        current_price = float(df['Close'].iloc[-1])

        # Fit Models
        hmm = RegimeDetector()
        hmm.fit(returns)
        regimes = hmm.predict(returns)
        current_regime = int(regimes[-1])
        regime_label = hmm.get_regime_label(current_regime)
        transmat = hmm.model.transmat_
        params = self.simulator.fit_regime_params(returns, regimes)

        for h in horizons:
            # 2. Check DB
            existing = self.repo.find_run(symbol, date, h)
            if existing:
                runs.append(existing)
                continue

            # 3. Compute
            # Run simulation for max horizon if needed, but here we do per horizon or max?
            # To be efficient, we should run ONCE for max horizon and extract.
            # But the requirement says "If not found -> generate new... Save SimulationRun document"
            # Let's run max horizon once if any are missing.
            
            # Actually, let's just run for this horizon 'h' to be simple and robust, 
            # or run for max(horizons) and cache.
            # The prompt implies individual SimulationRun documents.
            
            sim_res = self.simulator.simulate_paths(
                start_price=current_price,
                start_regime=current_regime,
                params=params,
                transmat=transmat,
                days=h,
                sims=1000
            )
            
            q = sim_res['quantiles'][h]
            
            run = SimulationRun(
                symbol=symbol,
                date=date,
                horizon=h,
                ml_forecast=0.0, # Placeholder
                p10=q['p10'],
                p50=q['p50'],
                p90=q['p90'],
                regime=regime_label,
                model_snapshot={"regime_id": current_regime}
            )
            
            saved_run = self.repo.create(run)
            runs.append(saved_run)

        return {
            "symbol": symbol,
            "date": date,
            "regime": regime_label,
            "runs": [run.dict() for run in runs]
        }
