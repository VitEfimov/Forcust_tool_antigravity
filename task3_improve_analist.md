1. Improve robustness & validation (HIGH IMPACT)
A. Guard against zero / invalid prices

You currently compute:

expected_return = (predicted_price - current_price) / current_price * 100


This will crash or produce inf when current_price == 0.

✅ Fix:

def safe_expected_return(predicted: float, current: float) -> float:
    if current <= 0:
        return 0.0
    return (predicted - current) / current * 100


Use it in prepare_analyst_input.

B. Clamp reliability into [0, 1]

LLMs respond poorly to invalid confidence values.

def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


Use:

reliability = clamp(reliability)

2. Make the prompt more LLM-friendly (VERY HIGH IMPACT)

LLMs behave much better when:

sections are explicit

output format is constrained

expectations are stated clearly

A. Add a structured header (system-level hint)

Append once to analyst.md or prepend dynamically:

You are a financial analyst AI.
Use the data strictly as provided.
Do not invent prices or probabilities.
If confidence is low, explicitly say so.

B. Convert DATA block to deterministic bullet schema

Change from freeform text to stable schema:

data_str = f"""
=== INPUT_DATA ===
symbol: {symbol}
horizon_days: {horizon}
start_price: {current_price:.2f}
predicted_price: {predicted_price:.2f}
expected_return_pct: {expected_return:+.2f}
reliability_score: {reliability:.2f}
market_regime: {regime}

monte_carlo:
  p10: {mc_p10:.2f}
  p50: {mc_p50:.2f}
  p90: {mc_p90:.2f}
"""


Why this matters:

Gemini is very sensitive to structured keys

GPT becomes more deterministic

Easier to parse later if you do JSON output

3. Support short vs long summaries (matches your roadmap)

You mentioned UI-friendly short vs long summaries earlier. Add a mode flag now.

A. Extend generate_analyst_prompt_full
def generate_analyst_prompt_full(
    symbol: str,
    wf_data: Dict[str, Any],
    sim_data: Dict[str, Any],
    summary_mode: str = "short"  # "short" | "long"
) -> str:

B. Inject explicit instruction
summary_instruction = f"""
=== OUTPUT_REQUIREMENTS ===
summary_mode: {summary_mode}

If summary_mode == "short":
- Max 3 bullet points
- One-sentence risk note

If summary_mode == "long":
- Detailed reasoning
- Risk factors
- Scenario analysis
"""


Final return:

return f"{system_prompt}\n{summary_instruction}\n{data_section}"

4. Make it future-proof for confidence decay & regime flips

You will want these soon.

A. Optional fields with defaults
confidence_decay = wf_data.get("confidence_decay", None)
regime_flip_prob = wf_data.get("regime_flip_probability", None)


Only include if present:

if confidence_decay is not None:
    data_str += f"\nconfidence_decay_30d: {confidence_decay:.2f}"

if regime_flip_prob is not None:
    data_str += f"\nregime_flip_probability: {regime_flip_prob:.2f}"


This avoids prompt churn later.

5. Improve file loading & caching (LOW effort, HIGH cleanliness)
A. Cache analyst prompt (no disk hit per symbol)
from functools import lru_cache

@lru_cache(maxsize=1)
def load_analyst_prompt() -> str:
    ...

B. Explicit encoding (prevents Windows issues)
with open(prompt_path, "r", encoding="utf-8") as f:

6. Add a single entry-point DTO (clean architecture)

Instead of passing many loose fields, define:

from dataclasses import dataclass

@dataclass
class AnalystInput:
    symbol: str
    horizon: int
    current_price: float
    predicted_price: float
    reliability: float
    regime: str
    mc_p10: float
    mc_p50: float
    mc_p90: float


Then:

def prepare_analyst_input(data: AnalystInput) -> str:


This:

reduces bugs

improves typing

helps testing

7. Testing recommendation (important for confidence)

Add snapshot tests:

def test_prompt_generation_snapshot():
    prompt = generate_analyst_prompt_full(...)
    assert "=== INPUT_DATA ===" in prompt
    assert "expected_return_pct" in prompt


This prevents silent prompt regressions.

Summary – What matters most

If you only do 5 things, do these:

✅ Guard expected return against zero

✅ Clamp reliability

✅ Switch to structured DATA schema

✅ Add short vs long output instruction

✅ Cache the analyst prompt

These changes directly improve forecast explanation quality, reduce hallucinations, and align perfectly with your tiered training + derived horizon architecture.