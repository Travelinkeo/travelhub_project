
import sqlite3

def check_raw():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Listar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Total tablas: {len(tables)}")
        
        # Contar Agencias
        try:
            cursor.execute("SELECT count(*) FROM core_agencia")
            print(f"Agencias (RAW): {cursor.fetchone()[0]}")
        except Exception as e:
            print(f"Error Agencias: {e}")

        # Contar Clientes
        try:
            cursor.execute("SELECT count(*) FROM core_cliente")
            print(f"Clientes (RAW): {cursor.fetchone()[0]}")
        except Exception as e:
            print(f"Error Clientes: {e}")

        conn.close()
    except Exception as e:
        print(f"Error conectando DB: {e}")

if __name__ == "__main__":
    check_raw()
