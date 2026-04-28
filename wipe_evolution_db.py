import psycopg2

try:
    conn = psycopg2.connect(
        dbname="travelhub_evolution",
        user="postgres",
        password="travelhub2026",
        host="localhost",
        port="5433"
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Limpieza total del esquema para que Prisma pueda recrearlo desde cero
    print("Dropping and recreating schema public...")
    cur.execute("DROP SCHEMA public CASCADE;")
    cur.execute("CREATE SCHEMA public;")
    cur.execute("GRANT ALL ON SCHEMA public TO postgres;")
    cur.execute("GRANT ALL ON SCHEMA public TO public;")
    
    print("Database wiped and schema reset successfully!")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error wiping database: {e}")
