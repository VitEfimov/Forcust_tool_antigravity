import os
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load .env from project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"Loading config from {env_path}")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

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
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/forecasts.db")

settings = Settings()
