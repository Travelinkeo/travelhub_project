import os
import sys

sys.path.insert(0, "/app")
os.environ["DJANGO_SETTINGS_MODULE"] = "travelhub.settings"

import django

django.setup()

from django.db import connection

# Check: are the DB-only migrations for the missing stubs actually present?
c = connection.cursor()

# Only add the stub if the record doesn't already exist
stubs = [
    ("core", "0044_api_keys_webhooks"),
    ("bookings", "0043_add_missing_performance_indexes"),
    ("bookings", "0045_remove_boletoimportado_uq_boleto_agencia_message_id_and_more"),
]

for app, name in stubs:
    c.execute("SELECT COUNT(*) FROM django_migrations WHERE app=%s AND name=%s", (app, name))
    count = c.fetchone()[0]
    if count == 0:
        print(f"WARNING: {app} {name} not found in DB - cannot stub")
    else:
        print(f"{app} {name}: OK (in DB)")
