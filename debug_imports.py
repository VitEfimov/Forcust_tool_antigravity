try:
    import pandas
    print("pandas ok")
    import numpy
    print("numpy ok")
    import ta
    print("ta ok")
    import lightgbm
    print("lightgbm ok")
    import hmmlearn
    print("hmmlearn ok")
    import joblib
    print("joblib ok")
    import fastapi
    print("fastapi ok")
    import yfinance
    print("yfinance ok")
    from src.models.hmm import RegimeDetector
    print("RegimeDetector ok")
except Exception as e:
    print(f"Error: {e}")
