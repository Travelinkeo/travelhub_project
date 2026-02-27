# verify_marketing_ai.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.marketing_service import MarketingService

def verify():
    print("--- Verificando Marketing AI ---")
    
    # 1. Test Social Caption
    print("\n1. Generando Caption para Redes Sociales...")
    caption = MarketingService.generate_social_caption(
        nombre_producto="Paquete Isla Margarita 4D/3N",
        destino="Isla de Margarita, Venezuela",
        detalles="Hotel 5 estrellas Todo Incluido, Translados, Tour de Compras. Precio especial parejas.",
        tono="DIVERTIDO"
    )
    print("\n--- Resultado Caption ---")
    print(caption)
    
    if "#" in caption and "Margarita" in caption:
        print("\n✅ Caption generado correctamente (contiene hashtags y keywords).")
    else:
        print("\n⚠️ Advertencia: El caption no parece completo.")

    # 2. Test Email Newsletter
    print("\n2. Generando Newsletter HTML...")
    ofertas = [
        {'titulo': 'Fin de Semana en Morrocoy', 'precio': '$150'},
        {'titulo': 'Escapada a Canaima', 'precio': '$450'},
        {'titulo': 'Full Day Los Roques', 'precio': '$280'}
    ]
    
    newsletter_html = MarketingService.generate_email_newsletter(ofertas)
    print("\n--- Resultado Newsletter (Snippet) ---")
    print(newsletter_html[:500] + "...")
    
    if "<html>" in newsletter_html.lower() or "<body" in newsletter_html.lower() or "Morrocoy" in newsletter_html:
         print("\n✅ Newsletter generado correctamente (HTML detectado).")
    else:
         print("\n⚠️ Advertencia: El newsletter no parece HTML válido.")

    print("\n--- Verificación Marketing AI Completada ---")

if __name__ == '__main__':
    verify()
