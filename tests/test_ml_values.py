import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.jobs.daily_run import step_2_walk_forward, step_4_simulation
from src.data.loader import DataLoader

def test_ml_values():
    print("--- Verifying ML Output Values ---")
    symbol = "SPY"
    loader = DataLoader()
    
    # Get Data
    df = loader.get_data(symbol)
    if df.empty:
        print("[FAIL] No data for SPY")
        return
        
    current_price = df['Close'].iloc[-1]
    print(f"Current Price: {current_price:.2f}")
    
    # 1. Test Walk Forward
    print("\nRunning Walk Forward (Step 2)...")
    try:
        wf_res = step_2_walk_forward(symbol, loader, horizon=10, train_window=730, step=30, use_meta=False)
        if not wf_res:
            print("[FAIL] Walk Forward returned None")
        else:
            pred = wf_res.get('ml_forecast_price')
            print(f"Prediction: {pred}")
            
            if pred == current_price:
                 print("[WARNING] Prediction equals current price (Potential Fallback/Failure)")
            else:
                 print("[SUCCESS] Prediction is distinct.")
    except Exception as e:
        print(f"[ERROR] Walk Forward crashed: {e}")

    # 2. Test Simulation
    print("\nRunning Simulation (Step 4)...")
    try:
        sim_res = step_4_simulation(symbol, loader, current_price)
        p10 = sim_res.get('mc_p10')
        p50 = sim_res.get('mc_p50')
        p90 = sim_res.get('mc_p90')
        
        print(f"P10: {p10}, P50: {p50}, P90: {p90}")
        
        if p10 == p50 == p90:
             print("[FAIL] P10 == P50 == P90 (Fallback/Flat)")
        else:
             print("[SUCCESS] Simulation values are distinct.")
             
    except Exception as e:
        print(f"[ERROR] Simulation crashed: {e}")

if __name__ == "__main__":
    test_ml_values()
