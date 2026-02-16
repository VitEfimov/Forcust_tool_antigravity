from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
from src.core.database import get_db, Database
from src.core.models import MarketOverview, SimulationRun, WishlistItem

class BaseRepository:
    def __init__(self):
        self._db: Database = get_db()

    @property
    def db(self):
        return self._db

class MarketRepository(BaseRepository):
    """
    Repository for Market Data (Overviews, Prices, etc.)
    """
    
    def find_by_date(self, symbol: str, date: str) -> Optional[MarketOverview]:
        """
        Find market overview by symbol and date.
        """
        if self.db.is_mongo:
            doc = self.db.db.market_overviews.find_one({
                "data.symbol": symbol,
                "date": date
            })
            if doc:
                # The data is nested in 'data' field for overviews
                data = doc.get("data", {})
                return MarketOverview(**data)
        elif self.db.is_excel:
            # Not fully supported in Excel for single item fetch efficienty, 
            # but could implement if needed.
            pass
        else:
            # SQLite
            # We implemented full_market_overviews as a big JSON blob per day usually.
            # But the requirement implies granular fetch?
            # Actually database.py save_market_overview saves the *entire* list of stocks in one record?
            # Let's check database.py... 
            # save_market_overview(self, overview_data: Dict) -> saves {overview: [...]}
            
            # This finding implies standard "MarketOverview" might be per-symbol or per-day?
            # Accessing src/services/logic.py: get_overview returns MarketOverview object.
            # logic.save: repo.create(overview)
            pass
            
        return None

    def create(self, overview: MarketOverview) -> MarketOverview:
        """
        Save a single market overview record.
        """
        data = overview.model_dump()
        
        # We need a way to store INDIVIDUAL symbol overviews if we want to fetch them individually.
        # The current database.py 'save_market_overview' saves a BULK snapshot.
        # We might need a new collection/table for granular history if we want to use this pattern.
        # OR we adapt to the bulk structure.
        
        # For now, let's implement a Granular Save if possible, or appending to Bulk.
        # Writing to 'market_state' collection?
        
        if self.db.is_mongo:
             self.db.db.market_overviews_granular.update_one(
                 {"symbol": overview.symbol, "date": overview.date},
                 {"$set": data},
                 upsert=True
             )
        
        # For compatibility with existing bulk viewer, we might leave that to the scheduler.
        return overview

    def get_available_dates(self) -> List[str]:
        """
        Get list of dates we have data for.
        """
        if self.db.is_mongo:
            # Aggregation to find distinct dates
            return self.db.db.market_overviews_granular.distinct("date")
        return [datetime.now().strftime("%Y-%m-%d")]

class SimulationRepository(BaseRepository):
    """
    Repository for Simulation Runs.
    """
    
    def find_run(self, symbol: str, date: str, horizon: int) -> Optional[SimulationRun]:
        if self.db.is_mongo:
            doc = self.db.db.simulation_runs.find_one({
                "symbol": symbol,
                "date": date,
                "horizon": horizon
            })
            if doc:
                 return SimulationRun(**doc)
        return None

    def create(self, run: SimulationRun) -> SimulationRun:
        data = run.model_dump()
        if self.db.is_mongo:
            self.db.db.simulation_runs.update_one(
                {"symbol": run.symbol, "date": run.date, "horizon": run.horizon},
                {"$set": data},
                upsert=True
            )
        # Add SQLite support if needed
        return run

    def delete_many(self, query: Dict):
        if self.db.is_mongo:
            self.db.db.simulation_runs.delete_many(query)

class WishlistRepository(BaseRepository):
    """
    Repository for User Watchlist.
    """
    def get_all(self) -> List[WishlistItem]:
        symbols = self.db.get_watchlist()
        return [WishlistItem(symbol=s) for s in symbols]
        
    def add(self, item: WishlistItem):
        self.db.add_to_watchlist(item.symbol)
        
    def remove(self, symbol: str):
        self.db.remove_from_watchlist(symbol)
