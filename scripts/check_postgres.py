
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
        print(f"✅ CONEXIÓN EXITOSA: {user}@{dbname}")
        
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
        # Manejo robusto de errores de encoding
        try:
            msg = str(e)
        except:
            msg = "Error de codificación en mensaje"
        #print(f"❌ Falló {user}/{password}: {msg}") 
        # Comentamos el print detallado para evitar ruido, solo imprimimos si conecta
        return False

if __name__ == "__main__":
    print("Probando credenciales típicas...")
    
    # Lista de credenciales a probar
    creds = [
        ("postgres", "postgres"),
        ("postgres", "admin"),
        ("postgres", "1234"),
        ("postgres", "travelhub"),
        ("postgres", ""), # Password vacío
        ("admin", "admin"),
        ("travelhub", "travelhub"),
        ("travelhub", "travelhub2024"),
        ("travelhub", "travelhub2025"),
        ("travelhub", "travelhub2026"),
        ("postgres", "root"),
    ]
    
    found = False
    for u, p in creds:
        print(f"Probando {u} / '{p}' ...")
        if check_postgres(u, p):
            print(f"\n🎉 ¡ENCONTRADO! Usa: User={u}, Pass={p}")
            found = True
            break
            
    if not found:
        print("\n❌ No se encontraron credenciales válidas en la lista común.")
