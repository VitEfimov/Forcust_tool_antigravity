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
        self.repo = MarketRepository()
        self.loader = DataLoader(settings.DATA_CACHE_DIR)

    def get_overview(self, symbol: str, date: str) -> MarketOverview:
        # 1. Try DB
        existing = self.repo.find_by_date(symbol, date)
        
        # Check Freshness
        force_refresh = False
        if existing:
            if needs_refresh(existing.created_at):
                # Only force refresh if the requested date is TODAY
                # If requesting past date, existing is fine (unless we want to correct history?)
                # Usually we only update 'today' intraday.
                if date == datetime.now().strftime("%Y-%m-%d"):
                    force_refresh = True
                    print(f"Refreshing stale data for {symbol} (Last update: {existing.created_at})")
        
        if existing and not force_refresh:
            return existing

        # 2. Compute
        # If force_refresh, bypass cache in loader
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
            forecast_short={}, # Placeholder for now
            forecast_medium={},
            forecast_long={}
        )
        
        # 3. Save (Upsert handled by repo/logic or we need delete/create?)
        # Repo 'create' inserts new doc. If unique index exists, it fails.
        # We should use 'update' or delete old one.
        # Let's check repo implementation. It uses insert_one.
        # We need an upsert or update method in repo.
        # For now, let's delete existing if force_refresh.
        
        if existing and force_refresh:
            self.repo.delete({"_id": existing.id})
            
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
        # Check freshness for simulation too?
        # If market data updated, simulation might be stale.
        # We can check if any run exists for this date.
        
        # Logic: Check one run (e.g. horizon 10)
        # If it exists and is stale -> delete ALL runs for this symbol/date and re-run.
        
        check_run = self.repo.find_run(symbol, date, horizons[0])
        force_refresh = False
        
        if check_run:
            if needs_refresh(check_run.created_at):
                if date == datetime.now().strftime("%Y-%m-%d"):
                    force_refresh = True
                    print(f"Refreshing stale simulation for {symbol}")
        
        if force_refresh:
            # Delete all runs for this symbol/date to ensure consistency
            self.repo.delete_many({"symbol": symbol, "date": date})
            # Also force data reload
            self.loader.get_data(symbol, use_cache=False)

        runs = []
        
        # Load data once
        df = self.loader.get_data(symbol) # Cache might be refreshed above
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
            # 2. Check DB (unless forced refresh which deleted them)
            existing = self.repo.find_run(symbol, date, h)
            if existing:
                runs.append(existing)
                continue

            # 3. Compute
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
            "runs": [run.model_dump() for run in runs]
        }
