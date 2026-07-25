# Generated migration to add missing updated_at column
"""Migración de base de datos para bookings.
"""

from django.db import migrations


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        (
            "bookings",
            "0021_rename_core_boleto_agencia_5b10f1_idx_bookings_bo_agencia_1abd71_idx_and_more",
        ),
    ]

    operations = []
