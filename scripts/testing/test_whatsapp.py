"""
Script de prueba para WhatsApp
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.whatsapp_notifications import enviar_whatsapp

print("=== Test WhatsApp ===\n")

# IMPORTANTE: Reemplaza con tu número en formato internacional
# Ejemplo Venezuela: +584121234567
# Ejemplo Colombia: +573001234567
mi_numero = '+582126317079'  # Tu número que viste en Twilio

print(f"Enviando mensaje de prueba a: {mi_numero}")

mensaje = """🌍 *TravelHub - Prueba de WhatsApp*

¡Hola! Este es un mensaje de prueba.

✅ Sistema funcionando correctamente

_Equipo TravelHub_"""

resultado = enviar_whatsapp(mi_numero, mensaje)

if resultado:
    print("\n✓ WhatsApp enviado exitosamente!")
    print("Revisa tu WhatsApp en unos segundos.")
else:
    print("\n✗ Error al enviar WhatsApp")
    print("Verifica que:")
    print("  1. Twilio esté instalado: pip install twilio")
    print("  2. Las credenciales en .env sean correctas")
    print("  3. Tu número esté en formato internacional (+58...)")
