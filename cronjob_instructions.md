# Deep Training Cronjob Setup (Ubuntu)

This guide explains how to set up the `deep_train.py` script to run automatically on your Ubuntu server.

## Prerequisites

1.  **Project Access**: Codebase is cloned to the server.
2.  **User Permissions**: You have sudo or user rights to edit crontab.
3.  **Virtual Environment**: A python venv is set up (e.g., `venv/`).

## 1. Identify Your Project Path

In your Linux terminal, navigate into the project folder and run:
```bash
pwd
```
This will give you the absolute path (e.g., `/home/vitlin/Forcust_tool_antigravity` or `/mnt/c/Users/...`). **Use this path in all steps below.**

Ensure the logs directory exists:
```bash
mkdir -p <YOUR_PATH>/data/logs
```

## 2. The Wrapper Script

The cron environment is minimal and often lacks environment variables. We use `scripts/run_deep_training.sh` to handle this.

**Verify the script exists and is executable:**
1. Navigate t
`

**Check variables in the script:**
Open the script and ensure `VENV_DIR` points to your actual virtual environment.
```bash
nano <YOUR_PATH>/scripts/run_deep_training.sh
# The script automatically detects PROJECT_DIR based on its location.
# Just ensure VENV_DIR="$PROJECT_DIR/.venv" matches your folder name.
```

## 3. Test Manually

Before adding to cron, run the wrapper manually to ensure it works.

```bash
<YOUR_PATH>/scripts/run_deep_training.sh
```
Check the output:
```bash
cat <YOUR_PATH>/data/logs/cron_deep_train.log
```
If you see "Deep Training Complete", you are good to go.

## 4. Add to Crontab

Open your crontab:
```bash
crontab -e
```

Add one of the following lines at the bottom:

**Option A: Weekly (Recommended for heavy training)**
Runs every Sunday at 2:00 AM.
```cron
0 2 * * 0 /home/ubuntu/Forcust_tool_antigravity/scripts/run_deep_training.sh
```

**Option B: Daily (If resources allow)**
Runs every night at 3:00 AM.
```cron
0 3 * * * /home/ubuntu/Forcust_tool_antigravity/scripts/run_deep_training.sh
```

保存 and exit (Ctrl+X, Y, Enter for nano).

## 5. Validation

Verify the job is listed:
```bash
crontab -l
```

Wait for the scheduled time and check the log file:
```bash
tail -f /home/ubuntu/Forcust_tool_antigravity/data/logs/cron_deep_train.log
```

## ⚠️ Important Notes

*   **Memory Usage**: Deep training can be RAM intensive (LightGBM + Transformers). If your server is small (e.g., t2.micro), consider adding swap space or running on a larger instance.
*   **Concurrency**: The wrapper script includes a **Lock File** (`/tmp/deep_training.lock`) to prevent multiple trainings from stacking up if one takes too long.
*   **Internal Scheduler**: If you are using the internal python scheduler (`main.py` or similar), ensure it is NOT also trying to run deep training to avoid conflicts. This cronjob replaces the internal scheduler for this specific task.
