import os
import django
import sys

# Añadir el directorio del proyecto al path
sys.path.append('c:/Users/ARMANDO/travelhub_project')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from dotenv import load_dotenv
load_dotenv()

from apps.marketing.services.copywriter_service import CopywriterService
from core.models import HotelTarifario

def test_generation():
    service = CopywriterService()
    hotel = HotelTarifario.objects.first()
    if not hotel:
        print("No hay hoteles en la DB.")
        return
        
    print(f"Probando generación para hotel: {hotel.nombre} (ID: {hotel.id})")
    try:
        package = service.generate_social_package(
            hotel_id=hotel.id,
            tone="LUXURY",
            extra_prompt="Enfócate en la exclusividad."
        )
        print("Resultado exitoso:")
        print(package)
    except Exception as e:
        print("Error capturado:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
