import sqlite3
import pandas as pd
try:
    conn = sqlite3.connect('db.sqlite3')
    df = pd.read_sql_query("SELECT app, name, applied FROM django_migrations ORDER BY applied DESC", conn)
    print(df.to_string())
    conn.close()
except Exception as e:
    print(f"Error: {e}")
