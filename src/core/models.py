"""
Pydantic models for the Forcust application.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class MarketOverview(BaseModel):
    """Model for market overview data."""
    symbol: str
    date: str
    regime: str
    price: float
    volatility: float
    forecast_short: Dict[str, Any] = {}
    forecast_medium: Dict[str, Any] = {}
    forecast_long: Dict[str, Any] = {}

class SimulationRun(BaseModel):
    """Model for a single simulation run."""
    symbol: str
    date: str
    horizon: int
    ml_forecast: float
    p10: float
    p50: float
    p90: float
    regime: str
    model_snapshot: Dict[str, Any] = {}

class WishlistItem(BaseModel):
    """Model for wishlist/watchlist items."""
    symbol: str
    added_at: Optional[datetime] = None
    notes: Optional[str] = None
