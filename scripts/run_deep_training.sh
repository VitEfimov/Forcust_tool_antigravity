#!/bin/bash

# Go to project directory
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
