import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),  # Depende de core para la Agencia y Usuario
        ("finance", "0012_remove_facturaconsolidada_agencia_and_more"),
    ]

    operations = []
