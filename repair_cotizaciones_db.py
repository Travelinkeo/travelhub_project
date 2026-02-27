import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def add_column_if_not_exists(table, column, definition):
    with connection.cursor() as cursor:
        # Check if column exists
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
    # core_cotizacion
    cotizacion_columns = [
        ('numero_pasajeros', 'integer DEFAULT 1'),
        ('fecha_vencimiento', 'date'),
        ('terminos_pago', 'text'),
        ('terminos_cancelacion', 'text'),
        ('archivo_pdf', 'character varying(255)'),
        ('fecha_envio', 'timestamp with time zone'),
        ('fecha_vista', 'timestamp with time zone'),
        ('fecha_respuesta', 'timestamp with time zone'),
        ('email_enviado', 'boolean DEFAULT false'),
        ('venta_generada_id', 'integer'),
        ('notas', 'text'),
        ('fecha_validez', 'date'),
    ]
    
    for col, defn in cotizacion_columns:
        add_column_if_not_exists('core_cotizacion', col, defn)
        
    # core_itemcotizacion
    item_columns = [
        ('tipo_item', 'character varying(3) DEFAULT \'OTR\''),
        ('descripcion', 'character varying(255) DEFAULT \'\''),
        ('detalles_json', 'jsonb'),
        ('costo', 'numeric(12,2) DEFAULT 0'),
        ('descripcion_personalizada', 'character varying(255)'),
        ('cantidad', 'numeric(10,2) DEFAULT 1'),
        ('precio_unitario', 'numeric(12,2) DEFAULT 0'),
        ('producto_servicio_id', 'integer'),
    ]
    
    for col, defn in item_columns:
        add_column_if_not_exists('core_itemcotizacion', col, defn)

if __name__ == "__main__":
    try:
        repair()
        print("Database repair completed successfully.")
    except Exception as e:
        print(f"Error during database repair: {e}")
