import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.apps import apps
from django.db import connection

apps_to_check = ['bookings', 'core', 'finance', 'common', 'crm', 'contabilidad', 'cotizaciones', 'marketing', 'cms']

for app_label in apps_to_check:
    app_config = apps.get_app_config(app_label)
    for model in app_config.get_models():
        table_name = model._meta.db_table
        
        # Get DB columns
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}';")
            db_columns = {row[0] for row in cursor.fetchall()}
            
        if not db_columns:
            continue # Table might not exist or we don't care right now
            
        # Get model columns
        model_columns = set()
        for f in model._meta.fields:
            model_columns.add(f.column)
            
        missing = model_columns - db_columns
        if missing:
            print(f"Model {model.__name__} (Table: {table_name}) is missing columns: {missing}")
