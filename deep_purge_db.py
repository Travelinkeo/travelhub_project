import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:travelhub2026@127.0.0.1:5433/travelhub_evolution')
    cur = conn.cursor()
    
    print("Limpiando tablas de Evolution API...")
    
    # Desactivar restricciones de llaves foráneas temporalmente
    cur.execute('TRUNCATE TABLE "Instance" CASCADE')
    cur.execute('TRUNCATE TABLE "Session" CASCADE')
    cur.execute('TRUNCATE TABLE "Setting" CASCADE')
    
    conn.commit()
    print("Base de datos de Evolution API purgada exitosamente.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
