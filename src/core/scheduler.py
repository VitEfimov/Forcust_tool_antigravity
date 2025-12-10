from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from pathlib import Path
import json
from src.core.config import settings
from src.core.monitoring import monitor
from src.api.routes import _compute_market_overview, TOP_SP500
from src.jobs.daily_run import main as run_daily_automation
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
        result = _compute_market_overview(TOP_SP500)
        
        # 2. Save to Disk
        save_dir = Path(settings.LOCAL_DATA_DIR) / "market_overviews"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"overview_{timestamp}.json"
        filepath = save_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(result, f, indent=4)
            
        print(f"[SCHEDULER] Saved Market Overview to {filepath}")
        monitor.log_heartbeat("MarketOverview", "success", {"files_saved": 1})
        
    except Exception as e:
        print(f"[SCHEDULER] Error in scheduled task: {e}")
        monitor.log_heartbeat("MarketOverview", "error", {"error": str(e)})

def start_scheduler():
    """Start the background scheduler."""
    
    # 1. Daily Automation (08:00 UTC)
    scheduler.add_job(
        run_daily_automation,
        CronTrigger(hour=8, minute=0),
        id="daily_automation",
        replace_existing=True
    )
    
    # 2. Weekly Training (Sunday 09:00 UTC)
    scheduler.add_job(
        run_weekly_training,
        CronTrigger(day_of_week='sun', hour=9, minute=0),
        id="weekly_training",
        replace_existing=True
    )

    # 3. Market Overview (10:00 AM)
    scheduler.add_job(
        run_scheduled_market_overview,
        CronTrigger(hour=10, minute=0),
        id="overview_10am",
        replace_existing=True
    )
    
    # 4. Market Overview (4:00 PM)
    scheduler.add_job(
        run_scheduled_market_overview,
        CronTrigger(hour=16, minute=0),
        id="overview_4pm",
        replace_existing=True
    )
    
    scheduler.start()
    print("[SCHEDULER] Background scheduler started (Daily/Weekly/Intraday).")

def stop_scheduler():
    scheduler.shutdown()
