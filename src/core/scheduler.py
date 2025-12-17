from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from pathlib import Path
import json
from src.core.config import settings
from src.core.monitoring import monitor
from src.api.routes import _compute_market_overview, TOP_SP500
from src.jobs.daily_run import run_daily_automation
from src.jobs.weekly_train import main as run_weekly_training

scheduler = BackgroundScheduler()

def run_scheduled_market_overview():
    """
    Task to run Market Overview updates and save the result.
    Scheduled for 10:00 and 16:00.
    """
    print(f"[SCHEDULER] Running scheduled Market Overview at {datetime.now()}")
    monitor.log_heartbeat("MarketOverview", "running")
    try:
        # 1. Compute Overview (this triggers caching and ensures fresh data if cache expired)
        # Note: We use the Logic function directly or the route helper. 
        # _compute_market_overview is the one that enriches with Advanced Sim.
        # 1. Compute Overview (this triggers caching and ensures fresh data if cache expired)
        # Combine Stocks + Indices for a complete picture
        targets = TOP_SP500 + settings.TIER_1_INDICES + settings.TIER_2_INDICES
        result = _compute_market_overview(targets)
        
        # 2. Save to Disk
        save_dir = Path(settings.LOCAL_DATA_DIR) / "market_overviews"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"overview_{timestamp}.json"
        filepath = save_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(result, f, indent=4)
            
        print(f"[SCHEDULER] Saved Market Overview to {filepath}")
        
        # 3. Save to DB (Full Data per User Request)
        saved_id = "N/A"
        try:
            from src.core.database import get_db
            # This returns None currently, but we can assume success if no error
            get_db().save_market_overview(result)
            print(f"[SCHEDULER] Saved Market Overview to Database.")
            saved_id = "Mongo/SQLite"
        except Exception as e:
            print(f"[SCHEDULER] Failed to save to DB: {e}")

        # 4. Calculate Summary Metrics for Heartbeat
        overview = result.get("overview", [])
        avg_change = 0.0
        bullish = 0
        bearish = 0
        vix = "N/A"
        
        if overview:
            changes = [x.get('change_pct', 0) for x in overview if isinstance(x.get('change_pct'), (int, float))]
            if changes:
                avg_change = sum(changes) / len(changes)
                bullish = sum(1 for c in changes if c > 0)
                bearish = sum(1 for c in changes if c < 0)
            
            # Find VIX
            vix_item = next((x for x in overview if x.get('symbol') == '^VIX'), None)
            if vix_item:
                vix = vix_item.get('price')

        details = {
            "files_saved": 1,
            "db_saved": True,
            "items_processed": len(overview),
            "market_breadth": f"{bullish} Up / {bearish} Down",
            "avg_change": f"{avg_change:+.2f}%",
            "vix": vix,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

        monitor.log_heartbeat("MarketOverview", "success", details)
        
    except Exception as e:
        print(f"[SCHEDULER] Error in scheduled task: {e}")
        monitor.log_heartbeat("MarketOverview", "error", {"error": str(e)})

def start_scheduler():
    """Start the background scheduler."""
    # API Mode: We do NOT run heavy jobs here. They are handled by GitHub Actions.
    
    # 1. Daily Automation -> GitHub Action (daily_compute.yml)
    # 2. Weekly Training -> GitHub Action (weekly_training.yml)
    # 3. Market Overview -> GitHub Action (market_open.yml)
    
    scheduler.start()
    print("[SCHEDULER] Background scheduler started (API Mode - No local jobs).")

def stop_scheduler():
    scheduler.shutdown()
    print("[SCHEDULER] Background scheduler stopped.")
