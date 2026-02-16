# Deep Training Cronjob Setup (Ubuntu)

## Prerequisites
- **OS**: Ubuntu 20.04+ (or similar Linux distro)
- **Software**: Python 3.9+, Git, Virtualenv
- **Hardware**: Dedicated worker instance recommended (1GB+ RAM) to avoid OOM on API server.

## 1. Clone Repository
```bash
git clone <repo-url>
cd Forcust_tool_antigravity
```

## 2. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the root directory with your production configuration:
```bash
nano .env
```
(Include `DATABASE_URL`, `API_URL`, etc.)

## 3. Test Manually
Verify the script runs correctly before automating:
```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
# Optional: Set limits for test run
export TRANSFORMER_BATCH_SIZE=8 
export DEEP_TRAINING_ENABLED=true

python src/jobs/deep_train.py
```
Check logs (`logs/deep_train_*.log` or console output) for "STARTING DEEP TRAINING JOB".

## 4. Create Wrapper Script
The wrapper script ensures the environment is loaded and prevents overlapping runs.

Create the file `scripts/run_deep_training.sh`:
```bash
nano scripts/run_deep_training.sh
```

Paste the following content:
```bash
#!/bin/bash

# Go to project directory (UPDATE PATH for your user)
cd /home/ubuntu/Forcust_tool_antigravity || exit 1

# Activate virtual environment
source .venv/bin/activate

# Load environment variables
set -a
source .env
set +a

# Prevent overlapping runs (extra safety)
LOCKFILE="/tmp/deep_training.lock"

if [ -f "$LOCKFILE" ]; then
  echo "$(date) - Skipping deep training (lock exists)" >> logs/cron.log
  exit 0
fi

touch "$LOCKFILE"

# Run training
echo "$(date) - Starting deep training" >> logs/cron.log
python src/jobs/deep_train.py >> logs/deep_train_cron.log 2>&1

# Cleanup
rm -f "$LOCKFILE"
echo "$(date) - Finished deep training" >> logs/cron.log
```

Make it executable:
```bash
chmod +x scripts/run_deep_training.sh
```

## 5. Add Cronjob
Open the crontab editor:
```bash
crontab -e
```

Add your schedule. 

**Example: Weekly (Sunday at 3 AM)**
```cron
0 3 * * 0 /home/ubuntu/Forcust_tool_antigravity/scripts/run_deep_training.sh
```

**Example: Daily (2 AM)**
```cron
0 2 * * * /home/ubuntu/Forcust_tool_antigravity/scripts/run_deep_training.sh
```

## 6. Verify Cron Setup
List cron jobs to confirm:
```bash
crontab -l
```

Test the wrapper script manually:
```bash
bash scripts/run_deep_training.sh
```

Check the logs to verify execution:
```bash
tail -f logs/cron.log
tail -f logs/deep_train_cron.log
```

## ⚠️ Critical Note on Memory (OOM)
If you are running on small instances (e.g., 512MB RAM):
1. **Isolate Workloads**: Do NOT run Deep Training on the exact same instance as your API server if possible.
2. **Disable Internal Scheduler**: Ensure `src/jobs/daily_run.py` or the API server is NOT also triggering deep training internally. Set `DEEP_TRAINING_ENABLED=false` in the API/Scheduler environment if you are using cron, OR ensure the scheduler logic checks for the same lockfile/flag.
