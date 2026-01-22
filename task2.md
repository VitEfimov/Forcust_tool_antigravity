PRIMARY GOAL

Reduce redundant model retraining and stabilize forecasts by introducing:

Tiered symbol handling

Horizon derivation instead of retraining

Explicit training vs inference modes

Clear progress reporting

Config-controlled weekly training inside daily runs (temporarily disabled)

⚠️ IMPORTANT:
Weekly training logic must remain callable from daily runs, but must be disabled by default until server wake-up issues are fixed.

🧠 CONSTRAINTS (VERY IMPORTANT)

❌ Do NOT remove weekly training code

❌ Do NOT hard-delete training paths

❌ Do NOT change data schemas in MongoDB

✅ Use feature flags / config switches

✅ Default behavior must be SAFE (no heavy retraining)

✅ Changes must be reversible by config only

🧩 ARCHITECTURAL CHANGES TO APPLY
1️⃣ Symbol Tiering

Introduce symbol tiers via config:

symbol_tiers:
  tier_1: ["^GSPC", "^VIX", "^TNX", "DX-Y.NYB"]
  tier_2: ["AAPL", "MSFT", "NVDA", "AMZN", "META"]
  tier_3: ["ALL_OTHER"]


Rules:

Tier 1 → full retraining allowed

Tier 2 → partial / reused regime

Tier 3 → inference only (default)

2️⃣ Horizon Strategy (Critical)

Train models ONLY for base horizons:

BASE_HORIZONS = [10, 100]


Derived horizons (NO retraining):

Requested	Derived From
30	10
60	10
200	100
365	100

You must:

Store derived_from in results

Never retrain just for horizon 30/365

3️⃣ Training vs Inference Modes

Every symbol × horizon run must explicitly declare:

{
  "mode": "train | inference_only | derived",
  "trained": true | false,
  "derived_from": null | 10 | 100
}

4️⃣ Progress Reporting (Replace Fake Progress)

Old pattern:

"progress": "18/193"


New pattern:

Count logical analysis steps, not trainings

Clearly mark training vs reuse

Example:

{
  "step": "analyzing_symbol",
  "symbol": "ADBE",
  "progress": "18/42",
  "mode": "inference_only",
  "trained": false,
  "horizon": 30,
  "derived_from": 10
}

🕒 WEEKLY TRAINING IN DAILY RUNS (TEMPORARY SAFETY MODE)
Requirement

Weekly training must be callable from daily runs, but disabled by default.

Introduce config:

training:
  allow_weekly_training: false
  weekly_training_day: "Sunday"
  force_training: false


Logic:

Daily runs must check config

If allow_weekly_training = false → skip training safely

No retries, no crashes, no wake-ups

⚠️ Do NOT attempt to fix server wake-up logic yet.

📦 MongoDB (DO NOT CHANGE COLLECTIONS)

You MUST:

Fetch last successful training metadata from MongoDB

Reuse:

regime labels

feature stats

calibration factors

You MAY add fields:

trained

mode

derived_from

training_timestamp

🧪 EXPECTED OUTCOMES

After refactor:

Daily run:

0 heavy retrainings

fast, stable inference

Weekly run (when enabled later):

~8–12 total trainings

Progress numbers drop from ~193 → ~40

Forecasts become more stable across runs

🛑 DO NOT DO

Do NOT optimize wake-up logic

Do NOT parallelize training

Do NOT introduce new ML models

Do NOT remove Gemini / GPT explanation layer

✅ DELIVERABLES

Updated orchestration logic

Config-driven training switch

Clear progress + mode reporting

Horizon derivation logic

Safe defaults (no heavy compute)