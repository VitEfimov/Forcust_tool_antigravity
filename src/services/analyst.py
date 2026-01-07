from typing import Dict, Any
from pathlib import Path

def load_analyst_prompt() -> str:
    """Load the analyst prompt from the file."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "analyst.md"
    if not prompt_path.exists():
        return ""
    with open(prompt_path, "r") as f:
        return f.read()

def prepare_analyst_input(
    symbol: str,
    horizon: int,
    current_price: float,
    predicted_price: float,
    reliability: float,
    regime: str,
    mc_p10: float,
    mc_p50: float,
    mc_p90: float
) -> str:
    """
    Format the input data string to be appended to the analyst prompt.
    """
    expected_return = (predicted_price - current_price) / current_price * 100
    
    data_str = f"""
DATA:
- Asset symbol: {symbol}
- Forecast horizon: {horizon} Days
- Predicted price: {predicted_price:.2f}
- Start price: {current_price:.2f}
- Expected return: {expected_return:+.2f}%
- Reliability score: {reliability:.2f} (0-1)
- Market regime label: {regime}
- Monte Carlo percentile ranges:
  - p10: {mc_p10:.2f}
  - p50: {mc_p50:.2f}
  - p90: {mc_p90:.2f}
"""
    return data_str

def generate_analyst_prompt_full(
    symbol: str, 
    wf_data: Dict[str, Any], 
    sim_data: Dict[str, Any]
) -> str:
    """
    Combine system prompt and data into a full prompt string.
    """
    system_prompt = load_analyst_prompt()
    
    horizon = wf_data.get('horizon', 10) # default or extract
    price = wf_data.get('current_price', 0.0)
    ml_forecast = wf_data.get('ml_forecast_price', price)
    rel_score = wf_data.get('reliability_score', 0.5)
    regime = wf_data.get('regime', 'Unknown')
    
    mc_p10 = sim_data.get('mc_p10', price)
    mc_p50 = sim_data.get('mc_p50', price)
    mc_p90 = sim_data.get('mc_p90', price)
    
    data_section = prepare_analyst_input(
        symbol=symbol,
        horizon=horizon,
        current_price=price,
        predicted_price=ml_forecast,
        reliability=rel_score,
        regime=regime,
        mc_p10=mc_p10,
        mc_p50=mc_p50,
        mc_p90=mc_p90
    )
    
    return f"{system_prompt}\n\n{data_section}"
