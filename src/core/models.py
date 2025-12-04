from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import List, Dict, Optional, Annotated, Any
from datetime import datetime
from bson import ObjectId

def validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")

PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

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
