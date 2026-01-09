
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Configure logging to see scheduler output
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Import the modules to test
from src.core import scheduler as sched_module

# --- MOCKS ---
# 1. Mock requests.get to ensure wakeup_server returns True immediately
mock_response = MagicMock()
mock_response.status_code = 200
sched_module.requests.get = MagicMock(return_value=mock_response)

# 2. Mock run_daily_automation to verify specific call args
sched_module.run_daily_automation = MagicMock()

# 3. Mock monitor to prevent side effects
sched_module.monitor = MagicMock()

def test_scheduler_trigger():
    print(f"[{datetime.now()}] Starting Scheduler Test...")
    
    # Initialize scheduler
    sched = sched_module.scheduler
    if not sched.running:
        sched.start()
        
    # Schedule the job for 2 seconds from now
    run_time = datetime.now() + timedelta(seconds=2)
    print(f"[{datetime.now()}] Scheduling wrapped_daily_automation for {run_time}...")
    
    sched.add_job(
        sched_module.wrapped_daily_automation,
        'date',
        run_date=run_time,
        id='test_daily_job'
    )
    
    # Wait for execution (5 seconds buffer)
    print(f"[{datetime.now()}] Waiting for job execution...")
    time.sleep(5)
    
    # Assertions
    print(f"[{datetime.now()}] Checking results...")
    
    with open("test_result.txt", "w") as f:
        # Check if run_daily_automation was called
        if sched_module.run_daily_automation.called:
            args, kwargs = sched_module.run_daily_automation.call_args
            f.write("SUCCESS: run_daily_automation was called!\n")
            f.write(f"  Called with args: {args}\n")
            f.write(f"  Called with kwargs: {kwargs}\n")
            
            if kwargs.get('scheduled_run') is True:
                 f.write("PASS: scheduled_run=True argument verified.\n")
            else:
                 f.write(f"FAIL: scheduled_run argument mismatch. Got: {kwargs}\n")
        else:
            f.write("FAIL: run_daily_automation was NOT called.\n")
        
    sched.shutdown()

if __name__ == "__main__":
    test_scheduler_trigger()
