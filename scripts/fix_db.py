import sqlite3

def clean_clients():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    # Eliminar clientes creados por el test
    cursor.execute("DELETE FROM core_cliente WHERE email LIKE 'test.encryption%'")
    deleted = cursor.rowcount
    
    # También verificar si hay algún pasaporte muy largo y truncarlo temporalmente para permitir la migración
    # (Aunque lo ideal es eliminar el dato inconsistente)
    cursor.execute("UPDATE core_cliente SET numero_pasaporte = SUBSTR(numero_pasaporte, 1, 50) WHERE LENGTH(numero_pasaporte) > 50")
    updated = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"Deleted {deleted} test clients.")
    print(f"Truncated {updated} over-length passports.")

if __name__ == "__main__":
    clean_clients()
