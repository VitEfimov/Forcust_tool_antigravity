
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.config import settings

def test_config():
    print(f"Checking {len(settings.MEGA_CAP_COMPONENTS)} Mega Cap Components...")
    
    expected = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'NVDA', 'META', 'BRK-B', 'JPM', 'JNJ', 'TSLA', 
        'UNH', 'LLY', 'V', 'XOM', 'MA', 'PG', 'HD', 'COST', 'AVGO', 'CVX', 
        'MRK', 'ABBV', 'PEP', 'KO', 'BAC', 'ADBE', 'WMT', 'MCD', 'CSCO', 'CRM', 
        'ACN', 'TMO', 'LIN', 'AMD', 'NFLX', 'ABT', 'DHR', 'ORCL', 'CMCSA', 'DIS', 
        'WFC', 'TXN', 'VZ', 'NEE', 'PM', 'UPS', 'NKE', 'INTC', 'RTX', 'MS']
    
    # Check deduplication
    assert len(expected) == len(set(expected)), "Expected list has duplicates?"
    
    missing = [x for x in expected if x not in settings.MEGA_CAP_COMPONENTS]
    if missing:
        print(f"MISSING COMPONENTS in Config: {missing}")
        sys.exit(1)
        
    # Check JPM and JNJ appear only once in settings
    if settings.MEGA_CAP_COMPONENTS.count('JPM') > 1:
        print("FAIL: JPM duplicate found in settings")
        sys.exit(1)
        
    # Check Targets
    targets = settings.TRAINING_TARGETS
    missing_targets = [x for x in expected if x not in targets]
    if missing_targets:
        print(f"FAIL: Mega Caps not in TRAINING_TARGETS: {missing_targets}")
        sys.exit(1)
        
    # --- NEW: Check Tiered Config ---
    assert settings.SYMBOL_TIERS, "SYMBOL_TIERS missing"
    assert "tier_1" in settings.SYMBOL_TIERS
    assert "tier_2" in settings.SYMBOL_TIERS
    assert len(settings.BASE_HORIZONS) == 2, "BASE_HORIZONS Check"
    assert 30 in settings.DERIVED_HORIZONS
    assert 365 in settings.DERIVED_HORIZONS
    
    # Check Safety Defaults
    assert settings.TRAINING_CONFIG["allow_weekly_training"] == False, "SAFETY FAIL: Weekly training enabled by default"
        
    print("SUCCESS: Config verified (Tiers + Safety).")
    
if __name__ == "__main__":
    test_config()
