❌ Issue 1: confidence_decay_30d is hardcoded but horizon varies
Code
if data.confidence_decay is not None:
    lines.append(f"confidence_decay_30d: {data.confidence_decay:.2f}")

Test
assert "confidence_decay_30d: 0.88" in output_opt

Problem

The label confidence_decay_30d assumes 30-day horizon

But data.horizon can be 10, 100, 365, etc.

This will become wrong once you use derived horizons seriously.

✅ Fix (required)

Change to horizon-aware labeling:

lines.append(
    f"confidence_decay_{data.horizon}d: {data.confidence_decay:.2f}"
)


And update tests accordingly.

❌ Issue 2: regime_flip_probability key mismatch
In generate_analyst_prompt_full
flip_prob = wf_data.get('regime_flip_probability')

In DTO
regime_flip_prob: Optional[float]

In schema output
lines.append(f"regime_flip_probability: {data.regime_flip_prob:.2f}")

Problem

You are mixing:

regime_flip_prob (internal)

regime_flip_probability (external)

This is OK internally, but you must be consistent in tests and docs.

Recommendation (keep as-is, but document)

Internal field: regime_flip_prob

Prompt field: regime_flip_probability

This is acceptable, but document it in analyst.md or comments.

❌ Issue 3: Test expects summary_mode echoed in prompt
Test
assert "summary_mode: short" in prompt_short

Code
summary_instruction = f"""
=== OUTPUT_REQUIREMENTS ===
summary_mode: {summary_mode}
...
"""


✔ This passes, but:

Problem

LLMs sometimes ignore instructions buried mid-prompt.

Recommended improvement (not required for test)

Echo summary mode in header too:

header = f"""You are a financial analyst AI.
summary_mode: {summary_mode}
Use the data strictly as provided.
...
"""


This improves Gemini compliance.

❌ Issue 4: Monte Carlo block indentation is semi-structured
monte_carlo:
  p10: ...
  p50: ...


This is fine for humans, but Gemini prefers flat key-value pairs.

Optional (but recommended) alternative

Flatten:

monte_carlo_p10: 90.00
monte_carlo_p50: 100.00
monte_carlo_p90: 110.00


Your tests don’t depend on this, so it’s optional.

3. Test Coverage Review 🧪

Your tests are excellent overall.

What you covered well

✔ DTO optional fields
✔ Clamping logic
✔ Zero-price safety
✔ Short vs long summary mode
✔ Prompt header existence

One test you should add (recommended)
def test_missing_prompt_file_fallback():
    prompt = load_analyst_prompt()
    assert "financial analyst AI" in prompt


This ensures deployment safety.

4. Final Verdict ✅
Status: VERIFIED WITH MINOR FIXES REQUIRED
Area	Status
DTO & validation	✅ Approved
Prompt structure	✅ Approved
Tests quality	✅ High
Horizon awareness	❌ Fix required
Naming consistency	⚠️ Document
LLM robustness	✅ Very good