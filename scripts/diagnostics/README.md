# Scripts de Diagnóstico

Scripts de solo lectura para auditar el estado del sistema (migraciones, BD,
columnas). Ninguno modifica datos ni el esquema; es seguro ejecutarlos en
cualquier entorno.

## `check_migration_health.py`

Diagnóstico integral que reporta tres causas históricas de divergencia entre
Django y la BD (ver [`docs/MIGRATIONS.md`](../../docs/MIGRATIONS.md)):

1. Migrations aplicadas en la BD cuyo archivo en disco ya no existe.
2. Tablas que aún viven como `core_*` cuando deberían ser `bookings_*`
   (resto del rename de la migración `0036_rename_core_tables_to_bookings`).
3. Columnas faltantes en modelos críticos (`Venta`, `BoletoImportado`,
   `PagoVenta`, `Factura`, `Moneda`).

```bash
python scripts/diagnostics/check_migration_health.py
python scripts/diagnostics/check_migration_health.py --skip-columns
```

Sale con código `!= 0` si detecta divergencias (útil como check pre-deploy).

## `check_missing_columns.py`

Compara los campos declarados en cada modelo con las columnas reales de la BD
(`information_schema.columns`) y reporta las faltantes.

```bash
# Todas las apps de negocio
python scripts/diagnostics/check_missing_columns.py

# Una app concreta
python scripts/diagnostics/check_missing_columns.py --app bookings

# Un modelo concreto
python scripts/diagnostics/check_missing_columns.py --app bookings --model Venta
```

Sale con código `!= 0` si encuentra columnas faltantes.

## `test_fresh_migrate.sh`

Crea una BD temporal vacía y corre `manage.py migrate` desde cero para verificar
que el historial de migraciones reconstruye un esquema válido. **No toca la BD
de desarrollo principal.** Documenta el problema de la triple representación de
`Moneda` (ver `docs/MIGRATIONS.md`).

```bash
bash scripts/diagnostics/test_fresh_migrate.sh
# Con un nombre de proyecto docker compose distinto:
COMPOSE_PROJECT=mi-proyecto bash scripts/diagnostics/test_fresh_migrate.sh
```

Requiere el stack de dev (`docker compose`) corriendo con servicios `db` y `web`.
