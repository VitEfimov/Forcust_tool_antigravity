import sys
from pathlib import Path
from apscheduler.triggers.cron import CronTrigger

# Fix path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.core.scheduler import scheduler, start_scheduler

def verify_registration():
    print("Starting Scheduler...")
    start_scheduler()
    
    jobs = scheduler.get_jobs()
    print(f"Found {len(jobs)} jobs registered.")
    
    expected_ids = ["market_overview_open", "market_overview_close", "daily_automation"]
    found_ids = [job.id for job in jobs]
    
    for eid in expected_ids:
        if eid in found_ids:
            print(f"Verified Job: {eid}")
        else:
            print(f"MISSING Job: {eid}")
            
    # Check if they are using the wrapped functions (by inspecting the func name if possible)
    for job in jobs:
        print(f"Job {job.id} targets: {job.func.__name__}")
        if "wrapped" not in job.func.__name__:
             print(f"WARNING: Job {job.id} is NOT using a wrapper!")
        else:
             print(f"OK: Job {job.id} is wrapped.")

    scheduler.shutdown()
    print("Scheduler shutdown.")

if __name__ == "__main__":
    verify_registration()
