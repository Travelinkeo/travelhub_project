
import os
import sys
import django
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.cms.services.cms_ai_service import CMSContentService

def test_cms_automation():
    results = {"meta": "Validacion CMS AI TravelHub"}
    service = CMSContentService()
    
    # Prueba 1: Post de Instagram
    print("Probando TEST 1...")
    vuelo_context = "Vuelo directo Caracas-Madrid con Iberia, salida 15 de Mayo, incluye 2 maletas."
    results["test_1_instagram"] = service.generate_social_post(vuelo_context, "Instagram")

    # Prueba 2: Guía de Destino
    print("Probando TEST 2...")
    results["test_2_guia"] = service.generate_destination_guide_data("Paris, Francia")

    # Prueba 3: Artículo de Blog
    print("Probando TEST 3...")
    try:
        articulo = service.generate_blog_article("5 consejos imprescindibles para tu primer viaje a Italia", "Italia")
        results["test_3_blog"] = {
            "titulo": articulo.titulo,
            "resumen": articulo.resumen,
            "meta_descripcion": articulo.meta_descripcion
        }
    except Exception as e:
        results["test_3_blog_error"] = str(e)

    # Guardar resultados
    with open("cms_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print("Prubea finalizada. Resultados guardados en cms_validation_results.json")

if __name__ == "__main__":
    test_cms_automation()
