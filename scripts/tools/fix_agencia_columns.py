#!/usr/bin/env python
"""
Fix script: Agrega las columnas SaaS faltantes al modelo core_agencia en PostgreSQL.
Ejecutar con: python fix_agencia_columns.py
"""
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="TravelHub",
    user="postgres",
    password="Linkeo1331@@"
)
cur = conn.cursor()

sql = """
    ALTER TABLE core_agencia 
        ADD COLUMN IF NOT EXISTS correo_emisiones varchar(254) NULL,
        ADD COLUMN IF NOT EXISTS password_app_correo varchar(255) NULL,
        ADD COLUMN IF NOT EXISTS telegram_bot_token varchar(255) NULL,
        ADD COLUMN IF NOT EXISTS telegram_chat_id varchar(255) NULL;
"""

cur.execute(sql)
conn.commit()
print("Columnas agregadas exitosamente a core_agencia:")
print("   - correo_emisiones (varchar 254)")
print("   - password_app_correo (varchar 255)")
print("   - telegram_bot_token (varchar 255)")
print("   - telegram_chat_id (varchar 255)")

# Verify
cur.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'core_agencia'
    AND column_name IN ('correo_emisiones', 'password_app_correo', 'telegram_bot_token', 'telegram_chat_id')
    ORDER BY column_name;
""")
rows = cur.fetchall()
print("\nVerificacion en la DB:")
for row in rows:
    print(f"   OK: {row[0]} ({row[1]}, max_length={row[2]})")

cur.close()
conn.close()
print("\nListo! Reinicia el servidor Django para aplicar los cambios.")
