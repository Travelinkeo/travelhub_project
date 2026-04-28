import sqlite3
try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY applied DESC")
    rows = cursor.fetchall()
    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
