import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.core.config import settings
from src.core.database import get_db, get_market_overview_logic
from src.core.monitoring import monitor
from src.api.routes import _compute_market_overview

def run_job():
    print(f"[JOB] Running Market Overview at {datetime.now()}")
    monitor.log_heartbeat("MarketOverview", "running")
    
    try:
        # 1. Watchlist
        db = get_db()
        watchlist = db.get_watchlist()
        
        # 2. Compute Overview
        if not watchlist:
            watchlist = settings.SYMBOLS
            
        # We use the routes helper which handles caching logic but here we force compute
        # Actually _compute_market_overview takes a list of symbols
        # But wait, routes.py imports might be tricky without full app context?
        # Let's see if we can use _compute_market_overview or replicate it.
        # It's cleaner to reuse.
        
        overview = _compute_market_overview(watchlist)
        
        # 3. Save
        db.save_market_overview(overview)
        
        # 4. Metrics
        bullish = len([x for x in overview.get('overview', []) if x.get('signal') == 'bullish'])
        bearish = len([x for x in overview.get('overview', []) if x.get('signal') == 'bearish'])
        monitor.log_heartbeat("MarketOverview", "success", {
            "items": len(overview.get('overview', [])),
            "breadth": f"{bullish}/{bearish}"
        })
        print("[JOB] Market Overview Completed Successfully.")
        
    except Exception as e:
        print(f"[JOB] Failed: {e}")
        monitor.log_heartbeat("MarketOverview", "error", {"error": str(e)})
        sys.exit(1)

if __name__ == "__main__":
    run_job()
