import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import ta
import joblib
from pathlib import Path
from typing import Dict, Optional, Callable
from datetime import timedelta
from .meta_learner import MetaLearner

RND = 42
np.random.seed(RND)


def calc_sharpe(returns, rf_rate=0.0, periods_per_year=252):
    """Returns annualized Sharpe ratio using log returns array."""
    if len(returns) == 0:
        return np.nan
    mean = np.mean(returns) - rf_rate / periods_per_year
    vol = np.std(returns, ddof=1)
    if vol == 0 or np.isnan(vol):
        return np.nan
    return (mean * periods_per_year) / (vol * np.sqrt(periods_per_year))


def max_drawdown(equity_curve):
    """equity_curve is an array-like of cumulative portfolio values."""
    arr = np.asarray(equity_curve)
    highwater = np.maximum.accumulate(arr)
    dd = (arr - highwater) / highwater
    return float(np.min(dd)), int(np.argmin(dd))  # value (negative), index


class WalkForwardForecaster:
    def __init__(
        self,
        symbol: str,
        df: pd.DataFrame,
        external_data: Optional[Dict[str, pd.DataFrame]] = None,
        prediction_horizon: int = 10,
        trade_horizon: Optional[int] = None,
        train_window: int = 2520,
        step: int = 1,
        model_params: Optional[dict] = None,
        save_models: bool = False,
        models_dir: str = "models",
        transaction_cost: float = 0.0,   # e.g., 0.0005 = 5 bps per trade
        slippage: float = 0.0,          # e.g., 0.0005 = 5 bps slippage per trade
        use_meta_learner: bool = True,  # Toggle for Meta-Learning
        verbose: bool = True,
        log_func: Optional[Callable[[str], None]] = None,
    ):
        """
        Enhanced Walk-Forward Forecaster.

        - prediction_horizon: days ahead the model is trained to predict (H)
        - trade_horizon: days you hold the trade (if None, equals prediction_horizon)
        - train_window: training window size in trading days
        - step: how many days to advance each fold
        - transaction_cost/slippage are applied as absolute fractions of price
        - use_meta_learner: If True, uses the secondary reliability model to adjust predictions.
        """
        self.symbol = symbol
        self.df = df.copy()
        self.external_data = external_data or {}
        self.prediction_horizon = prediction_horizon
        self.trade_horizon = prediction_horizon if trade_horizon is None else trade_horizon
        self.train_window = train_window
        self.step = step
        self.model_params = model_params or {}
        self.save_models = save_models
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.transaction_cost = float(transaction_cost)
        self.slippage = float(slippage)
        self.use_meta_learner = use_meta_learner
        self.use_meta_learner = use_meta_learner
        self.verbose = verbose
        self.log_func = log_func if log_func else print

        # internal
        self.feature_cols = None
        self.results_df = None
        self.equity_curve = None
        
        # Meta-Learner
        self.meta_learner = MetaLearner(verbose=verbose, log_func=self.log_func)

    def log(self, msg: str):
        if self.verbose:
            self.log_func(msg)

    # ---------------- Feature engineering ---------------- #
    def _merge_external(self, df: pd.DataFrame) -> pd.DataFrame:
        """Join external_data dict by index (date). Create simple features like 5d return."""
        df = df.copy()
        for name, ext_df in (self.external_data or {}).items():
            if 'Close' not in ext_df.columns:
                continue
            # ensure ext_df index is datetime and sorted
            ext = ext_df[['Close']].rename(columns={'Close': f"{name}_Close"}).copy()
            ext.index = pd.to_datetime(ext.index)
            df = df.join(ext, how='left')
            df[f"{name}_Close"] = df[f"{name}_Close"].ffill()
            # simple derived features
            df[f"{name}_Ret_5d"] = df[f"{name}_Close"].pct_change(5).fillna(0)
        return df

    def prepare_features(self) -> pd.DataFrame:
        """
        Create features and the prediction target.
        - Uses only past-looking rolling computations (no leakage).
        - Target is log return at prediction_horizon.
        """
        df = self.df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index(ascending=True)

        # Merge external
        df = self._merge_external(df)

        # Basic technicals (TA library is past-looking)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['MACD'] = ta.trend.macd_diff(df['Close'])
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
        df['Vol_20'] = df['Close'].pct_change().rolling(20, min_periods=1).std()
        df['Vol_100'] = df['Close'].pct_change().rolling(100, min_periods=1).std()
        df['Regime_Vol'] = (df['Vol_20'] > df['Vol_100']).astype(int)

        # Moving averages distances
        df['SMA_50'] = df['Close'].rolling(50, min_periods=1).mean()
        df['SMA_200'] = df['Close'].rolling(200, min_periods=1).mean()
        df['SMA_50_Dist'] = (df['Close'] / df['SMA_50'] - 1)
        df['SMA_200_Dist'] = (df['Close'] / df['SMA_200'] - 1)

        # Momentum
        df['Mom_10'] = df['Close'].pct_change(10).fillna(0)
        df['Mom_30'] = df['Close'].pct_change(30).fillna(0)

        # Short returns
        df['Ret_1'] = df['Close'].pct_change(1).fillna(0)
        df['Ret_3'] = df['Close'].pct_change(3).fillna(0)
        df['Ret_5'] = df['Close'].pct_change(5).fillna(0)

        # Target: log-return H days ahead
        future_close = df['Close'].shift(-self.prediction_horizon)
        df['Target'] = np.log(future_close / df['Close'])
        df['Target_Price'] = future_close

        # Compose feature column list (exclude raw OHLCV, target, and external raw close if you prefer)
        exclude = {'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Target', 'Target_Price'}
        cols = [c for c in df.columns if c not in exclude]
        self.feature_cols = cols

        if self.verbose:
            self.log_func(f"[prepare_features] {len(df)} rows, {len(self.feature_cols)} features")

        return df

    # ---------------- Walk-forward / run ---------------- #
    def run(self, save_models: Optional[bool] = None) -> pd.DataFrame:
        """
        Execute walk-forward training. Returns a DataFrame with per-fold results.
        """
        if save_models is None:
            save_models = self.save_models

        data = self.prepare_features()
        n = len(data)
        if n < self.train_window + self.prediction_horizon:
            raise ValueError("Not enough data for the chosen train_window + prediction_horizon")

        current_idx = self.train_window
        records = []
        cum_log = 0.0
        
        # We need this for equity curve reconstruction
        # (Start with 1.0)
        
        fold = 0
        while current_idx < n:
            fold += 1
            train_start = current_idx - self.train_window
            train_end = current_idx
            train_df = data.iloc[train_start:train_end]
            
            # Skip if too small (edge case)
            if len(train_df) < max(200, int(self.train_window * 0.2)):
                current_idx += self.step
                continue

            X_train = train_df[self.feature_cols].values
            y_train = train_df['Target'].values

            test_row = data.iloc[[current_idx]]
            X_test = test_row[self.feature_cols].values.reshape(1, -1)

            current_price = float(data['Close'].iloc[current_idx])
            actual_future_price = float(data['Target_Price'].iloc[current_idx])
            actual_log_ret = float(data['Target'].iloc[current_idx])
            date_t = data.index[current_idx]

            # Scale
            scaler = StandardScaler()
            X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=self.feature_cols)
            X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=self.feature_cols)

            # Train Model
            model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=31, verbosity=-1, n_jobs=-1)
            model.fit(X_train_scaled, y_train)
            raw_pred_log_ret = float(model.predict(X_test_scaled)[0])

            # Meta-Learning Integration
            reliability_score = 1.0
            if self.use_meta_learner and len(records) >= 20: 
                try:
                    # Construct Meta History
                    meta_history = pd.DataFrame(records)
                    meta_history['Error'] = meta_history['pred_log_ret'] - meta_history['actual_log_ret']
                    meta_history['date'] = pd.to_datetime(meta_history['date'])
                    
                    # Merge Market Data (cols like VIX, etc from 'data')
                    market_cols = [c for c in data.columns if 'VIX' in c or 'SPY' in c or 'Close' == c] 
                    meta_train_df = pd.merge(meta_history, data[market_cols], left_on='date', right_index=True, how='left')
                    
                    # Train Meta-Learner
                    self.meta_learner.train(meta_train_df, 'pred_log_ret', 'actual_log_ret')
                    
                    # Predict Reliability
                    # Context: Recent History + Current Row Test
                    recent_history = meta_train_df.tail(30).copy()
                    
                    # We must align columns for concat
                    # test_row has market cols but no 'Error', 'pred_', 'actual_'
                    # We can direct pass test_row if we handle cols in predict? 
                    # Helper construction:
                    current_context_row = test_row.copy()
                    current_context = pd.concat([recent_history, current_context_row], axis=0, ignore_index=True)
                    
                    reliability_score = self.meta_learner.predict_reliability(current_context)
                except Exception as e:
                    if self.verbose: self.log_func(f"Meta-Learner Error: {e}")
                    reliability_score = 1.0

            # Apply Reliability
            final_pred_log_ret = raw_pred_log_ret * reliability_score
            
            # Trading PnL Logic
            # Direction
            pred_direction = np.sign(final_pred_log_ret) if final_pred_log_ret != 0 else 0
            
            # Realized (Exit at H)
            trade_horizon = self.trade_horizon
            exit_idx = min(current_idx + trade_horizon, n - 1)
            exit_price = float(data['Close'].iloc[exit_idx])
            realized_log_ret = np.log(exit_price / current_price)
            
            # Cost
            total_cost = self.transaction_cost + self.slippage
            realized_mult = np.exp(realized_log_ret) * (1 - total_cost)
            realized_effective = np.log(realized_mult) if realized_mult > 0 else -999.0
            
            # Trade PnL
            # If pred_direction matches trade, we get return.
            # Here simple: Always take trade in direction of sign?
            if pred_direction == 0:
                trade_log_return = 0.0
            else:
                 trade_log_return = pred_direction * realized_effective
            
            cum_log += trade_log_return
            equity = np.exp(cum_log)
            
            # Record
            records.append({
                "fold": fold,
                "date": date_t,
                "current_price": current_price,
                "pred_price": current_price * np.exp(final_pred_log_ret),
                "actual_future_price": actual_future_price,
                "pred_log_ret": final_pred_log_ret, # We store Adjusted as main
                "actual_log_ret": actual_log_ret,
                "direction_correct": (np.sign(final_pred_log_ret) == np.sign(actual_log_ret)),
                "trade_log_return": trade_log_return,
                "cumulative_log_return": cum_log,
                "equity": equity,
                "regime": "N/A", # Base doesn't have regime classifier here unless I re-add it
                "regime_mult": 1.0,
                "base_pred": raw_pred_log_ret,
                "reliability": reliability_score,
                "realized_log_ret": realized_log_ret
            })
            
            if self.verbose and (fold % 50 == 0 or fold == 1):
                self.log_func(f"[fold {fold}] date={date_t.date()} pred={final_pred_log_ret:.5f} actual={actual_log_ret:.5f} equity={equity:.4f}")
                
            current_idx += self.step

        self.results_df = pd.DataFrame(records).set_index('fold') if records else pd.DataFrame()
        self.equity_curve = pd.Series([1.0] + [r['equity'] for r in records], index=[0] + [r['fold'] for r in records]) if records else pd.Series([1.0])
        
        return self.results_df

    # ---------------- Performance reporting ---------------- #
    def performance_report(self, periods_per_year: int = 252) -> Dict[str, float]:
        if self.results_df is None:
            raise RuntimeError("Run the forecaster first with .run()")

        df = self.results_df.copy()
        # total strategy return
        total_log = df['cumulative_log_return'].iloc[-1]
        final_value = float(np.exp(total_log))
        total_return_pct = (final_value - 1.0) * 100.0

        # benchmark: buy-and-hold realized over same trade periods (sum of realized_log_ret)
        benchmark_log = df['realized_log_ret'].sum()
        benchmark_value = float(np.exp(benchmark_log))
        benchmark_return_pct = (benchmark_value - 1.0) * 100.0

        # per-trade returns series
        trade_logs = df['trade_log_return'].values
        # annualized volatility of trade returns (approx)
        ann_vol = np.std(trade_logs, ddof=1) * np.sqrt(periods_per_year / max(1, self.step))
        # CAGR approx from trades
        n_years = (len(df) * self.step) / periods_per_year
        cagr = (final_value ** (1 / max(1e-9, n_years))) - 1 if n_years > 0 else np.nan

        sharpe = calc_sharpe(trade_logs, rf_rate=0.0, periods_per_year=periods_per_year / max(1, self.step))
        dir_acc = df['direction_correct'].mean() * 100.0
        mdd_val, mdd_idx = max_drawdown(self.equity_curve.values)

        stats = {
            "total_return_pct": total_return_pct,
            "final_value": final_value,
            "benchmark_return_pct": benchmark_return_pct,
            "benchmark_final_value": benchmark_value,
            "cagr": cagr * 100.0 if not np.isnan(cagr) else np.nan,
            "annualized_vol_pct": ann_vol * 100.0,
            "sharpe": float(sharpe) if not np.isnan(sharpe) else np.nan,
            "directional_accuracy_pct": float(dir_acc),
            "max_drawdown_pct": float(mdd_val * 100.0),
            "n_trades": len(df),
        }
        return stats

    # ---------------- Utilities ---------------- #
    def export_results(self, csv_path: str = "walkforward_results.csv", equity_csv: str = "equity_curve.csv"):
        """Export fold-level results and equity curve."""
        if self.results_df is None:
            raise RuntimeError("Run the forecaster first with .run()")
        self.results_df.to_csv(csv_path, index=True)
        # export equity with date mapping
        eq_df = pd.DataFrame({
            "fold": [0] + list(self.results_df.index),
            "equity": list(self.equity_curve.values)
        })
        eq_df.to_csv(equity_csv, index=False)
        if self.verbose:
            print(f"Exported folds -> {csv_path}, equity -> {equity_csv}")

    def summary_dataframe(self):
        if self.results_df is None:
            raise RuntimeError("Run the forecaster first with .run()")
        out = self.results_df.reset_index()[[
            'date', 'current_price', 'pred_price', 'actual_future_price',
            'pred_log_ret', 'actual_log_ret', 'direction_correct', 'trade_log_return', 'equity',
            'regime', 'regime_mult'
        ]]
        out = out.rename(columns={
            'date': 'Date',
            'current_price': 'Price',
            'pred_price': 'Pred',
            'actual_future_price': 'Actual_Price',
            'pred_log_ret': 'Pred_LogRet',
            'actual_log_ret': 'Actual_LogRet',
            'direction_correct': 'Dir_Correct',
            'trade_log_return': 'Trade_LogRet',
            'equity': 'Equity',
            'regime': 'Regime',
            'regime_mult': 'Regime_Mult',
            'base_pred': 'Base_Pred',
            'reliability': 'Reliability'
        })
        return out
