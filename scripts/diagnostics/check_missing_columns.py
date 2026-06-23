"""
Diagnóstico: detecta columnas definidas en los modelos que no existen en la BD.

Compara los campos declarados en cada modelo de Django con las columnas reales
de PostgreSQL (information_schema.columns) y reporta las faltantes.

Uso:
    python scripts/diagnostics/check_missing_columns.py
    python scripts/diagnostics/check_missing_columns.py --app bookings
    python scripts/diagnostics/check_missing_columns.py --app bookings --model Venta

Salida con código de exit != 0 si se encuentran columnas faltantes, para poder
usarlo en CI / checks pre-deploy.
"""

import argparse
import os
import sys

import django

# Asegurar que la raíz del proyecto esté en PYTHONPATH (igual que scripts/reset_password.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.apps import apps  # noqa: E402
from django.db import connection  # noqa: E402

# Apps de negocio a verificar por defecto (excluye django.contrib y third-party)
DEFAULT_APPS = [
    "bookings",
    "core",
    "finance",
    "common",
    "crm",
    "contabilidad",
    "cotizaciones",
    "marketing",
    "cms",
    "communications",
    "automation",
]


def get_db_columns(table_name: str) -> set[str]:
    """Devuelve el conjunto de columnas reales de una tabla en la BD."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            [table_name],
        )
        return {row[0] for row in cursor.fetchall()}


def check_model(model) -> set[str]:
    """Devuelve las columnas del modelo que no existen en la BD (vacío si todo ok)."""
    table_name = model._meta.db_table
    db_columns = get_db_columns(table_name)
    if not db_columns:
        # La tabla no existe (todavía) en la BD: no se puede comparar.
        return set()
    model_columns = {f.column for f in model._meta.fields}
    return model_columns - db_columns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app",
        action="append",
        help="App a verificar (se puede repetir). Por defecto: todas las apps de negocio.",
    )
    parser.add_argument(
        "--model",
        help="Limitar a un nombre de modelo (ignora mayúsculas/minúsculas).",
    )
    args = parser.parse_args()

    app_labels = args.app or DEFAULT_APPS
    model_filter = args.model.lower() if args.model else None

    total_missing = 0
    checked_models = 0

    for app_label in app_labels:
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            print(f"⚠️  App desconocida: '{app_label}'")
            continue

        for model in app_config.get_models():
            if model_filter and model.__name__.lower() != model_filter:
                continue
            checked_models += 1
            missing = check_model(model)
            if missing:
                total_missing += len(missing)
                table_name = model._meta.db_table
                print(
                    f"❌ {model.__name__} (tabla: {table_name}) "
                    f"faltan {len(missing)} columnas: {sorted(missing)}"
                )

    print("\n" + "=" * 60)
    if total_missing == 0:
        print(f"✅ {checked_models} modelo(s) verificado(s). Todas las columnas existen en la BD.")
        return 0
    print(f"❌ {checked_models} modelo(s) verificado(s). {total_missing} columna(s) faltante(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
