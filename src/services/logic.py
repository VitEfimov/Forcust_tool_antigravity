from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from src.core.repository import MarketRepository, SimulationRepository, WishlistRepository
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
        try:
            self.repo = MarketRepository()
        except Exception as e:
            print(f"Warning: MarketRepository init failed: {e}")
            self.repo = None
        self.loader = DataLoader(settings.DATA_CACHE_DIR)

    def get_overview(self, symbol: str, date: str) -> MarketOverview:
        # 1. Try DB
        existing = None
        if self.repo:
            try:
                existing = self.repo.find_by_date(symbol, date)
            except Exception as e:
                print(f"Warning: DB fetch failed for {symbol}: {e}")

        # Check Freshness
        force_refresh = False
        if existing:
            if needs_refresh(existing.created_at):
                if date == datetime.now().strftime("%Y-%m-%d"):
                    force_refresh = True
                    print(f"Refreshing stale data for {symbol} (Last update: {existing.created_at})")
        
        if existing and not force_refresh:
            return existing

        # 2. Compute
        use_cache = not force_refresh
        
        # Load data up to date
        df = self.loader.get_data(symbol, use_cache=use_cache)
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
            forecast_short={}, 
            forecast_medium={},
            forecast_long={}
        )
        
        # 3. Save
        if self.repo:
            try:
                if existing and force_refresh:
                    self.repo.delete({"_id": existing.id})
                return self.repo.create(overview)
            except Exception as e:
                print(f"Warning: DB save failed for {symbol}: {e}")
                return overview
        
        return overview

    def get_available_dates(self) -> Dict[str, List[str]]:
        dates = []
        if self.repo:
            try:
                dates = self.repo.get_available_dates()
            except Exception as e:
                print(f"Warning: DB get_available_dates failed: {e}")
        
        if not dates:
            dates = [datetime.now().strftime("%Y-%m-%d")]
            
        return {
            "allowed_dates": dates,
            "disabled_dates": [] 
        }

class SimulationService:
    def __init__(self):
        try:
            self.repo = SimulationRepository()
            self.market_repo = MarketRepository()
        except Exception as e:
            print(f"Warning: SimulationRepository init failed: {e}")
            self.repo = None
            self.market_repo = None
            
        self.loader = DataLoader(settings.DATA_CACHE_DIR)
        self.simulator = None

    def _get_simulator(self):
        if not self.simulator:
            from src.models.advanced_simulation import AdvancedSimulator
            self.simulator = AdvancedSimulator()
        return self.simulator

    def run_simulation(self, symbol: str, date: str, horizons: List[int] = [10, 30, 100, 365, 547, 730]) -> Dict[str, Any]:
        check_run = None
        if self.repo:
            try:
                check_run = self.repo.find_run(symbol, date, horizons[0])
            except Exception as e:
                print(f"Warning: DB find_run failed: {e}")

        force_refresh = False
        if check_run:
            if needs_refresh(check_run.created_at):
                if date == datetime.now().strftime("%Y-%m-%d"):
                    force_refresh = True
                    print(f"Refreshing stale simulation for {symbol}")
        
        if force_refresh and self.repo:
            try:
                self.repo.delete_many({"symbol": symbol, "date": date})
                self.loader.get_data(symbol, use_cache=False)
            except Exception as e:
                print(f"Warning: DB delete failed: {e}")

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
            existing = None
            if self.repo and not force_refresh:
                try:
                    existing = self.repo.find_run(symbol, date, h)
                except:
                    pass
            
            if existing:
                runs.append(existing)
                continue

            # Compute
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
                ml_forecast=0.0, 
                p10=q['p10'],
                p50=q['p50'],
                p90=q['p90'],
                regime=regime_label,
                model_snapshot={"regime_id": current_regime}
            )
            
            if self.repo:
                try:
                    saved_run = self.repo.create(run)
                    runs.append(saved_run)
                except Exception as e:
                    print(f"Warning: DB save run failed: {e}")
                    runs.append(run)
            else:
                runs.append(run)

        return {
            "symbol": symbol,
            "date": date,
            "regime": regime_label,
            "runs": [run.model_dump() for run in runs]
        }
