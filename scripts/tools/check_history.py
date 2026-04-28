import sqlite3
import pandas as pd

def check_history():
    conn = sqlite3.connect('db.sqlite3')
    df = pd.read_sql_query("SELECT id, app, name, applied FROM django_migrations WHERE app IN ('core', 'bookings', 'finance', 'crm', 'cotizaciones') ORDER BY id ASC", conn)
    print(df.to_string())
    conn.close()

if __name__ == "__main__":
    check_history()
