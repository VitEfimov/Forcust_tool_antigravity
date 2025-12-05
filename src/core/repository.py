from typing import List, Optional, Type, TypeVar, Generic
from datetime import datetime
import pymongo
from .config import settings
from .models import MarketOverview, WishlistItem, SimulationRun, UserPreferences

T = TypeVar('T', bound='MongoBaseModel')

class MongoRepository(Generic[T]):
    def __init__(self, collection_name: str, model_cls: Type[T]):
        self.client = pymongo.MongoClient(settings.DATABASE_URL)
        try:
            self.db = self.client.get_default_database()
        except pymongo.errors.ConfigurationError:
            # Fallback if no database name in URL
            self.db = self.client.get_database("forcast_antigravity")
        self.collection = self.db[collection_name]
        self.model_cls = model_cls

    def create(self, item: T) -> T:
        data = item.model_dump(by_alias=True, exclude={"id"})
        result = self.collection.insert_one(data)
        item.id = str(result.inserted_id)
        return item

    def find_one(self, query: dict) -> Optional[T]:
        data = self.collection.find_one(query)
        if data:
            return self.model_cls(**data)
        return None

    def find_many(self, query: dict, limit: int = 100, sort: list = None) -> List[T]:
        cursor = self.collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.limit(limit)
        return [self.model_cls(**doc) for doc in cursor]

    def update(self, query: dict, update_data: dict):
        self.collection.update_one(query, {"$set": update_data})

    def delete(self, query: dict):
        self.collection.delete_one(query)

    def delete_many(self, query: dict):
        self.collection.delete_many(query)

class MarketRepository(MongoRepository[MarketOverview]):
    def __init__(self):
        super().__init__("market_overview", MarketOverview)
        # Ensure index on symbol and date
        self.collection.create_index([("symbol", 1), ("date", 1)], unique=True)

    def find_latest_by_symbol(self, symbol: str) -> Optional[MarketOverview]:
        return self.find_one({"symbol": symbol}, sort=[("date", -1)])

    def find_by_date(self, symbol: str, date: str) -> Optional[MarketOverview]:
        return self.find_one({"symbol": symbol, "date": date})
    
    def get_available_dates(self) -> List[str]:
        return sorted(self.collection.distinct("date"))

class SimulationRepository(MongoRepository[SimulationRun]):
    def __init__(self):
        super().__init__("simulation_runs", SimulationRun)
        self.collection.create_index([("symbol", 1), ("date", 1), ("horizon", 1)], unique=True)

    def find_run(self, symbol: str, date: str, horizon: int) -> Optional[SimulationRun]:
        return self.find_one({"symbol": symbol, "date": date, "horizon": horizon})

    def get_available_dates(self, symbol: str) -> List[str]:
        return sorted(self.collection.distinct("date", {"symbol": symbol}))

class WishlistRepository(MongoRepository[WishlistItem]):
    def __init__(self):
        super().__init__("wishlist", WishlistItem)
        self.collection.create_index("symbol", unique=True)

    def get_all_symbols(self) -> List[str]:
        items = self.find_many({}, limit=1000)
        return sorted([item.symbol for item in items])
