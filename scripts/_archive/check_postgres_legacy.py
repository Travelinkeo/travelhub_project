import os
import sys

import psycopg2


def check_postgres(user, password, dbname="travelhub", host="localhost", port="5432"):
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        print(f"CONEXION EXITOSA: {user}@{dbname}")

        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        count = cur.fetchone()[0]
        print(f"   Tablas encontradas: {count}")

        try:
            cur.execute("SELECT count(*) FROM core_agencia;")
            agencias = cur.fetchone()[0]
            print(f"   Agencias en DB: {agencias}")
        except Exception:
            print("   (No se pudo leer tabla Agencias)")

        conn.close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME", "travelhub")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")

    if not db_password:
        print("ERROR: La variable de entorno DB_PASSWORD es requerida.")
        print("Uso: DB_PASSWORD=su_password python scripts/check_postgres_legacy.py")
        sys.exit(1)

    print(f"Probando conexion a {db_name}...")
    if check_postgres(db_user, db_password, dbname=db_name, host=db_host, port=db_port):
        print("\nConexion exitosa con las credenciales de entorno.")
    else:
        print("\nNo se pudo conectar con las credenciales de entorno.")
