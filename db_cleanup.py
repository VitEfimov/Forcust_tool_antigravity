import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "data/forecasts.db"

def clean_duplicates():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Identify duplicates
    print("Checking for duplicates...")
    c.execute('''
        SELECT date, symbol, horizon, COUNT(*) 
        FROM forecasts 
        GROUP BY date, symbol, horizon 
        HAVING COUNT(*) > 1
    ''')
    duplicates = c.fetchall()
    print(f"Found {len(duplicates)} groups of duplicates.")
    
    if duplicates:
        print("Removing duplicates (keeping the one with max id)...")
        # Keep the row with the MAX id for each (date, symbol, horizon) group
        c.execute('''
            DELETE FROM forecasts 
            WHERE id NOT IN (
                SELECT MAX(id) 
                FROM forecasts 
                GROUP BY date, symbol, horizon
            )
        ''')
        print(f"Deleted {c.rowcount} rows.")
        conn.commit()
    
    # 2. Add Unique Index
    print("Creating UNIQUE INDEX...")
    try:
        c.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_forecasts_unique 
            ON forecasts (date, symbol, horizon)
        ''')
        conn.commit()
        print("Unique index created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating index: {e}")

    # 3. Verify
    c.execute("PRAGMA index_list('forecasts')")
    indexes = c.fetchall()
    print("Indexes on forecasts table:", indexes)
    
    conn.close()

if __name__ == "__main__":
    clean_duplicates()
