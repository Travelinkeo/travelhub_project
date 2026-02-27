
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def check_columns():
    with connection.cursor() as cursor:
        desc = connection.introspection.get_table_description(cursor, 'core_boletoimportado')
        columns = [col.name for col in desc]
        print(f"Columns in core_boletoimportado: {columns}")
        
        needed = ['total_boleto', 'nombre_pasajero_procesado']
        for col in needed:
            if col in columns:
                print(f"✅ {col} exists.")
            else:
                print(f"❌ {col} MISSING!")

if __name__ == '__main__':
    check_columns()
