"""
Script de prueba para verificar que el logo se muestra en los emails
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.email_notifications import enviar_email_html
from django.conf import settings

print("=== Test Email con Logo ===\n")

context = {
    'cliente_nombre': 'Usuario de Prueba',
    'localizador': 'TEST123',
    'fecha': '03/10/2025',
    'total': '500.00',
    'moneda': '$',
    'estado': 'Confirmada'
}

print("Enviando email de prueba con logo...")
resultado = enviar_email_html(
    'Test - Email con Logo de TravelHub',
    'core/emails/confirmacion_venta.html',
    context,
    settings.EMAIL_HOST_USER
)

if resultado:
    print("\n✓ Email enviado exitosamente!")
    print(f"Revisa tu bandeja: {settings.EMAIL_HOST_USER}")
    print("\nEl email debe mostrar:")
    print("  1. Logo de TravelHub en el header")
    print("  2. Diseño con gradiente morado")
    print("  3. Información de la venta")
else:
    print("\n✗ Error al enviar email")
    print("Verifica:")
    print("  1. Que el archivo logo.svg exista en static/images/")
    print("  2. Las credenciales de email en .env")
