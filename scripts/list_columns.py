from django.db import connection
table_name = 'personas_pasajero'
with connection.cursor() as cursor:
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
    columns = [row[0] for row in cursor.fetchall()]
    print(columns)
