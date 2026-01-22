

      - name: Wake Render Server
        run: |
          curl --fail ${{ secrets.RENDER_BACKEND_URL }}/system/status

      - name: Run Daily Automation
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          ALLOW_WEEKLY_TRAINING: "false"
        run: |
          python src/jobs/daily_run.py
✔ What this does
Runs every day

Does inference + derived horizons

NO heavy training

Safe if Render sleeps

4️⃣ Weekly Training Workflow (Disabled by Default)
.github/workflows/weekly_training.yml
name: Weekly Training

on:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * 0" # Sunday 1AM EST

jobs:
  train:
    runs-on: ubuntu-latest
    timeout-minutes: 90

    if: ${{ secrets.ALLOW_WEEKLY_TRAINING == 'true' }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ secrets.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Wake Render
        run: |
          curl --fail ${{ secrets.RENDER_BACKEND_URL }}/system/status

      - name: Run Weekly Training
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          ALLOW_WEEKLY_TRAINING: "true"
          FORCE_TRAINING: "true"
        run: |
          python src/jobs/weekly_train.py
✔ Why this is safe
Disabled by default

Manual override only

Cannot accidentally trigger

5️⃣ Market Overview Workflow
.github/workflows/market_overview.yml
name: Market Overview

on:
  schedule:
    - cron: "0 14 * * 1-5" # Market open
    - cron: "15 20 * * 1-5" # Market close
  workflow_dispatch:

jobs:
  overview:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      - name: Wake Render
        run: |
          curl --fail ${{ secrets.RENDER_BACKEND_URL }}/system/status

      - name: Run Market Overview
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python src/jobs/market_overview.py
6️⃣ Code Changes Required (Minimal)
In config.py
ALLOW_WEEKLY_TRAINING = os.getenv("ALLOW_WEEKLY_TRAINING", "false") == "true"
FORCE_TRAINING = os.getenv("FORCE_TRAINING", "false") == "true"
7️⃣ Remove Local Scheduler for Production
IMPORTANT
In Render:

if settings.ENV == "production":
    DO NOT start APScheduler
GitHub Actions is now the scheduler.

8️⃣ Observability & Safety
Add Heartbeat Logging
Each workflow should log:

{
  "workflow": "daily_automation",
  "mode": "safe",
  "weekly_training": false,
  "timestamp": "..."
}
This makes debugging trivial.

9️⃣ Verification Checklist
First Run
Manually run Daily Automation

Confirm:

No training logs

Derived horizons exist

Render stays awake during run

Weekly Training (Later)
Flip:

ALLOW_WEEKLY_TRAINING=true
Manually trigger workflow

Confirm Tier-1 training only

