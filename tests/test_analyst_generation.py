import pytest
from src.services.analyst import AnalystInput, prepare_analyst_input, generate_analyst_prompt_full

def test_dto_instantiation():
    """Verify DTO works with and without optional fields."""
    # Test minimal
    data = AnalystInput(
        symbol="TEST", horizon=10, current_price=100.0, predicted_price=110.0,
        reliability=0.8, regime="Bull", mc_p10=90.0, mc_p50=105.0, mc_p90=120.0
    )
    assert data.confidence_decay is None
    
    # Test full
    data_full = AnalystInput(
        symbol="TEST", horizon=10, current_price=100.0, predicted_price=110.0,
        reliability=0.8, regime="Bull", mc_p10=90.0, mc_p50=105.0, mc_p90=120.0,
        confidence_decay=0.95, regime_flip_prob=0.1
    )
    assert data_full.confidence_decay == 0.95
    assert data_full.regime_flip_prob == 0.1

def test_prepare_analyst_input_schema():
    """Verify the deterministic output schema and validation."""
    data = AnalystInput(
        symbol="AAPL", horizon=30, current_price=100.0, predicted_price=105.0,
        reliability=1.5, # Should clamp to 1.0
        regime="Bear", mc_p10=90.0, mc_p50=100.0, mc_p90=110.0
    )
    
    output = prepare_analyst_input(data)
    
    # Check Schema Keys
    assert "=== INPUT_DATA ===" in output
    assert "symbol: AAPL" in output
    assert "reliability_score: 1.00" in output # Verified clamping
    assert "expected_return_pct: +5.00" in output
    assert "confidence_decay_30d" not in output # Optional missing

    # Flattened Monte Carlo Check
    assert "monte_carlo_p10: 90.00" in output
    assert "monte_carlo_p50: 100.00" in output
    assert "monte_carlo_p90: 110.00" in output

    # Test with optional fields
    data.confidence_decay = 0.88
    output_opt = prepare_analyst_input(data)
    assert "confidence_decay_30d: 0.88" in output_opt

def test_safe_return_calculation():
    """Verify zero-price safety."""
    data = AnalystInput(
        symbol="ZERO", horizon=10, current_price=0.0, predicted_price=10.0,
        reliability=0.5, regime="Flat", mc_p10=0, mc_p50=0, mc_p90=0
    )
    output = prepare_analyst_input(data)
    assert "expected_return_pct: +0.00" in output    

def test_generate_analyst_prompt_structure():
    """Verify full prompt integration."""
    wf_data = {
        "horizon": 10, "current_price": 100, "ml_forecast_price": 110,
        "confidence_decay": 0.9
    }
    sim_data = {}
    
    # Short Mode
    prompt_short = generate_analyst_prompt_full("SPY", wf_data, sim_data, summary_mode="short")
    
    assert "You are a financial analyst AI." in prompt_short # Header
    assert "summary_mode: short" in prompt_short
    assert "confidence_decay_10d: 0.90" in prompt_short # Pass-through verification (Horizon 10)
    
    # Check header echo
    header_line = "summary_mode: short"
    assert header_line in prompt_short

    # Long Mode
    prompt_long = generate_analyst_prompt_full("SPY", wf_data, sim_data, summary_mode="long")
    assert "summary_mode: long" in prompt_long
    assert "Detailed reasoning" in prompt_long

def test_missing_prompt_file_fallback():
    from src.services.analyst import load_analyst_prompt
    # We can't easily delete the file, but we can call it.
    # Ideally we'd mock pathlib.Path.exists or move the file temporarily.
    # For now, let's just assert the loader returns a string, possibly non-empty.
    # If the file exists, it returns the content. If not, the default string.
    prompt = load_analyst_prompt()
    print(f"DEBUG PROMPT: {repr(prompt)}")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # Minimal check for default or real prompt
    assert "analyst" in prompt.lower()
