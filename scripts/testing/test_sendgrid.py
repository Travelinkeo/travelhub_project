"""
test_sendgrid.py
================
Verifica que el backend SMTP de SendGrid está correctamente configurado.

USO:
    python manage.py shell < scripts/testing/test_sendgrid.py

    O bien:
    cd c:\Users\ARMANDO\travelhub_project
    .\venv\Scripts\python.exe scripts/testing/test_sendgrid.py
"""

import os
import sys
import django

# Bootstrap Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail

print("=" * 60)
print("🔍 DIAGNÓSTICO DE CONFIGURACIÓN DE EMAIL")
print("=" * 60)
print(f"  EMAIL_BACKEND  : {settings.EMAIL_BACKEND}")
print(f"  EMAIL_HOST     : {settings.EMAIL_HOST}")
print(f"  EMAIL_PORT     : {settings.EMAIL_PORT}")
print(f"  EMAIL_USE_TLS  : {settings.EMAIL_USE_TLS}")
print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"  EMAIL_PASSWORD : {'✅ CONFIGURADA' if settings.EMAIL_HOST_PASSWORD and not settings.EMAIL_HOST_PASSWORD.startswith('SG.pon-') else '❌ NO CONFIGURADA (placeholder)'}")
print(f"  DEFAULT_FROM   : {settings.DEFAULT_FROM_EMAIL}")
print("=" * 60)

if 'console' in settings.EMAIL_BACKEND:
    print("\n⚠️  Modo CONSOLA activo — los emails NO se envían.")
    print("   Agrega tu SENDGRID_API_KEY real al .env para activar el envío.")
    sys.exit(0)

# Solicitar destinatario
email_destino = input("\n📧 ¿A qué email enviar el test? (Enter para omitir): ").strip()
if not email_destino:
    print("Prueba cancelada.")
    sys.exit(0)

print(f"\n🚀 Enviando email de prueba a {email_destino}...")

try:
    resultado = send_mail(
        subject="✅ TravelHub — SendGrid funcionando",
        message=(
            "Este email confirma que SendGrid SMTP está correctamente "
            "configurado en TravelHub.\n\n"
            "Puedes eliminar este mensaje de prueba."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email_destino],
        fail_silently=False,
    )
    print(f"\n✅ ¡Email enviado exitosamente! (resultado: {resultado})")
    print("   Revisa tu bandeja de entrada.")
except Exception as e:
    print(f"\n❌ ERROR al enviar: {type(e).__name__}: {e}")
    print("\n💡 CAUSAS COMUNES:")
    print("   1. SENDGRID_API_KEY inválida o sin permisos 'Mail Send'")
    print("   2. El dominio del DEFAULT_FROM_EMAIL no está verificado en SendGrid")
    print("   3. La cuenta de SendGrid está en sandbox (no puede enviar a externos)")
