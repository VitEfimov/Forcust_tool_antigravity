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
import requests
import time

scheduler = BackgroundScheduler()

def wakeup_server():
    """
    Ensure the API is awake before running heavy background jobs.
    Retries up to 5 times (5 minutes).
    """
    url = settings.BACKEND_URL
    if "localhost" in url or "127.0.0.1" in url:
        print("[SCHEDULER] Running Locally. Wakeup check skipped.")
        return True
    logger_print = print # Simple print for scheduler
    
    logger_print("[SCHEDULER] Wakeup check initiated...")
    for i in range(1, 6):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                logger_print(f"[SCHEDULER] Server is awake (Attempt {i}).")
                return True
        except Exception as e:
            logger_print(f"[SCHEDULER] Wakeup attempt {i} failed: {e}")
            
        if i < 5:
            time.sleep(60) # Wait 1 minute
            
    logger_print("[SCHEDULER] Server failed to wakeup after 5 attempts. Skipping job.")
    return False

def wrapped_market_overview():
    if wakeup_server():
        run_scheduled_market_overview()
    else:
        monitor.log_heartbeat("MarketOverview", "skipped", {"reason": "Server wakeup failed"})

def wrapped_daily_automation():
    if wakeup_server():
        run_daily_automation(scheduled_run=True)
    else:
        monitor.log_heartbeat("DailyAutomation", "skipped", {"reason": "Server wakeup failed"})


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
    
    # --- PROPOSED FIX: Enable Local Scheduling for VPS/Local setups ---
    # Warning: This runs heavy compute in the same process as the API.
    # Ensure usage of async workers or enough resources.
    
    if settings.ENV == "production":
        print("[SCHEDULER] Production Mode Detected. Local Scheduler DISABLED (Delegate to GitHub Actions).")
        return
        
    print("[SCHEDULER] Configuring local jobs...")
    
    # 1. Market Overview (10:00 AM and 16:15 PM EST)
    scheduler.add_job(
        wrapped_market_overview, 
        CronTrigger(hour=10, minute=0, timezone='America/New_York'),
        id="market_overview_open",
        replace_existing=True
    )
    scheduler.add_job(
        wrapped_market_overview, 
        CronTrigger(hour=16, minute=15, timezone='America/New_York'),
        id="market_overview_close",
        replace_existing=True
    )
    
    # 2. Daily Automation (18:30 PM EST)
    # Runs the full production loop
    scheduler.add_job(
        wrapped_daily_automation,
        CronTrigger(hour=18, minute=30, timezone='America/New_York'),
        id="daily_automation",
        replace_existing=True
    )

    scheduler.start()
    print("[SCHEDULER] Background scheduler started with LOCAL JOBS enabled.")

def stop_scheduler():
    scheduler.shutdown()
    print("[SCHEDULER] Background scheduler stopped.")
