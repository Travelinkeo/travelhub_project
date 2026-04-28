import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:travelhub2026@127.0.0.1:5433/travelhub_evolution')
    cur = conn.cursor()
    
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='Session'")
    columns = cur.fetchall()
    print("Columnas en Session:", [c[0] for c in columns])
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
