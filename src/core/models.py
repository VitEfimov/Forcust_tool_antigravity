from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class MarketOverview(MongoBaseModel):
    symbol: str
    date: str # YYYY-MM-DD
    regime: str
    price: float
    volatility: float
    forecast_short: Dict[str, float] = {} # 10d
    forecast_medium: Dict[str, float] = {} # 100d
    forecast_long: Dict[str, float] = {} # 365d+

class WishlistItem(MongoBaseModel):
    symbol: str
    added_at: datetime = Field(default_factory=datetime.utcnow)
    note: Optional[str] = None
    user_id: str = "default"

class SimulationRun(MongoBaseModel):
    symbol: str
    date: str # YYYY-MM-DD
    horizon: int
    ml_forecast: float
    p10: float
    p50: float
    p90: float
    regime: str
    model_snapshot: Dict = {}
    
class UserPreferences(MongoBaseModel):
    user_id: str
    wishlist_symbols: List[str] = []
    ui_settings: Dict = {}
