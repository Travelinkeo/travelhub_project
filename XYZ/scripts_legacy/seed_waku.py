import os
import django
import requests
from django.core.files.base import ContentFile
from decimal import Decimal
from datetime import date

def run():
    print("--- SEEDING WAKU LODGE ---")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()

    from core.models import HotelTarifario, Amenity, TipoHabitacion, TarifaHabitacion, TarifarioProveedor, Proveedor

    # 1. Crear Proveedor Dummy si no existe
    try:
        print("Creating Proveedor...")
        prov, _ = Proveedor.objects.get_or_create(nombre="Waku Tours", defaults={'tipo_proveedor': 'HTL'})
        print("Creating TarifarioProveedor...")
        tarifario, _ = TarifarioProveedor.objects.get_or_create(
            proveedor=prov, 
            nombre="Tarifas 2026",
            defaults={
                'fecha_vigencia_inicio': date(2026, 1, 1),
                'fecha_vigencia_fin': date(2026, 12, 31)
            }
        )
    except Exception as e:
        print(f"❌ Error creando Proveedor/Tarifario: {e}")
        return

    # 2. Crear Amenidades
    print("Creating Amenities...")
    amenities_list = [
        ('Wifi Satelital', 'wifi'),
        ('Restaurante Gourmet', 'utensils'),
        ('Excursiones Salto Ángel', 'mountain'),
        ('Traslado Aéreo', 'plane'),
        ('Vista a la Laguna', 'eye'),
        ('Aire Acondicionado', 'wind')
    ]
    
    amenity_objs = []
    try:
        for name, icon in amenities_list:
            a, _ = Amenity.objects.get_or_create(nombre=name, defaults={'icono_lucide': icon})
            amenity_objs.append(a)
    except Exception as e:
        print(f"❌ Error creando Amenidades: {e}")
        return

    # 3. Crear Hotel
    print("Creating Hotel...")
    description = """
    Bienvenido a Waku Lodge, el refugio más exclusivo del Parque Nacional Canaima. 
    Situado a orillas de la laguna de Canaima, frente a las majestuosas cascadas Hacha, Golondrina y Ucaima. 
    
    Nuestra arquitectura se integra armónicamente con la selva, ofreciendo un lujo descalzo inigualable.
    Disfruta de nuestra gastronomía de autor, relájate escuchando el rugir de los tepuyes y embárcate 
    en la aventura de tu vida hacia el Kerepakupai Vená (Salto Ángel).
    
    Ideal para parejas, lunas de miel y aventureros que no renuncian al confort.
    """
    
    hotel = None
    try:
        hotel, created = HotelTarifario.objects.get_or_create(
            nombre="Waku Lodge",
            defaults={
                'destino': "Canaima",
                'tarifario': tarifario,
                'categoria': 5,
                'descripcion_corta': "Lujo frente a la laguna de Canaima.",
                'descripcion_larga': description.strip(),
                'regimen_default': 'PC', # Pensión Completa
                'comision': Decimal('12.00'),
                'destacado': True
            }
        )
        
        if created:
            print("✅ Hotel creado.")
            hotel.amenidades.set(amenity_objs)
            hotel.save()
            
            # 4. Descargar Imagen Dummy (Unsplash - Jungle/Waterfall)
            try:
                print("📸 Descargando imagen de portada...")
                img_url = "https://images.unsplash.com/photo-1469598284692-1014cc679461?ixlib=rb-4.0.3&auto=format&fit=crop&w=1080&q=80" # Waterfall
                resp = requests.get(img_url, timeout=10)
                if resp.status_code == 200:
                    hotel.imagen_principal.save("waku_cover.jpg", ContentFile(resp.content), save=True)
                    print("📸 Imagen guardada.")
            except Exception as e:
                print(f"⚠️ No se pudo descargar imagen: {e}")

        else:
            print("ℹ️ El hotel ya existía. Actualizando datos base...")
            hotel.descripcion_larga = description.strip()
            hotel.amenidades.set(amenity_objs)
            hotel.save()

    except Exception as e:
        print(f"❌ Error creando Hotel: {e}")
        if hotel: print(hotel.__dict__)
        return

    # 5. Crear Habitaciones y Tarifas
    print("Creating Rooms...")
    try:
        tipo_std, _ = TipoHabitacion.objects.get_or_create(
            hotel=hotel,
            nombre="Suite Laguna",
            defaults={
                'capacidad_total': 3,
                'descripcion': "Habitación amplia con terraza privada y hamaca frente a las cataratas."
            }
        )
        
        print("Creating Rates...")
        TarifaHabitacion.objects.get_or_create(
            tipo_habitacion=tipo_std,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 6, 30),
            defaults={
                'moneda': 'USD',
                'tarifa_dbl': Decimal('350.00'), # $350 por persona
                'tarifa_sgl': Decimal('500.00')
            }
        )
    except Exception as e:
        print(f"❌ Error creando Habitaciones/Tarifas: {e}")
        return
    
    print(f"✅ Datos listos para: {hotel.nombre}")
    print(f"   Slug: {hotel.slug}")

if __name__ == "__main__":
    run()
