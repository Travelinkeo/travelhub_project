import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:travelhub2026@127.0.0.1:5433/travelhub_evolution')
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    print("Tablas encontradas:", [t[0] for t in tables])
    
    # Intentar ver el contenido de Instance
    cur.execute('SELECT "name", "connectionStatus" FROM "Instance"')
    instances = cur.fetchall()
    print("Instancias en DB:", instances)
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
