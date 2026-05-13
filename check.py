import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'travelhub.settings'
import django
django.setup()
from django.db import connection
with connection.cursor() as cur:
    cur.execute("SELECT id_boleto_importado, estado_parseo, archivo_pdf_generado FROM bookings_boletoimportado ORDER BY fecha_subida DESC LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(f"ID:{r[0]} Estado:{r[1]} PDF:{r[2]}")