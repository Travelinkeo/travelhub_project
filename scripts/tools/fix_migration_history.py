#!/usr/bin/env python
"""
Fix the InconsistentMigrationHistory by directly inserting the missing
migration record into django_migrations table.
"""
import psycopg
from datetime import datetime, timezone

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="TravelHub",
    user="postgres",
    password="Linkeo1331@@"
)
cur = conn.cursor()

# 1. Check current state
cur.execute("SELECT app, name, applied FROM django_migrations WHERE app IN ('bookings', 'contabilidad') ORDER BY app, name;")
rows = cur.fetchall()
print("Estado actual de migraciones bookings y contabilidad:")
for row in rows:
    print(f"  {row[0]}.{row[1]} - applied: {row[2]}")

# 2. Check if contabilidad.0002_initial is already registered
cur.execute("SELECT COUNT(*) FROM django_migrations WHERE app='contabilidad' AND name='0002_initial';")
count = cur.fetchone()[0]

if count == 0:
    # Insert the fake migration record
    cur.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s);",
        ('contabilidad', '0002_initial', datetime.now(timezone.utc))
    )
    conn.commit()
    print("\nOK - Insertado registro fake: contabilidad.0002_initial")
else:
    print(f"\nEl registro ya existe ({count} veces). No se necesita insertar.")

# 3. Verify
cur.execute("SELECT app, name, applied FROM django_migrations WHERE app IN ('bookings', 'contabilidad') ORDER BY app, name;")
rows = cur.fetchall()
print("\nEstado FINAL:")
for row in rows:
    print(f"  {row[0]}.{row[1]}")

cur.close()
conn.close()
print("\nListo! Ahora ejecuta: python manage.py runserver")
