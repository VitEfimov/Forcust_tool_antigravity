#!/bin/bash
# Wrapper script for Deep Training Cronjob
# Ensures proper environment and locking

# 1. Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv" # Adjust if your venv is elsewhere
LOCK_FILE="/tmp/deep_training.lock"

# 2. Prevent Multiple Instances
if [ -f "$LOCK_FILE" ]; then
    # Check if process is actually running
    PID=$(cat "$LOCK_FILE")
    if ps -p $PID > /dev/null; then
        echo "Deep training is already running (PID: $PID). Exiting."
        exit 1
    else
        echo "Stale lock file found. Removing."
        rm "$LOCK_FILE"
    fi
fi

# Create Lock
echo $$ > "$LOCK_FILE"

# 3. Setup Environment
echo "Starting Deep Training at $(date)"
cd "$PROJECT_DIR"

# Source .env if exists (cron doesn't load it by default)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate Virtual Environment
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
elif [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
else
    echo "Warning: Virtualenv (venv or .venv) not found in $PROJECT_DIR"
fi

# 4. Run Script
# Using `python` from venv
python src/jobs/deep_train.py >> "$PROJECT_DIR/data/logs/cron_deep_train.log" 2>&1

# 5. Cleanup
rm "$LOCK_FILE"
echo "Deep Training Finished at $(date)"
