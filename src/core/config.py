import os

class Settings:
    PROJECT_NAME: str = "Antigravity"
    VERSION: str = "0.1.0"
    DATA_CACHE_DIR: str = "data/cache"
    MODELS_DIR: str = "models"
    SYMBOLS: list = ["SPY", "QQQ", "IWM"] # Default symbols to track
    
    # Cycle Theory Constants (Trading Days)
    # Mini-cycle: 4 years * 252 days = 1008 days
    MINI_CYCLE_DAYS: int = 1008
    # Business cycle: 10 years * 252 days = 2520 days
    BUSINESS_CYCLE_DAYS: int = 2520

settings = Settings()
