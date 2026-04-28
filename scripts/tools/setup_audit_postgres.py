import os
import django
from django.db import connection

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def setup_audit_table():
    with connection.cursor() as cursor:
        # Obtener nombres de tablas reales
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tablas en Postgres: {len(tables)}")

        # Identificar tabla de ventas (puede ser core_venta o bookings_venta)
        venta_table = 'bookings_venta' if 'bookings_venta' in tables else 'core_venta'
        agencia_table = 'core_agencia'
        
        print(f"Usando venta_table: {venta_table}")

        # SQL para crear la tabla
        sql = f"""
        CREATE TABLE IF NOT EXISTS bookings_ventaauditfinding (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(3) NOT NULL,
            mensaje TEXT NOT NULL,
            estado VARCHAR(3) NOT NULL,
            fecha_deteccion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            agencia_id INTEGER REFERENCES {agencia_table}(id) ON DELETE SET NULL,
            venta_id INTEGER NOT NULL REFERENCES {venta_table}(id_venta) ON DELETE CASCADE
        );
        """
        
        try:
            cursor.execute(sql)
            print("✅ Tabla bookings_ventaauditfinding creada/verificada en PostgreSQL.")
        except Exception as e:
            print(f"❌ Error creando tabla: {e}")

if __name__ == "__main__":
    setup_audit_table()
