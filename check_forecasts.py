
import sqlite3
import pandas as pd
from pathlib import Path

db_path = Path("data/forecasts.db")
if not db_path.exists():
    print("DB not found (yet)")
    exit()

conn = sqlite3.connect(db_path)
try:
    # Check for horizon=30
    df = pd.read_sql_query("SELECT * FROM forecasts WHERE horizon=30 ORDER BY created_at DESC LIMIT 5", conn)
    if not df.empty:
        print("Found horizon=30 forecasts:")
        print(df[['date', 'symbol', 'horizon', 'prediction']])
    else:
        print("No horizon=30 forecasts found yet.")
        
    # Check for DIS
    df_dis = pd.read_sql_query("SELECT * FROM forecasts WHERE symbol='DIS' LIMIT 1", conn)
    if not df_dis.empty:
        print("Found DIS forecast.")
    else:
        print("No DIS forecast yet.")
        
    # Check for CL=F
    df_clf = pd.read_sql_query("SELECT * FROM forecasts WHERE symbol='CL=F' LIMIT 1", conn)
    if not df_clf.empty:
        print("Found CL=F forecast.")
    else: 
        print("No CL=F forecast yet.")

finally:
    conn.close()
