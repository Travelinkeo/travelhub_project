
import psycopg2
import sys

def check_db(dbname):
    user = "postgres"
    password = "Linkeo1331@@"
    host = "localhost"
    port = "5432"
    
    print(f"\n--- Probando base de datos: '{dbname}' ---")
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print(f"✅ CONEXIÓN EXITOSA a '{dbname}'")
        
        cur = conn.cursor()
        
        # 1. Agencias
        try:
            cur.execute("SELECT count(*) FROM core_agencia;")
            c = cur.fetchone()[0]
            print(f"   🏢 Agencias: {c}")
        except:
            print("   ⚠️ Tabla core_agencia no encontrada")

        # 2. Ventas
        try:
            cur.execute("SELECT count(*) FROM core_venta;")
            c = cur.fetchone()[0]
            print(f"   💰 Ventas: {c}")
        except:
            print("   ⚠️ Tabla core_venta no encontrada")
            
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error conectando a '{dbname}': {e}")
        return False

if __name__ == "__main__":
    check_db("TravelHub")
