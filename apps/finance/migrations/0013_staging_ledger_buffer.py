"""Migración de base de datos para finance.
"""

from django.db import migrations


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("core", "0001_initial"),  # Depende de core para la Agencia y Usuario
        ("finance", "0012_remove_facturaconsolidada_agencia_and_more"),
    ]

    operations = []
