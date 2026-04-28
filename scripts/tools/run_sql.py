import sqlite3
import sys

def run_sql(sql):
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        print(f"Executing: {sql}")
        cursor.execute(sql)
        conn.commit()
        print(f"Rows affected: {cursor.rowcount}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_sql(sys.argv[1])
    else:
        print("No SQL provided")
