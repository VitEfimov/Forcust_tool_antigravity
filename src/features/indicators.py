import pandas as pd
import numpy as np
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to the dataframe.
    Expects columns: Open, High, Low, Close, Volume
    """
    if df.empty:
        return df
    
    df = df.copy()
    close = df['Close']

    # RSI
    rsi = RSIIndicator(close=close, window=14)
    df['RSI'] = rsi.rsi()

    # MACD
    macd = MACD(close=close)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_diff'] = macd.macd_diff()

    # Bollinger Bands
    bb = BollingerBands(close=close, window=20, window_dev=2)
    df['BB_high'] = bb.bollinger_hband()
    df['BB_low'] = bb.bollinger_lband()
    df['BB_width'] = (df['BB_high'] - df['BB_low']) / df['Close']

    # Moving Averages
    df['SMA_50'] = SMAIndicator(close=close, window=50).sma_indicator()
    df['SMA_200'] = SMAIndicator(close=close, window=200).sma_indicator()

    # Log Returns
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # Volatility (Rolling Std Dev of Log Returns)
    df['Volatility_20'] = df['Log_Return'].rolling(window=20).std()

    return df
