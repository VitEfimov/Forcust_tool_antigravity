from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
from functools import lru_cache

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
    confidence_decay: Optional[float] = None
    regime_flip_prob: Optional[float] = None

def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))

def safe_expected_return(predicted: float, current: float) -> float:
    if current <= 0:
        return 0.0
    return (predicted - current) / current * 100

@lru_cache(maxsize=1)
def load_analyst_prompt() -> str:
    """Load the analyst prompt from the file."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "analyst.md"
    if not prompt_path.exists():
        return "You are a financial analyst AI. Use the provided data to generate a forecast summary."
    
    # Explicit encoding for Windows safety
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def prepare_analyst_input(data: AnalystInput) -> str:
    """
    Format the input data string to be appended to the analyst prompt.
    """
    expected_return = safe_expected_return(data.predicted_price, data.current_price)
    reliability = clamp(data.reliability)
    
    # Deterministic Schema
    lines = [
        "=== INPUT_DATA ===",
        f"symbol: {data.symbol}",
        f"horizon_days: {data.horizon}",
        f"start_price: {data.current_price:.2f}",
        f"predicted_price: {data.predicted_price:.2f}",
        f"expected_return_pct: {expected_return:+.2f}",
        f"reliability_score: {reliability:.2f}",
        f"market_regime: {data.regime}",
        "",
        # Flattened Monte Carlo (Gemini preference)
        f"monte_carlo_p10: {data.mc_p10:.2f}",
        f"monte_carlo_p50: {data.mc_p50:.2f}",
        f"monte_carlo_p90: {data.mc_p90:.2f}"
    ]
    
    if data.confidence_decay is not None:
        # Horizon-aware label
        lines.append(f"confidence_decay_{data.horizon}d: {data.confidence_decay:.2f}")
        
    if data.regime_flip_prob is not None:
        # Note: Internal field 'regime_flip_prob' maps to external 'regime_flip_probability'
        lines.append(f"regime_flip_probability: {data.regime_flip_prob:.2f}")

    return "\n".join(lines)

def generate_analyst_prompt_full(
    symbol: str, 
    wf_data: Dict[str, Any], 
    sim_data: Dict[str, Any],
    summary_mode: str = "short"  # "short" | "long"
) -> str:
    """
    Combine system prompt and data into a full prompt string.
    """
    system_prompt = load_analyst_prompt()
    
    # Check for optional future fields in wf_data
    conf_decay = wf_data.get('confidence_decay')
    flip_prob = wf_data.get('regime_flip_probability')

    # Construct DTO
    input_data = AnalystInput(
        symbol=symbol,
        horizon=wf_data.get('horizon', 10),
        current_price=wf_data.get('current_price', 0.0),
        predicted_price=wf_data.get('ml_forecast_price', wf_data.get('current_price', 0.0)),
        reliability=wf_data.get('reliability_score', 0.5),
        regime=wf_data.get('regime', 'Unknown'),
        mc_p10=sim_data.get('mc_p10', 0.0),
        mc_p50=sim_data.get('mc_p50', 0.0),
        mc_p90=sim_data.get('mc_p90', 0.0),
        confidence_decay=conf_decay,
        regime_flip_prob=flip_prob
    )
    
    data_section = prepare_analyst_input(input_data)
    
    # Output Instructions Block (Echo summary_mode in header)
    header = f"You are a financial analyst AI.\nsummary_mode: {summary_mode}\nUse the data strictly as provided.\nDo not invent prices or probabilities.\nIf confidence is low, explicitly say so."
    
    # Redundant output instruction block removed/simplified or kept for safety?
    # Keeping it as is generally safer for instruction adherence.
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

    return f"{header}\n\n{system_prompt}\n{summary_instruction}\n{data_section}"
