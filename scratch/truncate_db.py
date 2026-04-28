import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:travelhub2026@host.docker.internal:5433/travelhub_evolution')
    cur = conn.cursor()
    cur.execute('TRUNCATE TABLE "Instance" CASCADE;')
    conn.commit()
    cur.close()
    conn.close()
    print("SUCCESS: DB Truncated")
except Exception as e:
    print(f"ERROR: {e}")
