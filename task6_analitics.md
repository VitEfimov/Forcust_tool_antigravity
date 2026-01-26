FULL IMPLEMENTATION PLAN

Market Analytics + Training System

1️⃣ Core Design Principles (Lock These In)
Training Types
Type	Purpose	Frequency
Daily	Tactical + regime updates	Every market day
Deep	Structural learning	Manual / weekly
Forecast Horizons (STRICT)
Run Type	Horizons
Daily	10d, 100d
Deep	30d, 180d, 365d

🚫 Never compute unused horizons
🚫 Never infer missing horizons
✅ UI renders what exists

2️⃣ Database Schema (Canonical)
2.1 Training Runs

Tracks what happened and why

training_runs
-------------
id (uuid)
run_type          ENUM('daily', 'deep')
trigger_source    ENUM('scheduler', 'manual', 'github_actions')
started_at        TIMESTAMP
completed_at      TIMESTAMP
model_version     TEXT
status            ENUM('success', 'failed')

2.2 Per-Symbol Results (IMPORTANT)
symbol_forecasts
----------------
id (uuid)
run_id (fk → training_runs.id)

symbol            TEXT
as_of_date        DATE

horizon_days      INT        -- 10, 100, 30, 180, 365
expected_return   FLOAT      -- %
confidence        FLOAT      -- 0–1

regime            ENUM('Uptrend','Downtrend')
volatility_label  ENUM('Low','Moderate','High')

created_at        TIMESTAMP


✅ Horizons are rows, not columns
✅ Scales forever
✅ Works with daily + deep

3️⃣ Training Pipeline Logic
3.1 Daily Training Job
if run_type == "daily":
    horizons = [10, 100]


Outputs:

regime

volatility

expected_return_pct

confidence

3.2 Deep Training Job
if run_type == "deep":
    horizons = [30, 180, 365]


Heavy:

retrains long models

overwrites only deep horizons

does NOT touch daily ones

4️⃣ GitHub Actions (Correct & Safe)
4.1 Weekly Deep Training (Manual + Scheduled)
name: Weekly Deep Training

on:
  workflow_dispatch:
    inputs:
      enable_deep:
        description: "Run deep training"
        required: true
        default: "false"
  schedule:
    - cron: "0 6 * * 0"

jobs:
  train:
    runs-on: ubuntu-latest
    if: ${{ github.event_name == 'schedule' || github.event.inputs.enable_deep == 'true' }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.9"

      - run: pip install -r requirements.txt
      - run: python src/jobs/deep_train.py


🚫 No secrets in if:
✅ Uses workflow inputs correctly

5️⃣ Backend API (Clean Contract)
5.1 Market Snapshot API
GET /market/snapshot?run_type=daily


Response:

{
  "as_of": "2026-01-24",
  "symbols": [
    {
      "symbol": "AAPL",
      "price": 248.04,
      "regime": "Downtrend",
      "volatility": "Moderate",
      "forecasts": {
        "10": 2.1,
        "100": 11.3
      }
    }
  ]
}

5.2 Deep Training Trigger
POST /admin/training/deep


Effect:

creates training_run

sets run_type = deep

async job starts

6️⃣ Analytics UI (Correct Architecture)
6.1 DO NOT Analyze Market Overview Alone

❌ Bad:

count up/down only

ignores forecasts

no confidence weighting

✅ Good:

use trained outputs

aggregate by horizon

6.2 Snapshot Table (Dynamic Horizons)
const horizons = Object.keys(stock.forecasts || {})


Render dynamically:

{horizons.map(h => (
  <td key={h}>
    {stock.forecasts[h].toFixed(2)}%
  </td>
))}


🚫 No hard-coded 30d
🚫 No N/A if horizon not returned

7️⃣ Chart Logic (Correct Signals)
Regime Distribution

Based on model output, not price heuristics.

regime = forecast_100d > 0 ? "Uptrend" : "Downtrend"

Volatility Profile

From training output:

volatility_label


Not ATR / price only.

8️⃣ Historical Analytics (IMPORTANT)

Store daily snapshots of model output.

daily_market_snapshots
----------------------
date
symbol
regime
volatility
forecast_10d
forecast_100d
confidence


Your charts should read from this table — not recompute.

9️⃣ N/A RULES (FINAL)
Situation	UI Behavior
Horizon not trained	Do not render column
Value exists	Render
Deep not run yet	Daily still works

🚫 Never fake values
🚫 Never interpolate

10️⃣ Admin Controls (You Already Did This Right)

UI:

Enable Deep Training (Next Run)


Backend:

POST /admin/training/deep


GitHub:

manual button

weekly schedule

Perfect.

11️⃣ Final Mental Model (Remember This)
Market Data → Training → Stored Forecasts → Analytics UI


NOT:

Market Data → UI heuristics

✅ END STATE

You now have:

deterministic forecasts

explainable analytics

scalable horizons

zero confusion with N/A

clean daily vs deep separation