import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text

# Read the Copa ticket
with open(r'C:\Users\ARMANDO\Downloads\Itinerary for Record Locator DYEXFG.eml', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("="*80)
print("TESTING COPA DETECTION")
print("="*80)

# Check for markers
print("\n1. Checking for Copa markers:")
print(f"   - 'COPA AIRLINES' in text: {'COPA AIRLINES' in content.upper()}")
print(f"   - 'RECORD LOCATOR' in text: {'RECORD LOCATOR' in content.upper()}")
print(f"   - 'ACCELYA.COM' in text: {'ACCELYA.COM' in content.upper()}")
print(f"   - 'FARELOGIX.COM/SPRK' in text: {'FARELOGIX.COM/SPRK' in content.upper()}")
print(f"   - 'SPRK/PUBLIC/IMAGES' in text: {'SPRK/PUBLIC/IMAGES' in content.upper()}")

print("\n2. Checking for SABRE markers:")
print(f"   - 'ETICKET RECEIPT' in text: {'ETICKET RECEIPT' in content.upper()}")
print(f"   - 'RECIBO DE PASAJE ELECTRÓNICO' in text: {'RECIBO DE PASAJE ELECTRÓNICO' in content.upper()}")
print(f"   - 'RESERVATION CODE' in text: {'RESERVATION CODE' in content.upper()}")
print(f"   - 'CÓDIGO DE RESERVACIÓN' in text: {'CÓDIGO DE RESERVACIÓN' in content.upper()}")

print("\n3. Running parser...")
try:
    result = extract_data_from_text(content, content)
    print(f"\n✅ Parser completed successfully!")
    print(f"\n📋 Detected System: {result.get('SOURCE_SYSTEM', 'UNKNOWN')}")
    print(f"\n📄 Full Result:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\n❌ Parser failed with error:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
