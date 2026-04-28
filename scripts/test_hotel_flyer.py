import os
import django
from io import BytesIO

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.marketing.services.flyer_service import FlyerService
from core.models.tarifario_hoteles import HotelTarifario

def test_hotel_flyer_generation():
    # Buscar un hotel cualquiera
    hotel = HotelTarifario.objects.first()
    if not hotel:
        print("No hay hoteles en la base de datos para probar.")
        return

    print(f"Probando generación para el hotel: {hotel.nombre} ({hotel.destino})")
    
    service = FlyerService()
    # Forzar una prueba
    buffer = service.generate_flyer(hotel_id=hotel.id, price="$120")
    
    # Guardar localmente para inspección manual
    output_path = "test_hotel_flyer.jpg"
    with open(output_path, "wb") as f:
        f.write(buffer.getvalue())
    
    print(f"Flyer generado exitosamente en: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    test_hotel_flyer_generation()
