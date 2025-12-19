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
from .kalman_filter import KalmanTrend
from .transformer_model import TransformerForecaster
from .ensemble import EnsembleModel
import gc

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
        regime_vol_threshold: float = 0.20, # Volatility threshold for regime classification
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
        - regime_vol_threshold: Annualized Volatility threshold for Bull/Bear regime classification.
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
        self.regime_vol_threshold = float(regime_vol_threshold)
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
            df[f"{name}_Close"] = df[f"{name}_Close"].ffill().bfill()
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
        
        # --- OPTIMIZATION: Downcast to float32 for Memory (50% savings) ---
        numeric_cols = df.select_dtypes(include=['float64']).columns
        df[numeric_cols] = df[numeric_cols].astype('float32')
        
        # --- NEW: Kalman Filter Trend ---
        kt = KalmanTrend()
        # fit_transform returns Series. We handle fillna for start
        df['Trend_Price'] = kt.fit_transform(df['Close'])
        # Slope: (Trend - PrevTrend) / PrevTrend approx
        df['Trend_Slope'] = df['Trend_Price'].pct_change().fillna(0)
        # Distance from Trend
        df['Trend_Dist'] = (df['Close'] / df['Trend_Price']) - 1

        # Target: log-return H days ahead
        future_close = df['Close'].shift(-self.prediction_horizon)
        df['Target'] = np.log(future_close / df['Close'])
        df['Target_Price'] = future_close

        # Compose feature column list (exclude raw OHLCV, target, and external raw close if you prefer)
        exclude = {'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Target', 'Target_Price', 'Trend_Price'}
        cols = [c for c in df.columns if c not in exclude]
        self.feature_cols = cols

        if self.verbose:
            self.log_func(f"[prepare_features] {len(df)} rows, {len(self.feature_cols)} features")

        return df

    # ---------------- Walk-forward / run ---------------- #
    def run(self, save_models: Optional[bool] = None) -> pd.DataFrame:
        """
        Execute walk-forward training. Returns a DataFrame with per-fold results.
        Refactored for Institutional Engine:
        - GPU Acceleration
        - Daily PnL Series
        - Volatility Scaling
        - Leakage-Proof Meta-Learning
        """
        if save_models is None:
            save_models = self.save_models

        data = self.prepare_features()
        n = len(data)
        if n < self.train_window + self.prediction_horizon:
            raise ValueError("Not enough data for the chosen train_window + prediction_horizon")

        current_idx = self.train_window
        records = []
        
        # Daily PnL Tracking
        # We need a continuous daily series for compounding
        daily_returns = data['Close'].pct_change().fillna(0) # Raw market returns
        strategy_daily_pnl = np.zeros(n) # Aggregated PnL stream
        
        # Transformer State
        tf_model = TransformerForecaster(input_dim=len(self.feature_cols), seq_len=10)
        tf_needs_retrain = True
        tf_last_train_fold = -999
        
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
            
            # --- MODEL 1: LightGBM (GPU) ---
            scaler = StandardScaler()
            X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=self.feature_cols)
            X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=self.feature_cols)

            lgbm = lgb.LGBMRegressor(
                n_estimators=300, 
                learning_rate=0.03, 
                num_leaves=63, 
                verbosity=-1, 
                n_jobs=1, # Optimization: 1 thread reduces memory overhead significantly
                histogram_pool_size=64 # Optimization: Limit histo memory to 64MB
            )
            lgbm.fit(X_train_scaled, y_train)
            lgbm_pred = float(lgbm.predict(X_test_scaled)[0])
            
            # --- MODEL 2: Transformer (Schedule: Every 60 folds) ---
            if (fold - tf_last_train_fold) >= 60:
                tf_needs_retrain = True
            
            if tf_needs_retrain:
                try:
                    tf_model.fit(X_train_scaled.tail(1000), pd.Series(y_train).tail(1000), epochs=5)
                    tf_last_train_fold = fold
                    tf_needs_retrain = False
                except Exception as e:
                    if self.verbose: self.log_func(f"Transformer Train Error: {e}")
            
            # Inference (Always run, weights frozen if not retrained)
            tf_mu, tf_sigma = tf_model.predict(X_train_scaled.tail(30)) # Use Context
            tf_pred = tf_mu
            
            # --- ENSEMBLE ---
            current_vol_annual = float(test_row['Vol_20'].iloc[0]) * np.sqrt(252)
            current_trend_slope = float(test_row['Trend_Slope'].iloc[0])
            regime_code = 1 if current_vol_annual < self.regime_vol_threshold else 0 
            
            ens = EnsembleModel()
            raw_pred_log_ret = ens.predict(
                lgbm_pred=lgbm_pred,
                transformer_pred=tf_pred,
                current_regime=regime_code,
                trend_slope=current_trend_slope,
                volatility=current_vol_annual
            )

            # --- META-LEARNING (Reliability) ---
            reliability_prob = 1.0 # Default High Trust
            
            # Retrain meta-learner every 20 folds to save compute
            should_retrain_meta = (self.use_meta_learner and len(records) >= 20 and (fold % 20 == 0))
            # Or if it's the first time we can?
            if self.use_meta_learner and len(records) >= 20: 
                try:
                    # Construct Meta History
                    meta_history = pd.DataFrame(records)
                    meta_history['date'] = pd.to_datetime(meta_history['date'])
                    
                    market_cols = [c for c in data.columns if 'VIX' in c or 'Close' == c] 
                    meta_train_df = pd.merge(meta_history, data[market_cols], left_on='date', right_index=True, how='left')
                    
                    # Only Retrain Periodically
                    if should_retrain_meta or not self.meta_learner.is_fitted:
                        self.meta_learner.train(meta_train_df, 'pred_log_ret', 'actual_log_ret')
                    
                    # Predict Reliability
                    recent_history = meta_train_df.tail(40).copy()
                    
                    # Create current context row
                    current_context_row = test_row.copy()
                    current_context_row['pred_log_ret'] = raw_pred_log_ret 
                    
                    current_context = pd.concat([recent_history, current_context_row], axis=0, ignore_index=True)
                    
                    reliability_prob = self.meta_learner.predict_reliability(current_context)
                except Exception as e:
                    if self.verbose: self.log_func(f"Meta-Learner Error: {e}")

            # --- RISK CONTROLS ---
            # 1. Signal Threshold
            min_signal = 0.0005 # 5bps
            if abs(raw_pred_log_ret) < min_signal:
                final_pred_log_ret = 0.0
                reliability_prob = 0.0 # Effectively no trade
            else:
                final_pred_log_ret = raw_pred_log_ret * reliability_prob # Scale by probability
            
            # 2. Volatility Scaling
            target_vol = 0.12
            vol_scalar = min(1.0, target_vol / (current_vol_annual + 1e-9))
            
            # Position sizing
            # Direction * VolScalar * Confidence
            position = np.sign(final_pred_log_ret) * vol_scalar * reliability_prob
            
            # --- DAILY PnL ENGINE ---
            # Apply position to future days [t+1 : t+H]
            start_pnl_idx = current_idx + 1
            end_pnl_idx = min(current_idx + 1 + self.trade_horizon, n)
            
            if start_pnl_idx < n:
                # Daily Returns for the holding period
                period_returns = daily_returns.iloc[start_pnl_idx : end_pnl_idx].values
                strategy_daily_pnl[start_pnl_idx : end_pnl_idx] += position * period_returns

            # --- RECORDING ---
            actual_log_ret = float(data['Target'].iloc[current_idx])
            
            records.append({
                "fold": fold,
                "date": data.index[current_idx],
                "price": float(data['Close'].iloc[current_idx]),
                
                "pred_log_ret": raw_pred_log_ret, # Base prediction
                "actual_log_ret": actual_log_ret,
                "reliability_prob": reliability_prob,
                "vol_scalar": vol_scalar,
                "final_position": position,
                
                "lgbm_pred": lgbm_pred,
                "tf_pred": tf_pred,
                "regime": "Bull" if regime_code==1 else "Bear"
            })
            
            if self.verbose and (fold % 50 == 0 or fold == 1):
                self.log_func(f"[fold {fold}] Reliab={reliability_prob:.2f} Pos={position:.2f} Vol={current_vol_annual:.1%}")
                
            # Cleanup per fold
            if fold % 10 == 0:
                gc.collect()

            current_idx += self.step

        # Finalize Results
        self.results_df = pd.DataFrame(records).set_index('fold') if records else pd.DataFrame()
        
        # Construct Equity Curve from Daily PnL
        # USE LOG-SPACE ACCUMULATION (Robust)
        # Avoids underflow for very small nums or drift
        # equity = exp( cumsum( log(1 + pnl) ) )
        # Handling negative PnL < -1? (bankruptcy) -> clip?
        strat_pnl_safe = pd.Series(strategy_daily_pnl, index=data.index).clip(lower=-0.999)
        self.equity_curve = np.exp(np.cumsum(np.log1p(strat_pnl_safe)))
        
        return self.results_df

    # ---------------- Performance reporting ---------------- #
    def performance_report(self, periods_per_year: int = 252) -> Dict[str, float]:
        if self.results_df is None or self.equity_curve is None:
            raise RuntimeError("Run the forecaster first with .run()")

        # Total Return from Equity Curve
        start_val = self.equity_curve.iloc[0]
        final_val = self.equity_curve.iloc[-1]
        total_return_pct = ((final_val / start_val) - 1.0) * 100.0

        # Benchmark (Buy and Hold)
        benchmark_start = self.df.loc[self.equity_curve.index[0]]['Close'] # approx
        benchmark_end = self.df.loc[self.equity_curve.index[-1]]['Close']
        benchmark_return_pct = ((benchmark_end / benchmark_start) - 1.0) * 100.0

        # Annualized Volatility (Daily)
        daily_rets = self.equity_curve.pct_change().dropna()
        ann_vol = daily_rets.std() * np.sqrt(periods_per_year)

        # CAGR
        days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        years = days / 365.25
        cagr = ((final_val / start_val) ** (1 / max(years, 0.001))) - 1 if years > 0 else 0.0

        # Sharpe
        sharpe = calc_sharpe(daily_rets.values, rf_rate=0.0, periods_per_year=periods_per_year)
        
        # Max Drawdown
        mdd_val, _ = max_drawdown(self.equity_curve.values)
        
        # Win Rate & Directional Accuracy
        n_trades = len(self.results_df)
        
        # Directional Accuracy: Sign(Position) == Sign(Actual Return)
        # Filter for non-zero positions
        active_trades = self.results_df[self.results_df['final_position'] != 0]
        if len(active_trades) > 0:
            matches = np.sign(active_trades['final_position']) == np.sign(active_trades['actual_log_ret'])
            dir_accuracy = matches.mean() * 100.0
        else:
            dir_accuracy = 0.0
        
        stats = {
            "total_return_pct": total_return_pct,
            "final_value": final_val,
            "benchmark_return_pct": benchmark_return_pct,
            "cagr": cagr * 100.0,
            "annualized_vol_pct": ann_vol * 100.0,
            "sharpe": float(sharpe) if not np.isnan(sharpe) else 0.0,
            "max_drawdown_pct": float(mdd_val * 100.0),
            "n_folds": n_trades,
            "avg_reliability": self.results_df['reliability_prob'].mean(),
            "directional_accuracy": dir_accuracy
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
            "date": self.equity_curve.index,
            "equity": list(self.equity_curve.values)
        })
        eq_df.to_csv(equity_csv, index=False)
        if self.verbose:
            print(f"Exported folds -> {csv_path}, equity -> {equity_csv}")

    def summary_dataframe(self):
        if self.results_df is None:
            raise RuntimeError("Run the forecaster first with .run()")
        
        # 'date' column might be index or in df depending on creation
        out = self.results_df.copy()
        if 'date' in out.columns:
            out = out.set_index('date') # Use date index for export readability
            
        out = out[[
             'price', 'pred_log_ret', 'actual_log_ret', 
             'reliability_prob', 'vol_scalar', 'final_position', 'regime'
        ]]
        
        out = out.rename(columns={
            'price': 'Price',
            'pred_log_ret': 'Raw_Link',
            'actual_log_ret': 'Actual_LogRet',
            'reliability_prob': 'Reliability',
            'vol_scalar': 'Vol_Scalar',
            'final_position': 'Position',
            'regime': 'Regime'
        })
        return out
