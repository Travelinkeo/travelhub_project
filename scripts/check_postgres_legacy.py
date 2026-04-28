
import psycopg2
import sys

def check_postgres(user, password, dbname="travelhub", host="localhost", port="5432"):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print(f"✅ CONEXIÓN EXITOSA: {user}@{dbname} con pass '{password}'")
        
        # Verificar si hay tablas
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_scheme = 'public';")
        count = cur.fetchone()[0]
        print(f"   Tablas encontradas: {count}")
        
        try:
            cur.execute("SELECT count(*) FROM core_agencia;")
            agencias = cur.fetchone()[0]
            print(f"   Agencias en DB: {agencias}")
        except:
            print("   (No se pudo leer tabla Agencias)")
        
        conn.close()
        return True
    except Exception as e:
        # Silenciamos errores para no llenar la pantalla, solo éxito nos importa
        return False

if __name__ == "__main__":
    print("Probando credenciales del .env viejo...")
    
    # Combinaciones a probar derived from user input
    users = ["postgres", "admin", "travelhub", "travelhub_user"]
    passwords = [
        "postgres", "admin", "root", 
        "travelhub", "travelhub2024", "travelhub2025", "travelhub2026",
        "Linkeo1331**", # SECRET_KEY
        "tddfugdgvsfgtgwq", # GMAIL_APP_PASSWORD
        "your_db_password", # Del ejemplo comentado
        "", # Vacía
    ]
    databases = ["travelhub", "travelhub_db", "postgres"]

    found = False
    for db in databases:
        print(f"--- Probando DB: {db} ---")
        for u in users:
            for p in passwords:
                # print(f"Probando {u} / {p} @ {db} ...") # Demasiado ruido
                if check_postgres(u, p, dbname=db):
                    print(f"\n🎉 ¡ENCONTRADO DE NUEVO! \n   DB={db}\n   User={u}\n   Pass={p}")
                    found = True
                    # No hacemos break total para ver si hay múltiples conexiones válidas
            
    if not found:
        print("\n❌ No se encontraron credenciales válidas con los datos suministrados.")
