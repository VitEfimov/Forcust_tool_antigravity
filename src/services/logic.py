from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import numpy as np
# from src.core.repository import MarketRepository, SimulationRepository, WishlistRepository
from src.core.models import MarketOverview, SimulationRun, WishlistItem
from src.data.loader import DataLoader
from src.core.config import settings

from src.models.hmm import RegimeDetector

def needs_refresh(last_update: datetime) -> bool:
    """
    Check if data needs refresh based on 10am, 12pm, 2pm, 4pm checkpoints.
    """
    if not last_update:
        return True
        
    now = datetime.now()
    # If different day, definitely refresh
    if last_update.date() < now.date():
        return True
    
    # Intraday checkpoints
    checkpoints = [10, 12, 14, 16]
    for cp in checkpoints:
        cp_time = now.replace(hour=cp, minute=0, second=0, microsecond=0)
        # If we passed a checkpoint that the last update didn't cover
        if now >= cp_time and last_update < cp_time:
            return True
            
    return False

class MarketService:
    def __init__(self):
        # self.repo = MarketRepository() # Removed for localruns
        self.loader = DataLoader(settings.DATA_CACHE_DIR)

    def get_overview(self, symbol: str, date: str) -> MarketOverview:
        # 1. Try DB -> SKIPPED
        # existing = self.repo.find_by_date(symbol, date)
        
        # Always Compute
        
        # Load data up to date
        df = self.loader.get_data(symbol, use_cache=True)
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
        
        # 3. Save -> SKIPPED
        # return self.repo.create(overview)
        return overview

    def get_available_dates(self) -> Dict[str, List[str]]:
        # dates = self.repo.get_available_dates() # Removed
        dates = [datetime.now().strftime("%Y-%m-%d")]
        return {
            "allowed_dates": dates,
            "disabled_dates": [] 
        }

class SimulationService:
    def __init__(self):
        # self.repo = SimulationRepository() # Removed
        # self.market_repo = MarketRepository() # Removed
        self.loader = DataLoader(settings.DATA_CACHE_DIR)
        self.simulator = None

    def _get_simulator(self):
        if not self.simulator:
            from src.models.advanced_simulation import AdvancedSimulator
            self.simulator = AdvancedSimulator()
        return self.simulator

    def run_simulation(self, symbol: str, date: str, horizons: List[int] = [10, 30, 100, 365, 547, 730]) -> Dict[str, Any]:
        # 1. Check DB -> SKIPPED
        
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
        params = self._get_simulator().fit_regime_params(returns, regimes)

        for h in horizons:
            # 2. Check DB -> SKIPPED

            # 3. Compute
            sim_res = self._get_simulator().simulate_paths(
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
            
            # saved_run = self.repo.create(run) # SKIPPED
            runs.append(run)

        return {
            "symbol": symbol,
            "date": date,
            "regime": regime_label,
            "runs": [run.model_dump() for run in runs]
        }
