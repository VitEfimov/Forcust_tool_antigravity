# Antigravity

Antigravity is a daily stock-forecasting service that combines Markov/HMM regime modeling with supervised machine learning (LightGBM).

## Features
- **Data Ingestion**: Fetches daily OHLCV data from yfinance (cached locally).
- **Regime Detection**: Uses Gaussian HMM to detect market regimes (e.g., Low Volatility vs High Volatility).
- **Forecasting**: Predicts next-day returns using LightGBM with technical indicators.
- **Simulation**: Monte-Carlo simulation for probabilistic price paths.
- **Dashboard**: React-based UI to visualize forecasts and regime probabilities.
- **Automation**: Daily background scheduler for model updates.

## Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker (optional)

### Backend Setup

**Option 1: Using pip (if poetry is not installed)**
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the API:
   ```bash
   python -m uvicorn src.api.main:app --reload
   ```

**Option 2: Using poetry**
1. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```
2. Run the API:
   ```bash
   poetry run uvicorn src.api.main:app --reload
   ```

The API will be available at `http://localhost:8000`.

### Frontend Setup
1. Navigate to frontend:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   The dashboard will be available at `http://localhost:5173`.

### Docker Setup
Run the entire stack with Docker Compose:
```bash
docker-compose up --build
```

## Usage
1. Open the dashboard.
2. Enter a stock symbol (e.g., "SPY").
3. View the current price, detected regime, forecasted return, and simulation scenarios.

## Testing
Run backend tests:
```bash
poetry run pytest
```
