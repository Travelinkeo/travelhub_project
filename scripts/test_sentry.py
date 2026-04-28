import sentry_sdk
import logging
import time

# Setup Django
import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

logger = logging.getLogger(__name__)

def test_sentry():
    print("\n" + "=" * 60)
    print("🚀 TEST: Sentry Integration")
    print("=" * 60 + "\n")
    
    try:
        from django.conf import settings
        print(f"📡 DSN Configurado: {settings.SENTRY_DSN[:20]}...")
        
        # Test sanitization
        from core.utils.sentry_utils import sanitize_sensitive_data
        print("✅ Función de sanitización cargada correctamente")
        
        test_event = {
            'extra': {
                'numero_pasaporte': 'P12345678',
                'normal_data': 'ok'
            }
        }
        sanitized = sanitize_sensitive_data(test_event, {})
        
        print("\n🛡️ Prueba de Sanitización:")
        print(f"   Original: ... 'numero_pasaporte': 'P12345678' ...")
        print(f"   Sanitizado: {sanitized['extra']}")
        
        if sanitized['extra']['numero_pasaporte'] == '[REDACTED]':
             print("   ✅ Sanitización FUNCIONA")
        else:
             print("   ❌ Sanitización FALLÓ")

        # Capture message
        print("\n📨 Enviando mensaje de prueba a Sentry...")
        sentry_id = sentry_sdk.capture_message("TravelHub Security Test - Verification")
        print(f"   ✅ Mensaje enviado! ID: {sentry_id}")
        
        print("\n" + "=" * 60)
        print("✅ VERIFICACIÓN DE SENTRY COMPLETADA")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == '__main__':
    test_sentry()
