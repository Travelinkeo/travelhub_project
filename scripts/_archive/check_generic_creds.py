import psycopg2


def check_postgres(user, password, dbname="travelhub", host="localhost", port="5432"):
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        print(f"✅ ¡BINGO! Conexión exitosa con: {user}@{dbname} (Clave: {password})")
        conn.close()
        return True
    except Exception:
        # print(f"❌ Falló {user}: {e}")
        return False


if __name__ == "__main__":
    print("Probando la URL genérica suministrada...")

    # Pruebas literales de lo que envió el usuario
    pruebas = [
        ("user", "password", "dbname"),
        ("user", "password", "travelhub"),
        ("travelhub_user", "your_db_password", "travelhub_db"),  # Del env viejo comentado
        ("postgres", "postgres", "travelhub"),
    ]

    found = False
    for u, p, db in pruebas:
        if check_postgres(u, p, dbname=db):
            found = True

    if not found:
        print("❌ Las credenciales genéricas ('user', 'password') no funcionaron.")
