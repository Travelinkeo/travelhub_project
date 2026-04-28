import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.linkeo_service import LinkeoService

# Test the service directly
print("Testing LinkeoService...")

test_messages = [
    "Hola",
    "Ventas de hoy",
    "Estatus boleto 863"
]

for msg in test_messages:
    print(f"\n{'='*50}")
    print(f"Input: {msg}")
    print(f"{'='*50}")
    try:
        response = LinkeoService.process_message(msg, user_id=123)
        print(f"✅ Response: {response}")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
