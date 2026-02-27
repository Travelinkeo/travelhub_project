import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def add_column_if_not_exists(table, column, definition):
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = '{column}'
        """)
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            print(f"Adding column {column} to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        else:
            print(f"Column {column} already exists in {table}.")

def repair():
    # finance_itemreporte
    item_reporte_columns = [
        ('pnr', 'character varying(10)'),
        ('pasajero', 'character varying(200)'),
        ('fecha_emision', 'date'),
        ('monto_sistema', 'numeric(12,2) DEFAULT 0'),
    ]
    
    for col, defn in item_reporte_columns:
        add_column_if_not_exists('finance_itemreporte', col, defn)
        
    # core_gastooperativo (Ensure it matches current model in finance)
    # The current model is GastoOperativo in finance, with db_table='core_gastooperativo'
    # schema: id_gasto (pk), descripcion (char), monto (decimal), fecha (date), 
    # categoria (char), comprobante (file), moneda_id (int), creado_por_id (int), fecha_registro (timestamp)
    
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'core_gastooperativo'")
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            print("Creating table core_gastooperativo...")
            cursor.execute("""
                CREATE TABLE core_gastooperativo (
                    id_gasto serial PRIMARY KEY,
                    descripcion character varying(255) NOT NULL,
                    monto numeric(12,2) NOT NULL,
                    fecha date NOT NULL,
                    categoria character varying(100),
                    comprobante character varying(100),
                    moneda_id integer NOT NULL,
                    creado_por_id integer,
                    fecha_registro timestamp with time zone NOT NULL DEFAULT now()
                )
            """)
        else:
            print("Table core_gastooperativo already exists. Syncing columns...")
            gasto_columns = [
                ('descripcion', 'character varying(255)'),
                ('monto', 'numeric(12,2)'),
                ('fecha', 'date'),
                ('categoria', 'character varying(100)'),
                ('comprobante', 'character varying(100)'),
                ('moneda_id', 'integer'),
                ('creado_por_id', 'integer'),
                ('fecha_registro', 'timestamp with time zone DEFAULT now()'),
            ]
            for col, defn in gasto_columns:
                add_column_if_not_exists('core_gastooperativo', col, defn)

if __name__ == "__main__":
    try:
        repair()
        print("Finance database repair completed successfully.")
    except Exception as e:
        print(f"Error during finance database repair: {e}")
