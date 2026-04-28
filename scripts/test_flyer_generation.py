
import os
import django
import sys
from io import BytesIO

def test_flyer():
    print("--- Probando Generador de Flyers ---")
    try:
        from core.services.flash_marketing_service import FlashMarketingService
        service = FlashMarketingService()
        
        dest = "Madrid"
        price = "850 USD"
        
        print(f"Generando flyer para: {dest} - {price}")
        img_buffer = service.generate_flyer(dest, price, airline="Air Europa")
        
        output_path = "test_flyer_result.jpg"
        with open(output_path, "wb") as f:
            f.write(img_buffer.getvalue())
            
        print(f"✅ Imagen generada exitosamente: {output_path}")
        print("Ábrela para verificar el diseño.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()
    
    test_flyer()
