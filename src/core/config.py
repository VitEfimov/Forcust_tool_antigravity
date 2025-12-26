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
    
    # Database check
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/forecasts.db")
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "sqlite") # sqlite, mongo, excel
    LOCAL_DATA_DIR: str = os.getenv("LOCAL_DATA_DIR", "data/local")

    # Feature Tiers (Free Tier Optimization)
    TIER_1_INDICES: list = ['^GSPC', '^VIX', '^TNX', 'DX-Y.NYB', 'CL=F']
    TIER_2_INDICES: list = ['^IXIC', '^RUT', 'GC=F']
    TIER_3_INDICES: list = ['^VVIX', '^SKEW', 'HYG', 'LQD'] # Advanced Risk Metrics
    MEGA_CAP_COMPONENTS: list = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'NVDA', 'META', 'BRK-B', 'JPM', 'JNJ', 'TSLA']
    
    # Training Config
    TRAINING_TARGETS: list = ['^IXIC', 'AAPL', 'NVDA', 'SPCE']

settings = Settings()
