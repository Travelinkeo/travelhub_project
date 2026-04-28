import psycopg2
import os

dsn = os.environ.get('DATABASE_URL')
print(f"Connecting to {dsn}")
try:
    conn = psycopg2.connect(dsn)
    print("Connected successfully")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print(f"Result: {cur.fetchone()}")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
