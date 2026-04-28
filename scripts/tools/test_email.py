import os
import django

# Configurar entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.email_service import send_custom_email

def test_send():
    print("🚀 Iniciando prueba de envío con Resend...")
    
    # Intenta enviar a una dirección de prueba (Cámbiala si quieres recibirla tú)
    destinatario = "armandoalemanm@gmail.com" # Probando con un email común
    asunto = "🚀 TravelHub AI - Prueba de Resend"
    
    contexto = {
        'mensaje': 'Si estás leyendo esto, el motor de Resend está 100% operativo en TravelHub. ¡Felicidades, Armando!',
        'nombre': 'Armando Aleman'
    }
    
    # Usamos un template base que ya existe o uno simple
    exito = send_custom_email(
        subject=asunto,
        recipient=destinatario,
        template_name='core/emails/base_email.html', # Usando el base que vimos en el listado
        context=contexto
    )
    
    if exito:
        print("✅ CORREO ENVIADO EXITOSAMENTE a través de Resend.")
    else:
        print("❌ FALLO EL ENVÍO. Revisa el log de errores.")

if __name__ == "__main__":
    test_send()
