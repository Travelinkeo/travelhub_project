# restore_catalogs.py
import os
import django
from django.core.management import call_command
from django.db.utils import IntegrityError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import (
    Moneda, TipoCambio, HotelTarifario, TipoHabitacion, TarifaHabitacion, 
    Proveedor, Amenity, AsientoContable
)

def restore():
    print("--- Iniciando Restauración de Catálogos ---")
    
    # 1. Cargar Fixtures Existentes (Con manejo de errores robusto)
    fixtures = [
        'paises.json',
        'ciudades.json',
        'monedas.json',
        'aerolineas.json',
        'aerolineas_venezuela.json',
        'plan_cuentas_venezuela.json',
        'productos_servicios.json'
    ]
    
    for f in fixtures:
        try:
            print(f"📂 Intentando cargar {f}...")
            # call_command levanta error si falla loaddata
            call_command('loaddata', f, verbosity=0) 
            print(f"   ✅ {f} cargado exitosamente.")
        except Exception as e:
            print(f"   ⚠️ Saltando {f} por error (probablemente datos ya existen): {type(e).__name__}")
            # No detener el script, continuar con el siguiente

    # 2. Seed Data para Modelos Complejos (Necesario para Marketing AI)
    print("\n--- Sembrando Datos Faltantes (Hoteles, Tarifas) ---")
    
    try:
        # Asegurar Moneda USD
        usd, _ = Moneda.objects.get_or_create(codigo_iso="USD", defaults={"nombre": "Dólar"})
        
        # Crear un Hotel de Prueba
        hotel, created = HotelTarifario.objects.get_or_create(
            nombre="Hotel Hesperia Isla Margarita",
            defaults={
                "destino": "Isla de Margarita",
                "categoria": 5,
                "descripcion_corta": "Lujo y confort en el Caribe.",
                "descripcion_larga": "Disfrute de nuestras instalaciones 5 estrellas con campo de golf, spa y acceso directo a la playa.",
                "activo": True
            }
        )
        if created:
            print("✅ Hotel de prueba creado: Hesperia Isla Margarita")
            
            # Crear Habitacion
            room, _ = TipoHabitacion.objects.get_or_create(
                hotel=hotel,
                nombre="Deluxe Vista al Mar",
                defaults={"capacidad_total": 4}
            )
            # Crear Tarifa
            TarifaHabitacion.objects.create(
                tipo_habitacion=room,
                moneda=usd,
                tarifa_dbl=120.00,
                nombre_temporada="Baja 2026"
            )
            # Crear Amenity
            wifi, _ = Amenity.objects.get_or_create(nombre="WiFi Gratis")
            hotel.amenidades.add(wifi)
        else:
             print("ℹ️ Hotel Hesperia ya existe.")

    except Exception as e:
        print(f"❌ Error sembrando datos de hotel: {e}")

    # 3. Datos Contables / Otros
    # (Ya se cargó plan_cuentas_venezuela.json arriba si funcionó)
    
    print("\n--- Restauración General Completada ---")

if __name__ == '__main__':
    restore()
