from django.db import connection
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute('SHOW SERVER_ENCODING')
    server = cursor.fetchone()
    cursor.execute('SHOW CLIENT_ENCODING')
    client = cursor.fetchone()
    print(f"Server: {server}, Client: {client}")
