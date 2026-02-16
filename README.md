# Antigravity: Advanced Market Forecasting System

Antigravity is a professional-grade stock forecasting, simulation, and analysis platform. It combines **statistical mechanics** (Regime-Switching GARCH) with **supervised machine learning** (LightGBM) to provide a multi-layered view of future market behavior.

## Core Capabilities

### 1. Market Overview (Macro View)
- **High-Speed Analysis**: Instantly scan the Top 50 S&P 500 stocks.
- **Smart Forecasts**: Uses a **Capped Analytical Drift** model to project 10d to 2-year returns without "infinite growth" errors.
- **Regime Detection**: Real-time classification of simulated volatility states (Low/High Volatility, Trending/Mean-Reverting).

### 2. Advanced Simulation (Deep Dive)
- **Engine**: "V2" Regime-Switching GARCH + Student-t Innovations + Jump Diffusion.
- **Precision**: Runs 2,000+ Monte Carlo paths per request to map out the full probability distribution (P10 Bear, P50 Base, P90 Bull).
- **Use Case**: Stress-testing specific stocks (e.g., "What is the 90th percentile outcome for high-beta stocks in a crash regime?").

### 3. ML Training Lab (Custom Alpha)
- **Exogenous Variables**: Train custom models that learn from broad market drivers (S&P 500, VIX, 10Y Yield, Oil, Gold).
- **On-the-Fly Learning**: Select your target stock and feature set, and the system dynamically fetches, aligns, and trains a **LightGBM** regressor.
- **Multi-Horizon**: Automatically generates forecasts for 10d, 30d, 100d, and 365d horizons.

### 4. Custom Watchlist
- **Personalized Tracking**: Add/remove specific tickers.
- **Full Power**: Unlike the standard overview, your watchlist runs the **Full V2 Simulation** in parallel for every item, giving maximum fidelity for your portfolio.

## Tech Stack
- **Backend**: Python (FastAPI), ThreadPoolExecutor (Parallelism), NumPy/Pandas (Vectorized Math), Arch/LightGBM (Modeling).
- **Frontend**: React (Vite), Recharts (Visualization), Concurrent Mode.
- **Data**: yfinance (Live), persistent local caching for speed.

## Quick Start

### 1. Backend
Run from the project root (`Forcust_tool_antigravity`):
```bash
# Install dependencies
pip install -r requirements.txt

# Start API (Hot Reload)
python -m uvicorn src.api.main:app --reload
```
*API: http://localhost:8000*

### 2. Frontend
Open a new terminal:
```bash
cd frontend
npm install
npm run dev
```
*Dashboard: http://localhost:5173*

## Usage Guide

1.  **Dashboard**: Quick check of your primary assets.
2.  **Market Overview**: Scan for opportunities (sort by "2Y Forecast" to find growth candidates).
3.  **Advanced Simulation**: Dive deep into a specific ticker. Check "Conservative Mode" to stress-test against fat tails.
4.  **ML Training**: Go to the "ML Training" tab. Select `^VIX` and `^TNX` (Treasury Yield) to train a model that understands fear and interest rates.

### 5. Deep Training (Full Run)
To run the full deep learning training pipeline (HMM, Transformer, LightGBM) for all horizons:
```bash
# Run from project root
export PYTHONPATH=$(pwd)
python src/jobs/deep_train.py
```
*Note: This process is resource-intensive. Ensure you have sufficient memory or configure `TRANSFORMER_BATCH_SIZE` in `.env`.*

