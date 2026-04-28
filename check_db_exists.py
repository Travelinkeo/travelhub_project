import psycopg2
try:
    print("Intentando conectar a TravelHub...")
    conn = psycopg2.connect("postgresql://postgres:travelhub2026@localhost:5433/TravelHub")
    print("Conexión exitosa a TravelHub")
    conn.close()
    
    print("Intentando conectar a travelhub_evolution...")
    conn2 = psycopg2.connect("postgresql://postgres:travelhub2026@localhost:5433/travelhub_evolution")
    print("Conexión exitosa a travelhub_evolution")
    conn2.close()
except Exception as e:
    print(f"Error: {e}")
