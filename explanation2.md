# Antigravity System Explanation (Current State)

This document explains the **current, verified architecture** of the Antigravity forecasting engine as of the latest deployment.

## 1. System Philosophy: "Hybrid Fidelity"

The system is designed with a "Hybrid Fidelity" architecture to balance **speed** vs. **precision**.

| Module | Speed | Precision | Methodology |
| :--- | :--- | :--- | :--- |
| **Market Overview** | Instant | Low (Approximation) | **Capped Analytical Drift** (Geometric Brownian Motion) |
| **Watchlist** | Medium | High (Full Simulation) | **V2 Parallel Simulation** (GARCH + Jump) |
| **Forecast Detail** | Fast | High (Ensemble) | **Ensemble Meta-Model** (ML + Kalman + Volatility) |
| **Simulation Lab** | Slow | Maximum (Stress Test) | **V2 Regime-Switching GARCH** (2,000 Paths) |
| **ML Training Lab** | Variable | Custom | **LightGBM** with Exogenous Indices |

---

## 2. Core Engines

### A. The "V2" Simulation Engine (`src/models/advanced_simulation.py`)
Used for the Watchlist and Advanced Simulation tab.
1.  **Regime Detection**: Uses a Hidden Markov Model (HMM) to classify the last 8 years of returns into 3 regimes (e.g., Low Vol Bull, High Vol Bear, Transition).
2.  **GARCH(1,1)**: Fits a volatility model *per regime*. This captures how volatility clusters (calm days follow calm days, panic follows panic).
3.  **Student-t Shocks**: Instead of a Bell Curve (Normal), it uses a Student-t distribution to allow for "Fat Tails" (extreme events are more likely than theory suggests).
4.  **Jump Diffusion**: Adds random Poisson jumps (sudden +/- 10% gaps) to mimic news shocks.
5.  **Robust Fallback**: If GARCH fails to converge (common in microcaps), it automatically falls back to a **Robust Block Bootstrap** method.

### B. The Ensemble Forecast Engine (`src/models/ensemble.py`)
Used for the "ML Forecast" column on the Dashboard.
It combines 4 distinct signals into one meta-prediction:
1.  **LightGBM**: Learns non-linear patterns (RSI, Moving Averages).
2.  **Transformer**: (Placeholder) Deep learning for sequence patterns.
3.  **Kalman Filter**: Extracts the "True Trend" slope, filtering out daily noise.
4.  **GARCH Volatility**: Adjusts confidence based on market stability.

**Formula**: `Final = (Weights * Models) + Trend_Factor + Regime_Adjustment`

---

## 3. Key Workflows

### 1. Market Overview (S&P 500)
- **Goal**: Scan 50 stocks instantly.
- **Logic**: Uses a simplified analytical formula (`Drift = Mean - 0.5*Sigma^2`).
- **Safety**: Applies a **Capped Drift** logic (Max +60% annualized) to prevent "infinite growth" errors on high-momentum stocks like Nvidia or Google.

### 2. ML Training Lab (Custom Alpha)
- **Goal**: Find hidden correlations between a stock (e.g., AAPL) and macro drivers (e.g., Oil, Gold, VIX).
- **Process**:
    1.  User selects indices (e.g., `^VIX`, `^TNX`).
    2.  System fetches history for all assets.
    3.  Aligns dates and generates lag features.
    4.  Trains a LightGBM regressor.
    5.  Returns **RMSE/MAE** with a "Quality Score" (Excellent/Good/Fair).

---

## 4. Technical Stack

- **Backend**: FastAPI (Python)
    - `ThreadPoolExecutor`: Used to parallelize the Watchlist simulations.
    - `yfinance`: Live data source.
    - `joblib`: Model persistence.
- **Frontend**: React (Vite)
    - `Recharts`: Visualization.
    - `Axios`: API communication.

## 5. Directory Structure (Key Files)
- `src/api/routes.py`: Main API logic, Ensemble integration, Capped Drift logic.
- `src/models/advanced_simulation.py`: The mathematics of the V2 engine.
- `src/features/pipeline.py`: Feature engineering (RSI, MACD) + Exogenous merging.
- `src/models/ensemble.py`: The weighting logic for the final forecast.
