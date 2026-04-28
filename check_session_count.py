import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:travelhub2026@127.0.0.1:5433/travelhub_evolution')
    cur = conn.cursor()
    
    cur.execute('SELECT id FROM "Instance" WHERE name = %s', ('TH_V2_1',))
    instance = cur.fetchone()
    if instance:
        instance_id = instance[0]
        cur.execute('SELECT COUNT(*) FROM "Session" WHERE "instanceId" = %s', (instance_id,))
        count = cur.fetchone()[0]
        print(f"Sesiones encontradas para TH_V2_1: {count}")
    else:
        print("Instancia TH_V2_1 no encontrada en DB.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
