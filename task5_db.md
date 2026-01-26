REQUIRED CHANGES (SHORT MODE)
1️⃣ Fix GitHub Actions condition (weekly training)

Use only secrets, no vars, no env logic:

if: ${{ secrets.ALLOW_WEEKLY_TRAINING == 'true' }}


(What you already have now is correct.)

2️⃣ Add hard safety guard in Python

In weekly_train.py:

if not settings.ALLOW_WEEKLY_TRAINING and not settings.FORCE_TRAINING:
    logger.warning("Weekly training blocked by config")
    return


Never rely on CI alone.

3️⃣ Fix derived horizon price logic (CRITICAL)

Stop copying spot price.

Implement log-return scaling:

base_return = math.log(base_pred / base_price)
scaled_return = base_return * math.sqrt(target_horizon / base_horizon)
derived_price = base_price * math.exp(scaled_return)

4️⃣ Add confidence decay for long horizons

Prevent fake high confidence:

derived_confidence = base_confidence * math.exp(-0.015 * (target_horizon / base_horizon))

5️⃣ Enforce derived ≠ spot price

Add guard:

if mode == "derived" and abs(predicted_price - start_price) < 1e-6:
    logger.warning("Derived forecast collapsed to spot price")

6️⃣ Cache DB reads per run

In daily_run.py:

Load latest results once per symbol

Pass down to all jobs

(Result: much lower DB load.)

7️⃣ Sanitize Monte Carlo NaNs

Before saving or using:

if any(math.isnan(v) for v in [mc_p10, mc_p50, mc_p90]):
    skip_symbol()

8️⃣ Analyst cost control

Prevent expensive summaries on lower tiers:

if tier != TIER_1 and summary_mode == "long":
    summary_mode = "short"



REQUIRED CHANGES (SHORT MODE)
1️⃣ Fix GitHub Actions condition (weekly training)

Use only secrets, no vars, no env logic:

if: ${{ secrets.ALLOW_WEEKLY_TRAINING == 'true' }}


(What you already have now is correct.)

2️⃣ Add hard safety guard in Python

In weekly_train.py:

if not settings.ALLOW_WEEKLY_TRAINING and not settings.FORCE_TRAINING:
    logger.warning("Weekly training blocked by config")
    return


Never rely on CI alone.

3️⃣ Fix derived horizon price logic (CRITICAL)

Stop copying spot price.

Implement log-return scaling:

base_return = math.log(base_pred / base_price)
scaled_return = base_return * math.sqrt(target_horizon / base_horizon)
derived_price = base_price * math.exp(scaled_return)

4️⃣ Add confidence decay for long horizons

Prevent fake high confidence:

derived_confidence = base_confidence * math.exp(-0.015 * (target_horizon / base_horizon))

5️⃣ Enforce derived ≠ spot price

Add guard:

if mode == "derived" and abs(predicted_price - start_price) < 1e-6:
    logger.warning("Derived forecast collapsed to spot price")

6️⃣ Cache DB reads per run

In daily_run.py:

Load latest results once per symbol

Pass down to all jobs

(Result: much lower DB load.)

7️⃣ Sanitize Monte Carlo NaNs

Before saving or using:

if any(math.isnan(v) for v in [mc_p10, mc_p50, mc_p90]):
    skip_symbol()

8️⃣ Analyst cost control

Prevent expensive summaries on lower tiers:

if tier != TIER_1 and summary_mode == "long":
    summary_mode = "short"