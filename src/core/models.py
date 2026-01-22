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

class WalkForwardResult(BaseModel):
    """
    Model for Daily Walk-Forward Analysis (The 'Brain' Output).
    """
    symbol: str
    date: str
    prediction_price: float
    reliability_score: float
    regime_label: str
    
    # Tiered Training Metadata
    mode: Optional[str] = "unknown" # train, inference_only, derived
    trained: Optional[bool] = False
    derived_from: Optional[int] = None
    
class AdvancedSimulationResult(BaseModel):
    """
    Model for Monte Carlo Stress Testing results.
    """
    symbol: str
    date: str
    mc_p10: float # Bear Case
    mc_p50: float # Base Case
    mc_p90: float # Bull Case
    conservative_mode: bool
    
class MLTrainingResult(BaseModel):
    """
    Model for Weekly Training Metrics.
    """
    symbol: str
    horizon: int
    rmse: float
    mae: float
    features_importance: Dict[str, float] = {}
    timestamp: datetime = datetime.now()
