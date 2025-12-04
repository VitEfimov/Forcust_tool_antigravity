# Antigravity Stock Forecasting System

A comprehensive, multi-model forecasting engine designed to predict stock returns across multiple horizons using advanced statistical and machine-learning techniques.

## 1. Overview

Antigravity is a stock forecasting service that predicts future price returns over several timeframes:

- **10 days**
- **100 days**
- **1 year (365 days)**
- **1.5 years (547 days)**
- **2 years (730 days)**

It combines:
- **Hidden Markov Models (HMM)** for market regime detection
- **LightGBM** for return forecasting
- **Deep learning (Transformers)**
- **Volatility models (GARCH)**
- **Monte Carlo simulation**
- **Copula correlation models**
- **Kalman filtering**

This creates a robust, ensemble-based prediction engine.

## 2. Market Cycle Theory Integration

Antigravity integrates modern cycle theory to improve forecast realism.

### 2.1 Mini-Cycle (2–4 Years)
Short cycles influenced by:
- Federal Reserve policy
- Earnings seasons
- Liquidity shocks
- Market corrections

**Implementation**:
- HMM is trained on a **4-year rolling window** (~1008 trading days).
- Detects regimes such as:
    - Low-volatility bull
    - High-volatility bear
    - Transitional regimes
- **Purpose**: Understand current market “mood.”

### 2.2 Business Cycle (7–10 Years)
Full macroeconomic cycles incorporating:
- Bull markets
- Bear markets
- Crashes
- Recoveries

**Implementation**:
- LightGBM forecasters trained on **10 years** (~2520 days).
- Captures long-term structural drivers of returns.

## 3. Model Architecture (Ensemble Meta-Model)

Antigravity uses a stacked ensemble of specialized models.

```
src/models/
├── hmm_regime.py             # Market regime detection via HMM
├── lightgbm_forecaster.py    # ML regressors for multiple horizons
├── transformer_model.py      # Deep learning model for long-range patterns
├── garch_volatility.py       # Volatility modeling using GARCH
├── kalman_filter.py          # Trend extraction & noise smoothing
├── copula_correlation.py     # Multi-asset dependency modeling
├── monte_carlo.py            # Future path generation
├── rl_agent.py               # Reinforcement learning agent (optional)
└── ensemble.py               # Weighted combination of all models
```

### 3.1 Components

#### 1. LightGBM Forecaster
- Horizon-based regressors
- Learns non-linear relationships in features
- Fast and reliable for tabular financial data

#### 2. Transformer (Deep Learning)
- Captures long sequence dependencies
- Learns patterns across months and years

#### 3. GARCH(1,1)
- Models volatility clustering
- Improves risk-adjusted forecasts

#### 4. Kalman Filter
- Removes noise
- Extracts the “true” trend

#### 5. Copula Correlation
- Models dependencies between assets
- Useful for:
    - SPY ↔ VIX interactions
    - Tail-risk events
    - Crash prediction

#### 6. Regime Detection (HMM)
- Helps contextualize predictions
- Adjusts weighting for bull vs. bear regimes

### Final Forecast Formula
`Forecast = (w1 * ML_Model + w2 * Deep_Model + Adjustments) * VolatilityFactor`

## 4. Data Layer (`src/data`)

- **Source**: Yahoo Finance via `yfinance`
- **Caching**: Local Parquet files for speed
- **Symbol Resolution**:
    - “S&P 500” → SPY
    - “NASDAQ 100” → QQQ

## 5. Feature Engineering (`src/features`)

Extracts predictive signals from OHLCV data.

- **Technical Indicators**
    - RSI
    - MACD
    - Bollinger Bands
    - Moving Averages
    - Volatility metrics
- **Lag Features**
    - Lagged returns
    - Volume shifts
- **Targets**
    - `log_return(t+h) = log( Price(t+h) / Price(t) )`
    - Computed for all forecast horizons.

## 6. Modeling (`src/models`)

### 6.1 Regime Detection
- Gaussian HMM trained on 4-year rolling window.

### 6.2 Forecasting
Separate LightGBM regressors for:
- 10 days
- 100 days
- 1 year
- 1.5 years
- 2 years

### 6.3 Simulation
- Monte Carlo generates 5,000–50,000 future paths.
- **Outputs**:
    - P10 (bearish scenario)
    - P50 (median forecast)
    - P90 (bullish scenario)

## 7. Persistence Layer (`src/core/database.py`)

**SQLite schema**:

| Column | Type | Description |
| :--- | :--- | :--- |
| date | DATE | When forecast was made |
| symbol | TEXT | Stock symbol |
| horizon | INT | Forecast horizon |
| prediction | FLOAT | Model output |
| target_date | DATE | Date of targeted return |
| actual | FLOAT | Actual future return (filled later) |

**Purpose**:
- Track performance
- Fine-tune future models

## 8. API Layer (`src/api`)

Built using **FastAPI**.

### Endpoints

- **GET /forecast/{symbol}**
    - Returns:
        - Model predictions
        - Simulation bands
        - Current regime

- **GET /archive/{symbol}**
    - Historical model accuracy and stored forecasts.

- **GET /indices/history**
    - Aggregated view of: SPY, QQQ, VIX, DIA, IWM

## 9. Frontend (React + Vite)

### Pages
- **Dashboard** (charts + forecast bands)
- **Archive** (model performance)
- **Indices Overview** (market-wide perspective)
- **Market Overview** (Top 50 S&P 500 table)
- **System Status** (Model architecture status)

### Libraries
- Recharts
- Axios

## 10. Full Workflow

1. User requests symbol
2. Backend fetches + caches data
3. Models load or train if missing
4. HMM determines regime
5. Ensemble forecast is generated
6. SQLite stores prediction
7. JSON returned to frontend

## 11. Technology Stack

- **Backend**: Python 3.10+, FastAPI, Pandas / NumPy, LightGBM, hmmlearn, statsmodels (GARCH), SQLite
- **Frontend**: React, Vite, Recharts

## 12. Operational Guide

### How Often to Run?
**Ideally: 24/7**
- The system includes a **Background Scheduler** (`src/core/scheduler.py`) that runs automatically every day.
- **Daily Routine**:
    1.  **Market Close (4:00 PM ET)**: New price data becomes available.
    2.  **Data Ingestion**: System downloads the latest OHLCV data for all tracked symbols.
    3.  **Model Retraining**:
        - **LightGBM**: Retrains weekly or monthly to adapt to shifting market structures.
        - **HMM**: Re-evaluates the current market regime (Bull/Bear) daily.
        - **Kalman Filter**: Updates its state vector (Trend/Velocity) with every new price point.
    4.  **Forecast Generation**: New predictions for 10d, 100d, etc., are generated and stored.

**If running locally (not 24/7):**
- Run the application **at least once per day**, preferably after market close.
- The system will automatically catch up, fetch the latest data, and update forecasts.

## 13. How ML Improves Forecasts ("Closer to Reality")

Traditional finance models (like Linear Regression) assume the world is simple and follows a straight line. **Machine Learning (ML)** brings the forecast closer to reality by acknowledging that markets are **complex, non-linear, and chaotic**.

### 1. Learning from Mistakes (The Feedback Loop)
- **Mechanism**: Every time the model makes a prediction, it compares it to what *actually happened* later.
- **Loss Function**: The model calculates the "Error" (Difference between Prediction and Reality).
- **Optimization**: It mathematically adjusts its internal "weights" to minimize this error for next time.
- **Result**: Over time, the model "learns" which signals (e.g., RSI > 70) actually lead to price drops and which are false alarms.

### 2. Adapting to Regimes (HMM)
- **Reality**: A strategy that works in a Bull Market often fails in a Crash.
- **ML Solution**: The **Hidden Markov Model (HMM)** acts as a "Market Weather Station."
    - If HMM detects a "High Volatility / Bear" regime, the Ensemble automatically **lowers confidence** in bullish predictions or shifts weight to defensive models.
    - This prevents the system from blindly predicting "Up" during a crash.

### 3. Capturing Non-Linearity (LightGBM)
- **Reality**: Stock prices don't move in straight lines. A 1% rise in volume might mean nothing, but a 500% rise might mean a breakout.
- **ML Solution**: **Gradient Boosting (LightGBM)** uses "Decision Trees" to map these complex rules.
    - *Example Rule Learned*: "IF Volatility is LOW AND RSI is LOW, THEN Price usually goes UP. BUT IF Volatility is HIGH, ignore RSI."
    - Linear models cannot learn these "IF/THEN" exceptions. ML can.

### 4. Filtering Noise vs. Signal (Kalman Filter)
- **Reality**: Daily price changes are 90% random noise and 10% true trend.
- **ML Solution**: The **Kalman Filter** treats the price as a "Noisy Measurement" of a hidden "True Value."
    - It mathematically separates the random jitter from the underlying velocity.
    - This stops the model from overreacting to a single bad day, keeping the long-term forecast stable.

### 5. Understanding Sequences (Transformers)
- **Reality**: What happened 6 months ago can influence today (e.g., a support level established last year).
- **ML Solution**: **Transformers** (Deep Learning) use "Attention Mechanisms" to look back at the entire history and "pay attention" to specific past events that are relevant to *today*, ignoring irrelevant periods.
