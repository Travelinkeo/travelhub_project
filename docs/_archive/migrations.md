# Estado de Migraciones Django

> Documento vivo. Última actualización: 2026-06-22.

## TL;DR

- **NO ejecutes `manage.py migrate` desde una DB vacía en `dev` o `prod`.** El historial de migraciones depende de estado pre-existente.
- **El camino soportado para resetear una DB local es `bash dev-reset.sh`** (usa `pg_dump --schema-only` del proyecto de referencia + `migrate --fake` para alinear el state).
- **El test de "fresh migrate"** (crear DB nueva, correr `migrate` desde cero) **falla en `bookings.0033`** por una divergencia histórica entre la representación de `Moneda` en `core.*`, `finance.*` y `common.*`.
- **Diagnósticos disponibles** en `scripts/diagnostics/` (limpieza 2026-06-22):
  - `check_migration_health.py` — estado integral (sync migrations, namespace core/bookings, columnas críticas).
  - `check_missing_columns.py` — columnas faltantes modelo vs BD.
  - `test_fresh_migrate.sh` — corre `migrate` contra una BD temporal vacía para validar el historial.

## Por qué `fresh migrate` falla

### El problema: tres "versiones" de `Moneda` en el state

A lo largo del tiempo, la tabla `Moneda` se movió entre apps:

| Migración | Operación | Estado |
|---|---|---|
| `core.0001_initial` | `CreateModel(core.Moneda)` | `db_table="core_moneda"` |
| `core.0011_delete_pais_delete_ciudad_and_more` | `DeleteModel(core.Moneda)` (state-only) | Moneda ya no está en `core` |
| `finance.0004_moneda_alter_reporteproveedor_proveedor_and_more` | `CreateModel(finance.Moneda)` (state-only, `db_table="core_moneda"`) | Moneda "vive" en `finance` pero la tabla real es `core_moneda` |
| `common.0003_moneda` | `CreateModel(common.Moneda)` (state-only, `db_table="core_moneda"`) | Hoy Moneda vive en `common` |

El problema crítico: **mientras `core_moneda` se crea con `core.0001`** (la primera migración de `core`), el **state** posterior tiene `finance.moneda` y `common.moneda` superpuestos. La tabla física está bien, pero el state tiene **dos modelos que apuntan a la misma tabla**.

### Lo que esto rompe

Django resuelve `ForeignKey(to="common.moneda")` a la tabla `core_moneda` (correcto). Pero:

- Algunas `AlterField` (especialmente en `bookings.0033`) comparan el "to" viejo (`finance.moneda` o el modelo con `db_table` antiguo) contra el "to" nuevo (`common.moneda`). Si la resolución cambia entre snapshots, Django emite `DROP CONSTRAINT` + `CREATE CONSTRAINT` con el nombre `_fk_<to_table>_<to_column>`.
- En el `bookings.0033` se emite SQL con `finance_moneda` como tabla destino, cuando la tabla real es `core_moneda`. PostgreSQL aborta con `relation "finance_moneda" does not exist`.

### Lo que NO rompe

- `dev-reset.sh`: la DB se recrea con el schema actual (`pg_dump --schema-only` del proyecto canónico) y luego se alinean las tablas `django_migrations` con `--fake`. Sin correr SQL DDL del historial, los modelos y la DB quedan consistentes.
- Deploys incrementales: una vez que la DB existe y los state están sincronizados, agregar migraciones nuevas (que **no** renombren modelos existentes) funciona.

## Pasos diagnósticos ya realizados

1. ✅ `bookings.0030_fix_missing_db_columns` reescrito con bloques `DO $$ ... $$` idempotentes que:
   - Detectan si la tabla está en `core_xxx` o `bookings_xxx` antes de agregar columnas.
   - Usan los nombres de PK custom del proyecto (`id_proveedor`, `id_crucero`, `id_venta`, `id_aerolinea`, `id_moneda`).
   - Funcionan tanto en fresh DB como en la DB histórica con renombres manuales.
2. ✅ `common.0003_moneda.py` fijado con `db_table="core_moneda"` (antes `finance_moneda`).
3. ✅ `common/models.py` Moneda fijado con `db_table="core_moneda"`.
4. ✅ `MigrationLoader.project_state()` confirma que el state final tiene `Moneda` apuntando a `core_moneda`.
5. ❌ `bookings.0033` aún genera SQL con `finance_moneda` pese al state correcto (la verificación visual del SQL no fue posible por issues de WSL/Docker durante la sesión 2026-06-07).

## Workaround recomendado

```bash
# 1. Reset usando el dump canónico (NO recrear DB vacía + migrate)
bash dev-reset.sh

# 2. Si necesitas una DB 100% nueva para CI / staging:
docker exec travelhub_db pg_dump --schema-only -U postgres travelhub > schema.sql
createdb travelhub_fresh
psql travelhub_fresh < schema.sql
docker exec travelhub_web python manage.py migrate --fake
```

## Roadmap (no prioritario)

1. Decidir si la "Moneda" lógica debe vivir en `common.Moneda` o `finance.Moneda` (debe ser una sola).
2. Reescribir `finance.0004` para NO crear un `finance.Moneda` paralelo (queda como no-op state-only, o se mueve a `core` con rename).
3. Reescribir `bookings.0033` con `SeparateDatabaseAndState` y `database_operations=[]` para evitar el alter FK que dispara el error.
4. Una vez los 3 puntos anteriores estén hechos, **re-generar la historia de migraciones desde cero** con `python manage.py makemigrations` y un squash inicial. Esto rompería `migrate --fake` en cualquier instalación existente, así que solo es válido para un reset completo.
5. Agregar CI que corra `migrate` desde fresh DB en cada PR para detectar futuras regresiones.

## Lo que NO se debe hacer

- ❌ `rm -rf apps/*/migrations/0*.py` + `makemigrations` en una instalación con datos. La historia de migraciones contiene bloques `RunSQL` y `RunPython` con lógica de backfill (PII scrubbing, RLS, soft-delete) que **no se puede regenerar** desde los modelos actuales.
- ❌ `ALTER TABLE core_moneda RENAME TO finance_moneda` (o viceversa) sin antes revisar TODAS las migraciones que mencionan ambas tablas. Varios `RenameIndex old_name="core_..."` y `RenameField` dependen del nombre histórico.
- ❌ `python manage.py migrate bookings 0032` y luego `0034` saltándose 0033. 0033 deja el state en una posición que 0034 espera.

## Referencia: migraciones con `SeparateDatabaseAndState` o `RunSQL`/`RunPython`

- `bookings.0030` (DO blocks idempotentes)
- `finance.0020`, `core.0017`, `core.0021`, `core.0027`
- `core.0029_alter_anulacionboleto_agencia_and_more` (añade índices)

## Limpieza de scripts temporales (2026-06-22)

Se eliminó `_para_revisar/scripts_temp/` por completo. Los scripts allí eran
parches de un solo uso que manipulaban directamente `django_migrations`
(`DELETE FROM django_migrations WHERE ...`) o renombraban tablas a mano
(`fix_tables.py`, `reverse_tables.py`), además de shells de emergencia para
producción. Su existencia daba una falsa sensación de que el problema estaba
"arreglado" cuando en realidad lo enmascaraba.

Lo que se hizo:

- **Eliminados** (17 scripts): `fix_core_migrations`, `fix_migrations`,
  `fix_deps`, `fix_deps2`, `fix_deps3`, `smart_fix_deps`, `fix_tables`,
  `reverse_tables`, `emergency_fix`, `fake_migrate.ps1`,
  `fix_completo_produccion`, `fix_produccion_bookings_venta`,
  `verificar_fix_produccion`, `debug_boleto`, `debug_all_parsers`,
  `check_state`, `check_missing_cols`.
- **Eliminados por seguridad** (4 scripts con contraseñas en texto plano):
  `create_admin` (`admin123456`), `verify_local_setup` (`viaggio1` + usuarios
  reales), `setup_users`, `setup_users_agencias`. Ver
  `docs/deployment/security.md` (sección "Gestión de Superusuarios").
- **Consolidados** en `scripts/diagnostics/`: `check_all_missing_cols` →
  `check_missing_columns.py` (con flags `--app`/`--model`), las 4 variantes de
  `test_fresh_migrate{,_v2,_v3,_v4}` → un único `test_fresh_migrate.sh`, y se
  añadió `check_migration_health.py` como diagnóstico integral.

**El workaround soportado sigue siendo `dev-reset.sh`.** `fresh migrate` aún no
funciona (ver Roadmap). Los nuevos scripts de `scripts/diagnostics/` sirven para
monitorizar el estado y detectar divergencias, no para repararlas.
- 19 migraciones con `SeparateDatabaseAndState` (declaración pura, no emiten DDL)
- 17 migraciones con `AlterModelTable(table=None)` (mienten al state declarando que el modelo "ya no tiene tabla custom")
- 4 migraciones con `RenameIndex old_name="core_..."` (renombres históricos)
