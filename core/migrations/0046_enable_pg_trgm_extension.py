from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """
    Crea la extensión pg_trgm en PostgreSQL para habilitar búsquedas de
    similitud de trigramas (ILIKE combinado con índices GIN/GIST).

    Antes esta extensión se activaba en tests/conftest.py via signal
    connection_created, lo que:
      - Usaba SQL nativo en lugar de ORM/migraciones
      - Se ejecutaba en cada conexión (innecesario)
      - Ocultaba errores con try/except pass
    """

    dependencies = [
        ("core", "0045_api_keys_webhooks_v2"),
    ]

    operations = [
        CreateExtension(name="pg_trgm"),
    ]
