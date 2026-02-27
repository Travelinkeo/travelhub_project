import os
import django
import sys

def run():
    print("--- VERIFICACIÓN WAKU LODGE ---")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()

    from core.models.tarifario_hoteles import HotelTarifario
    from core.services.ai_copywriter import AICopywriter

    # 1. Buscar Hotel
    query = "AGUA DORADA"
    hotels = HotelTarifario.objects.filter(nombre__icontains=query)
    
    if not hotels.exists():
        print(f"❌ No se encontró ningún hotel con el nombre '{query}'.")
        # Listar algunos disponibles
        print("Hoteles disponibles:")
        for h in HotelTarifario.objects.all()[:5]:
            print(f"- {h.nombre}")
        return

    hotel = hotels.first()
    print(f"✅ Hotel Encontrado: {hotel.nombre} (ID: {hotel.pk})")
    print(f"   Destino: {hotel.destino}")
    print(f"   Amenidades: {', '.join([a.nombre for a in hotel.amenidades.all()])}\n")

    # 2. Generar Copy (Prueba Real)
    print("🤖 Generando Copy con Gemini AI (Tono: AVENTURERO)...\n")
    
    cw = AICopywriter()
    copy = cw.generate_caption(hotel.id, tone="AVENTURERO")
    
    print("--- RESULTADO ---")
    print(copy)
    print("-----------------")

if __name__ == "__main__":
    run()
