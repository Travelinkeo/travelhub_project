"""
Diagnóstico integral del estado de migraciones de TravelHub.

Reporta tres aspectos que históricamente han causado divergencia entre
el estado de Django y la BD (ver docs/MIGRATIONS.md):

1. Sincronía entre migrations aplicadas (django_migrations) y los archivos
   en disco por app: detecta migrations que faltan en disco o no aplicadas.
2. Divergencia de namespace de tablas: tablas que existen como core_* cuando
   el modelo vive en bookings (resto del rename incompleto de 0036).
3. Columnas faltantes en modelos críticos (Venta, BoletoImportado, PagoVenta).

Uso:
    python scripts/diagnostics/check_migration_health.py
    python scripts/diagnostics/check_migration_health.py --skip-columns

Salida con código de exit != 0 si se detecta alguna divergencia (útil para CI).
"""

import argparse
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.apps import apps as django_apps  # noqa: E402
from django.db import connection  # noqa: E402

# Modelos críticos para el chequeo de columnas
CRITICAL_MODELS = [
    ("bookings", "Venta"),
    ("bookings", "BoletoImportado"),
    ("bookings", "PagoVenta"),
    ("finance", "Factura"),
    ("finance", "Moneda"),
]

# Mapeo de tablas que DEBERÍAN vivir en bookings_* (post-rename 0036) pero que
# históricamente pudieron quedar como core_* si el rename no completó.
# Derivado de apps/bookings/migrations/0036_rename_core_tables_to_bookings.py
BOOKINGS_TABLE_RENAMES = [
    "actividadservicio",
    "alojamientoreserva",
    "alquilerautoreserva",
    "boletoimportado",
    "circuitodia",
    "circuitoturistico",
    "comisionproveedorservicio",
    "cruceroreserva",
    "eventoservicio",
    "feeventa",
    "itemventa",
    "pagoventa",
    "paqueteaereo",
    "productoservicio",
    "proveedor",
    "segmentovuelo",
    "servicioadicionaldetalle",
    "solicitudanulacion",
    "trasladoservicio",
    "ventaparsemetadata",
    "venta_pasajeros",
    "venta",
]


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def get_existing_tables() -> set[str]:
    """Devuelve todas las tablas del schema public."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        return {row[0] for row in cursor.fetchall()}


def check_migration_sync() -> int:
    """Compara migrations aplicadas vs archivos en disco."""
    from django.db.migrations.loader import MigrationLoader
    from django.db.migrations.recorder import MigrationRecorder

    loader = MigrationLoader(connection, ignore_no_migrations=True)
    disk_migrations = loader.disk_migrations  # {(app, name): Migration}
    applied = set(MigrationRecorder(connection).applied_migrations())

    issues = 0

    # (a) Aplicadas en BD pero sin archivo en disco (peligroso: el state ya no se reconstruye)
    applied_not_on_disk = applied - set(disk_migrations)
    if applied_not_on_disk:
        issues += len(applied_not_on_disk)
        print(
            f"❌ {len(applied_not_on_disk)} migration(s) aplicadas en BD pero SIN archivo en disco:"
        )
        for app, name in sorted(applied_not_on_disk):
            print(f"     • {app}.{name}")
        print("   Esto impide reconstruir el state desde cero (ver docs/MIGRATIONS.md).")
    else:
        print("✅ Toda migration aplicada tiene su archivo en disco.")

    # (b) En disco pero no aplicadas (pendientes de migrate)
    on_disk_not_applied = set(disk_migrations) - applied
    # Filtrar las que el loader marca como no-aplicables por dependencias rotas
    real_pending = {key for key in on_disk_not_applied if key in loader.graph.nodes}
    if real_pending:
        # No es necesariamente un error (puede haber migrations nuevas sin deploy)
        print(
            f"ℹ️  {len(real_pending)} migration(s) en disco pendientes de aplicar (puede ser normal)."
        )

    return issues


def check_table_namespace(existing_tables: set[str]) -> int:
    """Detecta tablas que aún viven como core_* cuando deberían ser bookings_*."""
    orphans = []
    for base in BOOKINGS_TABLE_RENAMES:
        core_name = f"core_{base}"
        bookings_name = f"bookings_{base}"
        if core_name in existing_tables and bookings_name not in existing_tables:
            orphans.append(core_name)
    if orphans:
        print(f"⚠️  {len(orphans)} tabla(s) aún con prefijo 'core_' (rename 0036 incompleto):")
        for t in sorted(orphans):
            print(f"     • {t}")
        print("   El rename de tablas core->bookings no completó en esta BD.")
        return len(orphans)
    print("✅ No hay tablas core_* huérfanas del rename a bookings.")
    return 0


def check_columns() -> int:
    """Verifica columnas faltantes en modelos críticos."""
    total_missing = 0
    for app_label, model_name in CRITICAL_MODELS:
        try:
            model = django_apps.get_model(app_label, model_name)
        except LookupError:
            print(f"⚠️  Modelo no encontrado: {app_label}.{model_name}")
            continue
        table_name = model._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
                [table_name],
            )
            db_columns = {row[0] for row in cursor.fetchall()}
        if not db_columns:
            print(f"⚠️  Tabla {table_name} no existe en la BD.")
            continue
        model_columns = {f.column for f in model._meta.fields}
        missing = model_columns - db_columns
        if missing:
            total_missing += len(missing)
            print(f"❌ {app_label}.{model_name} ({table_name}) faltan: {sorted(missing)}")
        else:
            print(f"✅ {app_label}.{model_name}: columnas OK")
    return total_missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-columns", action="store_true", help="Omitir el chequeo de columnas."
    )
    args = parser.parse_args()

    section("1) Sincronía migrations aplicadas vs archivos en disco")
    issues = check_migration_sync()

    section("2) Divergencia de namespace de tablas (core_* vs bookings_*)")
    existing = get_existing_tables()
    issues += check_table_namespace(existing)

    if not args.skip_columns:
        section("3) Columnas faltantes en modelos críticos")
        issues += check_columns()

    section("RESUMEN")
    if issues == 0:
        print("✅ Estado saludable: sin divergencias detectadas.")
        return 0
    print(f"❌ {issues} divergencia(s) detectada(s). Revisar docs/MIGRATIONS.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
