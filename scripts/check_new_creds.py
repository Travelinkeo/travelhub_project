
import psycopg2
import sys

def check_postgres(user, password, dbname="travelhub", host="localhost", port="5432"):
    print(f"\n--- Probando conexión a '{dbname}' ---")
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print(f"✅ ¡CONEXIÓN EXITOSA! Usuario: {user}")
        
        # Verificar tablas y conteos
        cur = conn.cursor()
        
        # 1. Contar Agencias
        try:
            cur.execute("SELECT count(*) FROM core_agencia;")
            agencias = cur.fetchone()[0]
            print(f"   🏢 Agencias encontradas: {agencias}")
        except Exception as e:
            print(f"   ⚠️ No se pudo leer core_agencia: {e}")

        # 2. Contar Ventas (Historial)
        try:
            cur.execute("SELECT count(*) FROM core_venta;")
            ventas = cur.fetchone()[0]
            print(f"   💰 Ventas registradas: {ventas}")
        except:
             print("   (Tabla core_venta no encontrada o vacía)")
             
        # 3. Contar Boletos
        try:
            cur.execute("SELECT count(*) FROM core_boletoimportado;")
            boletos = cur.fetchone()[0]
            print(f"   🎫 Boletos importados: {boletos}")
        except:
            print("   (Tabla core_boletoimportado no encontrada)")

        conn.close()
        return True
    except psycopg2.OperationalError as e:
        if "authentication failed" in str(e):
            print("❌ Error de Autenticación (Clave incorrecta)")
        elif "database" in str(e) and "does not exist" in str(e):
             print(f"❌ La base de datos '{dbname}' no existe.")
        else:
            print(f"❌ Error de Conexión: {e}")
        return False
    except Exception as e:
        print(f"❌ Error General: {e}")
        return False

if __name__ == "__main__":
    user = "postgres"
    password = "Linkeo1331@@"
    
    # Probar primero con base de datos 'travelhub'
    if not check_postgres(user, password, dbname="travelhub"):
        # Si falla, probar con 'postgres' para ver si al menos entra al sistema y listar bases de datos
        print("\nIntentando conectar a DB 'postgres' para listar bases de datos existentes...")
        try:
            conn = psycopg2.connect(dbname="postgres", user=user, password=password)
            cur = conn.cursor()
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
            dbs = cur.fetchall()
            print("\n📂 Bases de Datos encontradas en el sistema:")
            for db in dbs:
                print(f"   - {db[0]}")
                
            # Si encontramos algo parecido a travelhub, probamos esa
            for db in dbs:
                name = db[0]
                if "travel" in name or "hub" in name or "db" in name:
                    if name != "travelhub": # Ya probada
                        check_postgres(user, password, dbname=name)
            
            conn.close()
        except Exception as e:
             print(f"❌ Tampoco se pudo conectar a 'postgres': {e}")
