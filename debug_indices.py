
import pandas as pd
import numpy as np
import sys
# Add src to path
sys.path.append('.')
from src.features.pipeline import FeaturePipeline

def test_pipeline_indices():
    # 1. Create Mock Main DF (SPY)
    dates = pd.date_range(start="2023-01-01", periods=50)
    df = pd.DataFrame({
        "Open": 100 + np.random.randn(50),
        "High": 105 + np.random.randn(50),
        "Low": 95 + np.random.randn(50),
        "Close": 100 + np.random.randn(50),
        "Volume": 1000
    }, index=dates)

    # 2. Create Mock External Data
    # HYG (Junk)
    hyg = pd.DataFrame({"Close": 75 + np.random.randn(50)}, index=dates)
    # LQD (Grade)
    lqd = pd.DataFrame({"Close": 105 + np.random.randn(50)}, index=dates)
    # VVIX
    vvix = pd.DataFrame({"Close": 90 + np.random.randn(50)}, index=dates)

    external_data = {
        "HYG": hyg,
        "LQD": lqd,
        "^VVIX": vvix
    }

    # 3. Run Pipeline
    pipeline = FeaturePipeline()
    print("Running pipeline...")
    processed = pipeline.prepare_features(df, external_data)

    # 4. Verify Columns
    print("Columns:", processed.columns.tolist())
    
    errors = []
    if "Credit_Spread_Ratio" not in processed.columns:
        errors.append("Missing Credit_Spread_Ratio")
    else:
        print("[OK] Credit_Spread_Ratio found")
        print("Sample Spread:", processed['Credit_Spread_Ratio'].iloc[-1])

    if "^VVIX_Close" not in processed.columns:
        errors.append("Missing ^VVIX_Close")
    else:
        print("[OK] ^VVIX_Close found")

    if errors:
        print("ERRORS:", errors)
    else:
        print("SUCCESS: All new features present.")

if __name__ == "__main__":
    test_pipeline_indices()
